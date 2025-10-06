# Load necessary libraries
from flask import Flask, render_template, request, url_for, redirect, send_from_directory, jsonify
import os
import threading
import time
import uuid
import tempfile
import atexit
import shutil
from werkzeug.utils import secure_filename
import fitz # PyMuPDF
import logging
import zipfile
from manage_pdfs.compress import compress_pdf
from manage_pdfs.split import split_pdf_with_progress as split_func
from manage_pdfs.combine import combine_pdfs
from manage_pdfs.flatten import flatten_pdf
from manage_pdfs.optimize import optimize_pdf
from manage_pdfs.extract_pages import extract_pages
from utils.manage_temp import cleanup_temp_folder
from utils.manage_output_dir import get_default_output_folder, FolderSelector

DEBUG = True

# Configure logging
if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Create default output directory
DEFAULT_OUTPUT_FOLDER = get_default_output_folder()
logging.debug(f"Default output folder: {DEFAULT_OUTPUT_FOLDER}")

# Create a temporary directory for intermediate file operations
TEMP_FOLDER = tempfile.mkdtemp(prefix='pdf_management_temp_')
logging.debug(f"Created temporary folder: {TEMP_FOLDER}")

# Ensure cleanup on exit
atexit.register(lambda: cleanup_temp_folder(TEMP_FOLDER))

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session
app.config['UPLOAD_FOLDER'] = TEMP_FOLDER  # For temporary uploads
app.config['OUTPUT_FOLDER'] = DEFAULT_OUTPUT_FOLDER  # For final outputs
ALLOWED_EXTENSIONS = {'pdf'}

# In-memory job state (for demo only)
redaction_jobs = {}

# Global redaction service instances (keyed by PDF filename)
redaction_services = {}

# Split progress tracking
split_progress = {}

# Flatten progress tracking
flatten_progress = {}

### Page Routes ####

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_default_output_folder')
def get_default_output_folder_api():
    """Return the default output folder path"""
    return jsonify({'folder': app.config['OUTPUT_FOLDER']})

@app.route('/api/select_folder', methods=['POST'])
def api_select_folder():
    """Open native folder selection dialog"""
    try:
        # Use the FolderSelector from utils
        folder_selector = FolderSelector()
        selected_folder = folder_selector.select_folder()
        
        if selected_folder:
            return jsonify({'success': True, 'folder': selected_folder})
        else:
            return jsonify({'success': False, 'error': 'No folder selected'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def allowed_file(filename, allowed=ALLOWED_EXTENSIONS):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

@app.route('/help/')
def help():
    return render_template('help.html')

@app.route('/home')
@app.route('/home/')
def redirect_home_to_index():
    return redirect(url_for('index'), code=301)

@app.route('/help')
def redirect_help():
    return redirect(url_for('help'), code=301)


### Other Routes ####

@app.errorhandler(404)
def handle_404(e):
    if request.path.endswith('.map'):
        return '', 204  # Return an empty response for .map requests
    return render_template('404.html'), 404

@app.route('/api/compress_pdf', methods=['POST'])
def api_compress_pdf():
    try:
        input_pdf = request.files.get('input_pdf')
        output_filename = request.form.get('output_filename')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        should_optimize = request.form.get('optimize', 'false').lower() == 'true'
        
        if not input_pdf or not output_filename:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
            
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(input_pdf.filename))
        input_pdf.save(input_path)
        
        # If optimization is requested, optimize first then compress
        if should_optimize:
            temp_optimized_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_optimized_{secure_filename(input_pdf.filename)}")
            optimize_result = optimize_pdf(input_path, temp_optimized_path, aggressive=False)
            if not optimize_result:
                return jsonify({'success': False, 'error': 'Optimization failed.'})
            # Use optimized file as input for compression
            compress_input_path = temp_optimized_path
        else:
            compress_input_path = input_path
        
        output_path = os.path.join(output_folder, secure_filename(output_filename))
        result = compress_pdf(compress_input_path, output_path)
        
        # Clean up temporary optimized file if it was created
        if should_optimize and os.path.exists(temp_optimized_path):
            os.unlink(temp_optimized_path)
        
        if result:
            return jsonify({'success': True, 'filename': output_path, 'error': None})
        else:
            return jsonify({'success': False, 'error': 'Compression failed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def flatten_pdf_with_progress(job_id, input_path, output_path):
    """Run PDF flatten with progress tracking"""
    try:
        # Initialize progress
        flatten_progress[job_id] = {
            'status': 'starting',
            'current_page': 0,
            'total_pages': 0,
            'percentage': 0,
            'message': 'Initializing...',
            'cancelled': False
        }
        
        # Call flatten function with progress callback
        def progress_callback(current_page, total_pages, percentage, message):
            # Check for cancellation request
            if flatten_progress[job_id].get('cancelled', False):
                logging.info(f"Flatten job {job_id} cancelled during progress callback")
                return False  # Signal cancellation to flatten function
            
            # Update progress dictionary
            flatten_progress[job_id].update({
                'status': 'processing',
                'current_page': current_page,
                'total_pages': total_pages,
                'percentage': percentage,
                'message': message
            })
            
            logging.debug(f"Flatten progress update: page {current_page}/{total_pages}, {percentage}% - {message}")
            return True  # Continue processing
        
        # Create a cancellation checker function
        def cancellation_checker():
            return flatten_progress[job_id].get('cancelled', False)
        
        # Call flatten_pdf with progress callback and cancellation checker
        result = flatten_pdf(input_path, output_path, dpi=300, quality='high', jpeg_quality=95, 
                           progress_callback=progress_callback, cancellation_checker=cancellation_checker)
        
        # Check if operation was cancelled during processing
        if flatten_progress[job_id].get('cancelled', False):
            logging.info(f"Flatten job {job_id} was cancelled")
            # Mark as cancelled immediately for fast user feedback
            flatten_progress[job_id].update({
                'status': 'cancelled',
                'message': 'Flatten operation was cancelled',
                'percentage': 0
            })
        elif result:
            # Mark as complete
            flatten_progress[job_id] = {
                'status': 'complete',
                'current_page': flatten_progress[job_id].get('total_pages', 0),
                'total_pages': flatten_progress[job_id].get('total_pages', 0),
                'percentage': 100,
                'message': 'Complete!',
                'output_path': output_path
            }
        else:
            flatten_progress[job_id] = {
                'status': 'error',
                'message': 'Flatten failed',
                'percentage': 0
            }
    except Exception as e:
        flatten_progress[job_id] = {
            'status': 'error',
            'message': f'Error: {str(e)}',
            'percentage': 0
        }

@app.route('/api/flatten_pdf', methods=['POST'])
def api_flatten_pdf():
    try:
        input_pdf = request.files.get('input_pdf')
        output_filename = request.form.get('output_filename')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        
        if not input_pdf or not output_filename:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
            
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(input_pdf.filename))
        input_pdf.save(input_path)
        output_path = os.path.join(output_folder, secure_filename(output_filename))
        
        # Generate job ID for progress tracking
        job_id = str(uuid.uuid4())
        
        # Start flatten in background thread
        flatten_thread = threading.Thread(
            target=flatten_pdf_with_progress,
            args=(job_id, input_path, output_path)
        )
        flatten_thread.daemon = True
        flatten_thread.start()
        
        # Return job ID for progress tracking
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def split_pdf_with_progress(job_id, input_path, temp_dir, max_pages_per_chunk, max_chunk_size_mb, output_zip, output_folder):
    """Run PDF split with progress tracking"""
    try:
        
        # Initialize progress
        split_progress[job_id] = {
            'status': 'starting',
            'current_page': 0,
            'total_pages': 0,
            'current_chunk': 0,
            'total_chunks': 0,
            'percentage': 0,
            'message': 'Initializing...',
            'cancelled': False
        }
        
        # Call split function with progress callback - no throttling
        def progress_callback(current_page, total_pages, current_chunk, total_chunks, message):
            # Check for cancellation request - this is the primary cancellation check
            if split_progress[job_id].get('cancelled', False):
                logging.info(f"Split job {job_id} cancelled during progress callback")
                return False  # Signal cancellation to split function
            
            # Calculate progress as 70% for pages + 30% for chunks
            # This gives users feedback on both page processing AND chunk completion
            if total_pages > 0 and total_chunks > 0:
                page_progress = (current_page / total_pages) * 70
                chunk_progress = (current_chunk / total_chunks) * 30
                percentage = int(page_progress + chunk_progress)
            else:
                percentage = 0
            
            # Always update the progress dictionary with every callback
            split_progress[job_id].update({
                'status': 'processing',
                'current_page': current_page,
                'total_pages': total_pages,
                'current_chunk': current_chunk,
                'total_chunks': total_chunks,
                'percentage': percentage,
                'message': message
            })
            
            # Log every update for debugging
            logging.debug(f"Progress update: page {current_page}/{total_pages}, chunk {current_chunk}/{total_chunks}, {percentage}% - {message}")
            
            # Add special logging for saving messages to track the issue
            if 'Saving' in message:
                logging.info(f"PROGRESS DICT UPDATED WITH SAVING: {message} - page {current_page}/{total_pages}")
                logging.info(f"Frontend will see: {split_progress[job_id]}")
            
            return True  # Continue processing
        
        # Create a cancellation checker function that can be passed to split function
        def cancellation_checker():
            return split_progress[job_id].get('cancelled', False)
        
        # Call split_pdf with progress callback and cancellation checker
        if max_pages_per_chunk:
            result = split_func(input_path, temp_dir, max_pages_per_chunk=int(max_pages_per_chunk), 
                              progress_callback=progress_callback, cancellation_checker=cancellation_checker)
        else:
            result = split_func(input_path, temp_dir, max_chunk_size_mb=float(max_chunk_size_mb), 
                              progress_callback=progress_callback, cancellation_checker=cancellation_checker)
        
        # Check if operation was cancelled during processing
        if split_progress[job_id].get('cancelled', False):
            logging.info(f"Split job {job_id} was cancelled, cleaning up temp directory")
            # Mark as cancelled immediately for fast user feedback
            split_progress[job_id].update({
                'status': 'cancelled',
                'message': 'Split operation was cancelled',
                'percentage': 0
            })
            # Clean up temporary directory in background thread for faster response
            def cleanup_background():
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    logging.info(f"Background cleanup completed for job {job_id}")
                except Exception as e:
                    logging.error(f"Background cleanup failed for job {job_id}: {e}")
            
            cleanup_thread = threading.Thread(target=cleanup_background, daemon=True)
            cleanup_thread.start()
        elif result:
            # Check again before zipping in case cancellation happened during split
            if split_progress[job_id].get('cancelled', False):
                logging.info(f"Split job {job_id} cancelled before zipping")
                # Mark as cancelled immediately
                split_progress[job_id].update({
                    'status': 'cancelled',
                    'message': 'Split operation was cancelled',
                    'percentage': 0
                })
                # Background cleanup
                def cleanup_background():
                    try:
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                    except Exception as e:
                        logging.error(f"Background cleanup failed: {e}")
                
                cleanup_thread = threading.Thread(target=cleanup_background, daemon=True)
                cleanup_thread.start()
            else:
                # Update progress for zipping
                split_progress[job_id]['message'] = 'Creating zip file...'
                split_progress[job_id]['percentage'] = 95
                
                # Zip all PDFs in temp_dir
                zipname = output_zip
                if not zipname.lower().endswith('.zip'):
                    zipname += '.zip'
                zip_path = os.path.join(output_folder, secure_filename(zipname))
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for fname in os.listdir(temp_dir):
                        fpath = os.path.join(temp_dir, fname)
                        if os.path.isfile(fpath):
                            zipf.write(fpath, arcname=fname)
                
                shutil.rmtree(temp_dir)
                final_path = zip_path
                
                # Mark as complete
                split_progress[job_id] = {
                    'status': 'complete',
                    'current_page': split_progress[job_id]['total_pages'],
                    'total_pages': split_progress[job_id]['total_pages'],
                    'current_chunk': split_progress[job_id]['total_chunks'],
                    'total_chunks': split_progress[job_id]['total_chunks'],
                    'percentage': 100,
                    'message': 'Complete!',
                    'zipfile': final_path
                }
        else:
            # Clean up temp directory on failure
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            split_progress[job_id] = {
                'status': 'error',
                'message': 'Split failed',
                'percentage': 0
            }
    except Exception as e:
        # Clean up temp directory on exception
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        split_progress[job_id] = {
            'status': 'error',
            'message': f'Error: {str(e)}',
            'percentage': 0
        }

@app.route('/api/split_pdf', methods=['POST'])
def api_split_pdf():
    try:
        # Debug logging
        logging.debug(f"Request method: {request.method}")
        logging.debug(f"Request content type: {request.content_type}")
        logging.debug(f"Request headers: {dict(request.headers)}")
        logging.debug(f"Request files: {list(request.files.keys())}")
        logging.debug(f"Request form: {dict(request.form)}")
        
        input_pdf = request.files.get('input_pdf')
        output_zip = request.form.get('output_zip')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        max_pages = request.form.get('max_pages_per_chunk')
        max_size_mb = request.form.get('max_size_mb')  # New parameter
        
        logging.debug(f"Parsed values: input_pdf={input_pdf}, output_zip={output_zip}, max_pages={max_pages}, max_size_mb={max_size_mb}")
        
        if not input_pdf or not output_zip:
            logging.error(f"Missing required fields: input_pdf={bool(input_pdf)}, output_zip={bool(output_zip)}")
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
            
        # Must have either max_pages OR max_size_mb, but not both
        if not max_pages and not max_size_mb:
            return jsonify({'success': False, 'error': 'Either max pages or max size must be specified.'}), 400
        if max_pages and max_size_mb:
            return jsonify({'success': False, 'error': 'Cannot specify both max pages and max size.'}), 400
            
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(input_pdf.filename))
        input_pdf.save(input_path)
        
        # Create a temp output dir for split files
        temp_dir = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Start split in background thread
        split_thread = threading.Thread(
            target=split_pdf_with_progress,
            args=(job_id, input_path, temp_dir, max_pages, max_size_mb, output_zip, output_folder)
        )
        split_thread.daemon = True
        split_thread.start()
        
        # Return job ID for progress tracking
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/combine_pdfs', methods=['POST'])
def api_combine_pdfs():
    try:
        pdf_files = request.files.getlist('pdf_list')
        output_filename = request.form.get('output_filename')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        should_optimize = request.form.get('optimize', 'false').lower() == 'true'
        
        if not pdf_files or not output_filename:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        input_paths = []
        optimized_paths = []
        
        # Save all input files and optionally optimize them
        for i, f in enumerate(pdf_files):
            path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
            f.save(path)
            
            if should_optimize:
                # Create optimized version
                optimized_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_optimized_{i}_{secure_filename(f.filename)}")
                optimize_result = optimize_pdf(path, optimized_path, aggressive=False)
                if not optimize_result:
                    # Clean up any previously created files
                    for fp in optimized_paths:
                        if os.path.exists(fp):
                            os.unlink(fp)
                    return jsonify({'success': False, 'error': f'Optimization failed for file: {f.filename}'})
                
                input_paths.append(optimized_path)
                optimized_paths.append(optimized_path)
            else:
                input_paths.append(path)
        
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        output_path = os.path.join(output_folder, secure_filename(output_filename))
        
        result = combine_pdfs(input_paths, output_path)
        
        # Clean up temporary optimized files
        for fp in optimized_paths:
            if os.path.exists(fp):
                os.unlink(fp)
        
        if result:
            return jsonify({'success': True, 'filename': output_path, 'error': None})
        else:
            return jsonify({'success': False, 'error': 'Combine failed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimize_pdf', methods=['POST'])
def api_optimize_pdf():
    try:
        input_pdf = request.files.get('input_pdf')
        output_filename = request.form.get('output_filename')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        aggressive = request.form.get('aggressive') == 'true'
        
        if not input_pdf or not output_filename:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
            
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(input_pdf.filename))
        input_pdf.save(input_path)
        output_path = os.path.join(output_folder, secure_filename(output_filename))
        
        result = optimize_pdf(input_path, output_path, aggressive=aggressive)
        if result:
            return jsonify({'success': True, 'filename': output_path, 'error': None})
        else:
            return jsonify({'success': False, 'error': 'Optimization failed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/extract_pages', methods=['POST'])
def api_extract_pages():
    try:
        input_pdf = request.files.get('input_pdf')
        output_filename = request.form.get('output_filename')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        pages_string = request.form.get('pages')
        
        if not input_pdf or not output_filename or not pages_string:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        
        # Parse page numbers using the same logic as extract_pages.py
        from manage_pdfs.extract_pages import parse_page_numbers
        page_numbers = parse_page_numbers(pages_string)
        
        if not page_numbers:
            return jsonify({'success': False, 'error': 'No valid page numbers provided.'})
        
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
            
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(input_pdf.filename))
        input_pdf.save(input_path)
        output_path = os.path.join(output_folder, secure_filename(output_filename))
        
        result = extract_pages(input_path, output_path, page_numbers)
        if result:
            return jsonify({'success': True, 'filename': output_path, 'error': None})
        else:
            return jsonify({'success': False, 'error': 'Page extraction failed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/split_progress/<job_id>')
def get_split_progress(job_id):
    """Get progress for a split job"""
    if job_id in split_progress:
        return jsonify(split_progress[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/cancel_split/<job_id>', methods=['POST'])
def cancel_split(job_id):
    """Cancel a split job"""
    try:
        if job_id in split_progress:
            # Mark the job as cancelled
            split_progress[job_id]['cancelled'] = True
            split_progress[job_id]['status'] = 'cancelled'
            split_progress[job_id]['message'] = 'Cancelling...'
            
            logging.info(f"Split job {job_id} marked for cancellation")
            return jsonify({'success': True, 'message': 'Cancellation requested'})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        logging.error(f"Error cancelling split job {job_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/flatten_progress/<job_id>')
def get_flatten_progress(job_id):
    """Get progress for a flatten job"""
    if job_id in flatten_progress:
        return jsonify(flatten_progress[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/cancel_flatten/<job_id>', methods=['POST'])
def cancel_flatten(job_id):
    """Cancel a flatten job"""
    try:
        if job_id in flatten_progress:
            # Mark the job as cancelled
            flatten_progress[job_id]['cancelled'] = True
            flatten_progress[job_id]['status'] = 'cancelled'
            flatten_progress[job_id]['message'] = 'Cancelling...'
            
            logging.info(f"Flatten job {job_id} marked for cancellation")
            return jsonify({'success': True, 'message': 'Cancellation requested'})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        logging.error(f"Error cancelling flatten job {job_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download route for processed files"""
    try:
        # Secure the filename and check if file exists
        safe_filename = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        if not os.path.exists(file_path):
            return "File not found", 404
            
        return send_from_directory(app.config['UPLOAD_FOLDER'], safe_filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Download error: {str(e)}")
        return "Download failed", 500

if __name__ == '__main__':
    app.run(debug=DEBUG)