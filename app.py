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
from utils.process_with_progress import flatten_pdf_with_progress, split_pdf_with_progress, extract_pages_with_progress, optimize_pdf_with_progress, compress_pdf_with_progress, combine_pdf_with_progress
from utils.filename_utils import make_unique_filename, make_unique_zip_filename

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

# Extract progress tracking  
extract_progress = {}

# Optimize progress tracking
optimize_progress = {}

# Compress progress tracking
compress_progress = {}

# Combine progress tracking
combine_progress = {}

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
        output_path = os.path.join(output_folder, secure_filename(output_filename))
        # Make filename unique if it already exists
        output_path = make_unique_filename(output_path)
        
        # Generate job ID for progress tracking
        job_id = str(uuid.uuid4())
        
        # Initialize the progress entry before starting thread
        compress_progress[job_id] = {
            'status': 'starting',
            'message': 'Starting PDF compression...',
            'cancelled': False
        }
        
        # Start compress in background thread
        compress_thread = threading.Thread(
            target=compress_pdf_with_progress,
            args=(job_id, input_path, output_path, should_optimize, compress_progress)
        )
        compress_thread.daemon = True
        compress_thread.start()
        
        # Return job ID for progress tracking
        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        # Make filename unique if it already exists
        output_path = make_unique_filename(output_path)
        # Generate job ID for progress tracking
        job_id = str(uuid.uuid4())
        
        # Start flatten in background thread
        flatten_thread = threading.Thread(
            target=flatten_pdf_with_progress,
            args=(job_id, input_path, output_path, flatten_progress)
        )
        flatten_thread.daemon = True
        flatten_thread.start()
        
        # Return job ID for progress tracking
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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

        # Make zip filename unique if it already exists
        zip_path = os.path.join(output_folder, secure_filename(output_zip))
        output_zip_path = make_unique_zip_filename(zip_path)
        # Extract just the filename for passing to the background function
        output_zip = os.path.basename(output_zip_path)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Start split in background thread
        split_thread = threading.Thread(
            target=split_pdf_with_progress,
            args=(job_id, input_path, temp_dir, max_pages, max_size_mb, output_zip, output_folder, split_progress)
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
        # Debug logging
        logging.debug(f"Request method: {request.method}")
        logging.debug(f"Request content type: {request.content_type}")
        logging.debug(f"Request files: {list(request.files.keys())}")
        logging.debug(f"Request form: {dict(request.form)}")
        
        pdf_files = request.files.getlist('pdf_list')
        output_filename = request.form.get('output_filename')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        should_optimize = request.form.get('optimize', 'false').lower() == 'true'
        
        logging.debug(f"pdf_files count: {len(pdf_files) if pdf_files else 0}")
        logging.debug(f"output_filename: {output_filename}")
        logging.debug(f"output_folder: {output_folder}")
        logging.debug(f"should_optimize: {should_optimize}")
        
        if not pdf_files or not output_filename:
            logging.error(f"Missing required fields - pdf_files: {len(pdf_files) if pdf_files else 0}, output_filename: {output_filename}")
            return jsonify({'success': False, 'error': 'Missing required fields.'}), 400
        
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Save all input files to temporary locations
        input_paths = []
        for i, f in enumerate(pdf_files):
            path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
            f.save(path)
            input_paths.append(path)
        
        output_path = os.path.join(output_folder, secure_filename(output_filename))
        # Make filename unique if it already exists
        output_path = make_unique_filename(output_path)
        
        # Generate job ID for progress tracking
        job_id = str(uuid.uuid4())
        
        # Initialize the progress entry before starting thread
        combine_progress[job_id] = {
            'status': 'starting',
            'message': 'Starting PDF combination...',
            'cancelled': False
        }
        
        # Start combine in background thread
        combine_thread = threading.Thread(
            target=combine_pdf_with_progress,
            args=(job_id, input_paths, output_path, should_optimize, combine_progress)
        )
        combine_thread.daemon = True
        combine_thread.start()
        
        # Return job ID for progress tracking
        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimize_pdf', methods=['POST'])
def api_optimize_pdf():
    try:
        input_pdf = request.files.get('input_pdf')
        output_filename = request.form.get('output_filename')
        output_folder = request.form.get('output_folder', app.config['OUTPUT_FOLDER'])
        aggressive = True # request.form.get('aggressive') == 'true'
        
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
        # Make filename unique if it already exists
        output_path = make_unique_filename(output_path)
        
        # Generate job ID for progress tracking
        job_id = str(uuid.uuid4())
        
        # Initialize the progress entry before starting thread
        optimize_progress[job_id] = {
            'status': 'starting',
            'message': 'Starting PDF optimization...',
            'cancelled': False
        }
        
        # Start optimize in background thread
        optimize_thread = threading.Thread(
            target=optimize_pdf_with_progress,
            args=(job_id, input_path, output_path, aggressive, optimize_progress)
        )
        optimize_thread.daemon = True
        optimize_thread.start()
        
        # Return job ID for progress tracking
        return jsonify({'success': True, 'job_id': job_id})
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
        # Make filename unique if it already exists
        output_path = make_unique_filename(output_path)
        # Generate job ID for progress tracking
        job_id = str(uuid.uuid4())
        
        # Initialize the progress entry before starting thread
        extract_progress[job_id] = {
            'status': 'starting',
            'message': 'Starting page extraction...',
            'cancelled': False
        }
        
        # Start extract in background thread
        extract_thread = threading.Thread(
            target=extract_pages_with_progress,
            args=(job_id, input_path, output_path, page_numbers, extract_progress)
        )
        extract_thread.daemon = True
        extract_thread.start()
        
        # Return job ID for progress tracking
        return jsonify({'success': True, 'job_id': job_id})
        
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

@app.route('/api/extract_progress/<job_id>')
def get_extract_progress(job_id):
    """Get progress for an extract job"""
    if job_id in extract_progress:
        return jsonify(extract_progress[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/cancel_extract/<job_id>', methods=['POST'])
def cancel_extract(job_id):
    """Cancel an extract job"""
    try:
        if job_id in extract_progress:
            # Mark the job as cancelled
            extract_progress[job_id]['cancelled'] = True
            extract_progress[job_id]['status'] = 'cancelled'
            extract_progress[job_id]['message'] = 'Cancelling...'
            logging.info(f"Marked extract job {job_id} for cancellation")
            return jsonify({'success': True, 'message': 'Job marked for cancellation'})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        logging.error(f"Error cancelling extract job {job_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimize_progress/<job_id>')
def get_optimize_progress(job_id):
    """Get progress for an optimize job"""
    if job_id in optimize_progress:
        return jsonify(optimize_progress[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/cancel_optimize/<job_id>', methods=['POST'])
def cancel_optimize(job_id):
    """Cancel an optimize job"""
    try:
        if job_id in optimize_progress:
            # Mark the job as cancelled
            optimize_progress[job_id]['cancelled'] = True
            optimize_progress[job_id]['status'] = 'cancelled'
            optimize_progress[job_id]['message'] = 'Cancelling...'
            logging.info(f"Marked optimize job {job_id} for cancellation")
            return jsonify({'success': True, 'message': 'Job marked for cancellation'})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        logging.error(f"Error cancelling optimize job {job_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/compress_progress/<job_id>')
def get_compress_progress(job_id):
    """Get progress for a compress job"""
    if job_id in compress_progress:
        return jsonify(compress_progress[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/cancel_compress/<job_id>', methods=['POST'])
def cancel_compress(job_id):
    """Cancel a compress job"""
    try:
        if job_id in compress_progress:
            # Mark the job as cancelled
            compress_progress[job_id]['cancelled'] = True
            compress_progress[job_id]['status'] = 'cancelled'
            compress_progress[job_id]['message'] = 'Cancelling...'
            logging.info(f"Marked compress job {job_id} for cancellation")
            return jsonify({'success': True, 'message': 'Job marked for cancellation'})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        logging.error(f"Error cancelling compress job {job_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/combine_progress/<job_id>')
def get_combine_progress(job_id):
    """Get progress for a combine job"""
    if job_id in combine_progress:
        return jsonify(combine_progress[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/api/cancel_combine/<job_id>', methods=['POST'])
def cancel_combine(job_id):
    """Cancel a combine job"""
    try:
        if job_id in combine_progress:
            # Mark the job as cancelled
            combine_progress[job_id]['cancelled'] = True
            combine_progress[job_id]['status'] = 'cancelled'
            combine_progress[job_id]['message'] = 'Cancelling...'
            logging.info(f"Marked combine job {job_id} for cancellation")
            return jsonify({'success': True, 'message': 'Job marked for cancellation'})
        else:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
    except Exception as e:
        logging.error(f"Error cancelling combine job {job_id}: {str(e)}")
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