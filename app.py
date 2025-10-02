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

DEBUG = True

# Configure logging
if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a temporary directory for file operations
TEMP_FOLDER = tempfile.mkdtemp(prefix='pdf_management_')
logging.debug(f"Created temporary folder: {TEMP_FOLDER}")

# Ensure cleanup on exit
def cleanup_temp_folder():
    if os.path.exists(TEMP_FOLDER):
        shutil.rmtree(TEMP_FOLDER, ignore_errors=True)
        logging.debug(f"Cleaned up temporary folder: {TEMP_FOLDER}")

atexit.register(cleanup_temp_folder)

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session
app.config['UPLOAD_FOLDER'] = TEMP_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'svg'}

# In-memory job state (for demo only)
redaction_jobs = {}

# Global redaction service instances (keyed by PDF filename)
redaction_services = {}

# Split progress tracking
split_progress = {}

### Page Routes ####

@app.route('/')
def index():
    return render_template('index.html')

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
        should_flatten = request.form.get('flatten', 'false').lower() == 'true'
        
        if not input_pdf or not output_filename:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
            
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(input_pdf.filename))
        input_pdf.save(input_path)
        
        # If flattening is requested, flatten first then compress
        if should_flatten:
            temp_flattened_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_flattened_{secure_filename(input_pdf.filename)}")
            flatten_result = flatten_pdf(input_path, temp_flattened_path, 
                                       remove_links=False, remove_annotations=True, flatten_transparency=False)
            if not flatten_result:
                return jsonify({'success': False, 'error': 'Flattening failed.'})
            # Use flattened file as input for compression
            compress_input_path = temp_flattened_path
        else:
            compress_input_path = input_path
        
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(output_filename))
        result = compress_pdf(compress_input_path, output_path)
        
        # Clean up temporary flattened file if it was created
        if should_flatten and os.path.exists(temp_flattened_path):
            os.unlink(temp_flattened_path)
        
        if result:
            rel_path = os.path.relpath(output_path, app.config['UPLOAD_FOLDER'])
            return jsonify({'success': True, 'filename': rel_path, 'error': None})
        else:
            return jsonify({'success': False, 'error': 'Compression failed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/flatten_pdf', methods=['POST'])
def api_flatten_pdf():
    try:
        input_pdf = request.files.get('input_pdf')
        output_filename = request.form.get('output_filename')
        remove_links = request.form.get('remove_links', 'false').lower() == 'true'
        remove_annotations = request.form.get('remove_annotations', 'true').lower() == 'true'
        flatten_transparency = request.form.get('flatten_transparency', 'false').lower() == 'true'
        
        if not input_pdf or not output_filename:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
            
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(input_pdf.filename))
        input_pdf.save(input_path)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(output_filename))
        
        result = flatten_pdf(input_path, output_path, remove_links=remove_links, remove_annotations=remove_annotations, flatten_transparency=flatten_transparency)
        if result:
            rel_path = os.path.relpath(output_path, app.config['UPLOAD_FOLDER'])
            return jsonify({'success': True, 'filename': rel_path, 'error': None})
        else:
            return jsonify({'success': False, 'error': 'Flattening failed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def split_pdf_with_progress(job_id, input_path, temp_dir, max_pages_per_chunk, max_chunk_size_mb, output_zip):
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
            'message': 'Initializing...'
        }
        
        # Call split function with progress callback - no throttling
        def progress_callback(current_page, total_pages, current_chunk, total_chunks, message):
            # Always update the progress dictionary with every callback
            percentage = int((current_page / max(total_pages, 1)) * 100)
            split_progress[job_id] = {
                'status': 'processing',
                'current_page': current_page,
                'total_pages': total_pages,
                'current_chunk': current_chunk,
                'total_chunks': total_chunks,
                'percentage': percentage,
                'message': message
            }
            
            # Log every update for debugging
            logging.debug(f"Progress update: page {current_page}/{total_pages}, chunk {current_chunk}/{total_chunks}, {percentage}% - {message}")
            
            # Add special logging for saving messages to track the issue
            if 'Saving' in message:
                logging.info(f"PROGRESS DICT UPDATED WITH SAVING: {message} - page {current_page}/{total_pages}")
                logging.info(f"Frontend will see: {split_progress[job_id]}")
        
        # Call split_pdf with progress callback
        if max_pages_per_chunk:
            result = split_func(input_path, temp_dir, max_pages_per_chunk=int(max_pages_per_chunk), progress_callback=progress_callback)
        else:
            result = split_func(input_path, temp_dir, max_chunk_size_mb=float(max_chunk_size_mb), progress_callback=progress_callback)
        
        if result:
            # Update progress for zipping
            split_progress[job_id]['message'] = 'Creating zip file...'
            split_progress[job_id]['percentage'] = 95
            
            # Zip all PDFs in temp_dir
            zipname = output_zip
            if not zipname.lower().endswith('.zip'):
                zipname += '.zip'
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(zipname))
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for fname in os.listdir(temp_dir):
                    fpath = os.path.join(temp_dir, fname)
                    if os.path.isfile(fpath):
                        zipf.write(fpath, arcname=fname)
            
            shutil.rmtree(temp_dir)
            rel_path = os.path.relpath(zip_path, app.config['UPLOAD_FOLDER'])
            
            # Mark as complete
            split_progress[job_id] = {
                'status': 'complete',
                'current_page': split_progress[job_id]['total_pages'],
                'total_pages': split_progress[job_id]['total_pages'],
                'current_chunk': split_progress[job_id]['total_chunks'],
                'total_chunks': split_progress[job_id]['total_chunks'],
                'percentage': 100,
                'message': 'Complete!',
                'zipfile': rel_path
            }
        else:
            split_progress[job_id] = {
                'status': 'error',
                'message': 'Split failed',
                'percentage': 0
            }
    except Exception as e:
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
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Start split in background thread
        split_thread = threading.Thread(
            target=split_pdf_with_progress,
            args=(job_id, input_path, temp_dir, max_pages, max_size_mb, output_zip)
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
        should_flatten = request.form.get('flatten', 'false').lower() == 'true'
        
        if not pdf_files or not output_filename:
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        
        input_paths = []
        flattened_paths = []
        
        # Save all input files and optionally flatten them
        for i, f in enumerate(pdf_files):
            path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
            f.save(path)
            
            if should_flatten:
                # Create flattened version
                flattened_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_flattened_{i}_{secure_filename(f.filename)}")
                flatten_result = flatten_pdf(path, flattened_path, 
                                           remove_links=False, remove_annotations=True, flatten_transparency=False)
                if not flatten_result:
                    # Clean up any previously created files
                    for fp in flattened_paths:
                        if os.path.exists(fp):
                            os.unlink(fp)
                    return jsonify({'success': False, 'error': f'Flattening failed for file: {f.filename}'})
                
                input_paths.append(flattened_path)
                flattened_paths.append(flattened_path)
            else:
                input_paths.append(path)
        
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(output_filename))
        
        result = combine_pdfs(input_paths, output_path)
        
        # Clean up temporary flattened files
        for fp in flattened_paths:
            if os.path.exists(fp):
                os.unlink(fp)
        
        if result:
            rel_path = os.path.relpath(output_path, app.config['UPLOAD_FOLDER'])
            return jsonify({'success': True, 'filename': rel_path, 'error': None})
        else:
            return jsonify({'success': False, 'error': 'Combine failed.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/split_progress/<job_id>')
def get_split_progress(job_id):
    """Get progress for a split job"""
    if job_id in split_progress:
        return jsonify(split_progress[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

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