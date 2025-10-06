
import os
import threading
import shutil
import zipfile
import logging
import time
from werkzeug.utils import secure_filename
from manage_pdfs.flatten import flatten_pdf
from manage_pdfs.split import split_pdf_with_progress as split_func
from manage_pdfs.extract_pages import extract_pages
from manage_pdfs.optimize import optimize_pdf
from manage_pdfs.compress import compress_pdf


def flatten_pdf_with_progress(job_id, input_path, output_path, flatten_progress):
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


def split_pdf_with_progress(job_id, input_path, temp_dir, max_pages_per_chunk, max_chunk_size_mb, output_zip, output_folder, split_progress):
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


def extract_pages_with_progress(job_id, input_path, output_path, page_numbers, extract_progress):
    """Run PDF page extraction with progress tracking"""
    try:
        # Check if job was already cancelled before we even started
        if extract_progress[job_id].get('cancelled', False):
            logging.info(f"Extract job {job_id} was cancelled before background thread started")
            extract_progress[job_id].update({
                'status': 'cancelled',
                'message': 'Page extraction was cancelled'
            })
            return
        
        # Add a small delay to allow frontend cancellation during startup
        time.sleep(0.1)  # 100ms delay
        
        # Check again after delay - this catches cancellations during startup
        if extract_progress[job_id].get('cancelled', False):
            logging.info(f"Extract job {job_id} was cancelled during startup delay")
            extract_progress[job_id].update({
                'status': 'cancelled',
                'message': 'Page extraction was cancelled'
            })
            return
        
        # Update to processing status
        extract_progress[job_id].update({
            'status': 'processing',
            'message': 'Extracting pages from PDF...'
        })
        
        # Final check for cancellation before starting actual work
        if extract_progress[job_id].get('cancelled', False):
            logging.info(f"Extract job {job_id} cancelled before starting extraction")
            extract_progress[job_id].update({
                'status': 'cancelled',
                'message': 'Page extraction was cancelled'
            })
            return
        
        # Create a cancellation checker function
        def cancellation_checker():
            return extract_progress[job_id].get('cancelled', False)
        
        # Call extract_pages function with cancellation checker
        result = extract_pages(input_path, output_path, page_numbers, cancellation_checker=cancellation_checker)
        
        # Check if operation was cancelled during processing
        if extract_progress[job_id].get('cancelled', False):
            logging.info(f"Extract job {job_id} was cancelled")
            extract_progress[job_id].update({
                'status': 'cancelled',
                'message': 'Page extraction was cancelled'
            })
        elif result:
            # Mark as complete
            extract_progress[job_id] = {
                'status': 'complete',
                'message': 'Page extraction completed successfully!',
                'filename': output_path
            }
        else:
            extract_progress[job_id] = {
                'status': 'error',
                'message': 'Page extraction failed'
            }
    except Exception as e:
        extract_progress[job_id] = {
            'status': 'error',
            'message': f'Error: {str(e)}'
        }


def optimize_pdf_with_progress(job_id, input_path, output_path, aggressive, optimize_progress):
    """Run PDF optimization with progress tracking"""
    try:
        # Check if job was already cancelled before we even started
        if optimize_progress[job_id].get('cancelled', False):
            logging.info(f"Optimize job {job_id} was cancelled before background thread started")
            optimize_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF optimization was cancelled'
            })
            return
        
        # Add a small delay to allow frontend cancellation during startup
        time.sleep(0.1)  # 100ms delay
        
        # Check again after delay - this catches cancellations during startup
        if optimize_progress[job_id].get('cancelled', False):
            logging.info(f"Optimize job {job_id} was cancelled during startup delay")
            optimize_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF optimization was cancelled'
            })
            return
        
        # Update to processing status
        optimize_progress[job_id].update({
            'status': 'processing',
            'message': 'Optimizing PDF file...'
        })
        
        # Final check for cancellation before starting actual work
        if optimize_progress[job_id].get('cancelled', False):
            logging.info(f"Optimize job {job_id} cancelled before starting optimization")
            optimize_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF optimization was cancelled'
            })
            return
        
        # Call optimize_pdf function (no cancellation checker support in current implementation)
        result = optimize_pdf(input_path, output_path, aggressive)
        
        # Check if operation was cancelled during processing
        if optimize_progress[job_id].get('cancelled', False):
            logging.info(f"Optimize job {job_id} was cancelled")
            optimize_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF optimization was cancelled'
            })
        elif result:
            # Mark as complete
            optimize_progress[job_id] = {
                'status': 'complete',
                'message': 'PDF optimization completed successfully!',
                'filename': output_path
            }
        else:
            optimize_progress[job_id] = {
                'status': 'error',
                'message': 'PDF optimization failed'
            }
    except Exception as e:
        optimize_progress[job_id] = {
            'status': 'error',
            'message': f'Error: {str(e)}'
        }


def compress_pdf_with_progress(job_id, input_path, output_path, should_optimize, compress_progress):
    """Run PDF compression with progress tracking"""
    try:
        # Check if job was already cancelled before we even started
        if compress_progress[job_id].get('cancelled', False):
            logging.info(f"Compress job {job_id} was cancelled before background thread started")
            compress_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF compression was cancelled'
            })
            return
        
        # Add a small delay to allow frontend cancellation during startup
        time.sleep(0.1)  # 100ms delay
        
        # Check again after delay - this catches cancellations during startup
        if compress_progress[job_id].get('cancelled', False):
            logging.info(f"Compress job {job_id} was cancelled during startup delay")
            compress_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF compression was cancelled'
            })
            return
        
        # Update to processing status
        compress_progress[job_id].update({
            'status': 'processing',
            'message': 'Preparing PDF for compression...'
        })
        
        # Final check for cancellation before starting actual work
        if compress_progress[job_id].get('cancelled', False):
            logging.info(f"Compress job {job_id} cancelled before starting compression")
            compress_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF compression was cancelled'
            })
            return
        
        # Handle optimization if requested
        temp_optimized_path = None
        if should_optimize:
            # Update status for optimization phase
            compress_progress[job_id].update({
                'status': 'processing',
                'message': 'Optimizing PDF before compression...'
            })
            
            # Log optimization start
            logging.info(f"Starting optimization for job {job_id}")
            
            # Check for cancellation before optimization
            if compress_progress[job_id].get('cancelled', False):
                logging.info(f"Compress job {job_id} cancelled before optimization")
                compress_progress[job_id].update({
                    'status': 'cancelled',
                    'message': 'PDF compression was cancelled'
                })
                return
            
            # Create temporary optimized file
            temp_optimized_path = input_path.replace('.pdf', '_temp_optimized.pdf')
            optimize_result = optimize_pdf(input_path, temp_optimized_path, aggressive=False)
            
            logging.info(f"Optimization completed for job {job_id}, result: {optimize_result}")
            
            if not optimize_result:
                compress_progress[job_id] = {
                    'status': 'error',
                    'message': 'Optimization step failed'
                }
                return
            
            compress_input_path = temp_optimized_path
        else:
            compress_input_path = input_path
        
        # Update status for compression phase
        compress_progress[job_id].update({
            'status': 'processing',
            'message': 'Compressing PDF file...'
        })
        
        # Add a small delay to ensure the UI sees the compression message
        time.sleep(0.5)  # 500ms delay to ensure UI polling catches the message update
        
        # Log the compression start for debugging
        logging.info(f"Starting compression for job {job_id}: {compress_input_path} -> {output_path}")

        # Final check for cancellation before compression
        if compress_progress[job_id].get('cancelled', False):
            logging.info(f"Compress job {job_id} cancelled before compression")
            # Clean up temp optimized file if it exists
            if should_optimize and temp_optimized_path and os.path.exists(temp_optimized_path):
                os.unlink(temp_optimized_path)
            compress_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF compression was cancelled'
            })
            return
        
        # Call compress_pdf function (no cancellation checker support in current implementation)
        result = compress_pdf(compress_input_path, output_path)
        
        # Log compression completion
        logging.info(f"Compression completed for job {job_id}, result: {result}")
        
        # Clean up temporary optimized file if it was created
        if should_optimize and temp_optimized_path and os.path.exists(temp_optimized_path):
            try:
                os.unlink(temp_optimized_path)
            except Exception as e:
                logging.warning(f"Failed to cleanup temp file {temp_optimized_path}: {e}")
        
        # Check if operation was cancelled during processing
        if compress_progress[job_id].get('cancelled', False):
            logging.info(f"Compress job {job_id} was cancelled")
            compress_progress[job_id].update({
                'status': 'cancelled',
                'message': 'PDF compression was cancelled'
            })
        elif result:
            # Mark as complete
            compress_progress[job_id] = {
                'status': 'complete',
                'message': 'PDF compression completed successfully!',
                'filename': output_path
            }
        else:
            compress_progress[job_id] = {
                'status': 'error',
                'message': 'PDF compression failed'
            }
    except Exception as e:
        compress_progress[job_id] = {
            'status': 'error',
            'message': f'Error: {str(e)}'
        }
