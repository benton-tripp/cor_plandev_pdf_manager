import fitz # PyMuPDF
import os
import sys
import logging
import time

logging.basicConfig(level=logging.INFO)

def create_size_based_chunks(doc, max_chunk_size_mb):
    """Create page ranges based on estimated file size using fast calculation"""
    max_chunk_bytes = max_chunk_size_mb * 1024 * 1024
    
    # Fast estimation: use file size divided by page count to get average page size
    try:
        if hasattr(doc, 'name') and doc.name and os.path.exists(doc.name):
            original_size = os.path.getsize(doc.name)
        else:
            original_size = 0
    except:
        original_size = 0
    
    if original_size == 0:
        # Fallback: estimate based on typical PDF sizes
        avg_page_size = 1.5 * 1024 * 1024  # 1.5MB per page estimate
        logging.warning("Could not determine file size, using 1.5MB per page estimate")
    else:
        avg_page_size = original_size / doc.page_count
        logging.info(f"File size: {original_size/1024/1024:.1f}MB, {doc.page_count} pages")
    
    # Calculate approximate pages per chunk
    pages_per_chunk = max(1, int(max_chunk_bytes / avg_page_size))
    
    logging.info(f"Fast size estimation: {avg_page_size/1024/1024:.1f}MB avg per page, ~{pages_per_chunk} pages per {max_chunk_size_mb}MB chunk")
    
    # Create chunks using this estimate
    chunks = []
    total_pages = doc.page_count
    
    for start_page in range(0, total_pages, pages_per_chunk):
        end_page = min(start_page + pages_per_chunk, total_pages)
        chunks.append(range(start_page, end_page))
        estimated_size = (end_page - start_page) * avg_page_size / 1024 / 1024
        logging.debug(f"Created chunk: pages {start_page+1}-{end_page} (~{estimated_size:.1f}MB estimated)")
    
    return chunks

def split_pdf_with_progress(input_pdf, output_dir, max_pages_per_chunk=None, max_chunk_size_mb=None, no_overwrite=False, progress_callback=None):
    """Split PDF with progress tracking"""
    if not os.path.exists(input_pdf):
        logging.error(f"Input file '{input_pdf}' does not exist.")
        return None
    if not os.path.isdir(output_dir):
        logging.error(f"Output directory '{output_dir}' does not exist.")
        return None
    if max_pages_per_chunk is None and max_chunk_size_mb is None:
        logging.error("Either max_pages_per_chunk or max_chunk_size_mb must be specified.")
        return None
    if max_pages_per_chunk is not None and (not isinstance(max_pages_per_chunk, int) or max_pages_per_chunk < 1):
        logging.error("max_pages_per_chunk must be a positive integer.")
        return None
    if max_chunk_size_mb is not None and (not isinstance(max_chunk_size_mb, (int, float)) or max_chunk_size_mb <= 0):
        logging.error("max_chunk_size_mb must be a positive number.")
        return None
    
    try:
        doc = fitz.open(input_pdf)
        # Log original file size
        original_size = os.path.getsize(input_pdf) / 1024
        logging.info(f"Opened PDF '{input_pdf}' with {doc.page_count} pages ({original_size:,} KB)")
        total_pages = doc.page_count
        
        # Only check page count limit when using page-based splitting
        if max_pages_per_chunk is not None and total_pages <= max_pages_per_chunk:
            logging.warning(f"PDF has only {total_pages} pages, less than or equal to max_pages_per_chunk ({max_pages_per_chunk}). No split performed.")
            return None
            
        base_name = os.path.basename(input_pdf)
        
        # Progress callback for chunk calculation
        if progress_callback:
            progress_callback(0, total_pages, 0, 0, "Calculating chunks...")
        
        # Create chunks based on the specified method
        if max_pages_per_chunk is not None:
            # Page-based chunking (original method)
            chunks = [range(i, min(i+max_pages_per_chunk, total_pages)) for i in range(0, total_pages, max_pages_per_chunk)]
            logging.info(f"Using page-based chunking: {max_pages_per_chunk} pages per chunk")
        else:
            # Size-based chunking (new method)
            chunks = create_size_based_chunks(doc, max_chunk_size_mb)
            logging.info(f"Using size-based chunking: ~{max_chunk_size_mb}MB per chunk")
        
        total_chunks = len(chunks)
        current_page_count = 0
        
        # Initial progress callback
        if progress_callback:
            progress_callback(0, total_pages, 0, total_chunks, "Starting PDF split...")
        
        # Calculate padding width based on total number of chunks
        padding_width = len(str(len(chunks)))
        chunks_completed = 0  # Track completed chunks separately
        for idx, page_range in enumerate(chunks, 1):
            # Zero-pad the index for proper sorting
            padded_idx = str(idx).zfill(padding_width)
            out_path = os.path.join(output_dir, f"{padded_idx}_{base_name}")
            
            # Check if file already exists and no-overwrite is enabled
            if no_overwrite and os.path.exists(out_path):
                file_size = os.path.getsize(out_path)
                logging.info(f"Skipping chunk {idx}: {out_path} already exists ({file_size/1024:,} KB)")
                current_page_count += len(page_range)
                chunks_completed += 1
                if progress_callback:
                    progress_callback(current_page_count, total_pages, chunks_completed, total_chunks, f"Skipped chunk {idx} (already exists)")
                continue
            
            new_doc = fitz.open()
            
            # Progress callback for starting this chunk
            if progress_callback:
                progress_callback(current_page_count, total_pages, chunks_completed, total_chunks, f"Starting chunk {idx} ({len(page_range)} pages)")
            
            # Insert pages one at a time to better control image duplication
            # This preserves links and annotations while minimizing duplication
            
            for page_num in page_range:
                logging.debug(f"Inserting page {page_num + 1} into chunk {idx}")
                
                # Insert each page individually to minimize cross-page image duplication
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num, 
                                 links=True, annots=True)
                
                # Progress callback AFTER each page insertion - now we've actually processed it
                current_page_count += 1
                if progress_callback:
                    progress_callback(current_page_count, total_pages, chunks_completed, total_chunks, f"Processed page {current_page_count} for chunk {idx}")
            
            # Skip image analysis - it's too slow for large embedded images
            logging.debug(f"Completed inserting all pages for chunk {idx}")
            
            # Progress callback for saving - ensure this gets sent and processed
            if progress_callback:
                progress_callback(current_page_count, total_pages, chunks_completed, total_chunks, f"Saving chunk {idx}...")
                # Force immediate logging to verify this callback is made
                logging.info(f"SAVING CALLBACK SENT: Saving chunk {idx}... (page {current_page_count}/{total_pages})")
                # Add a small delay to ensure this callback gets processed before the next one
                time.sleep(0.1)  # 100ms delay to ensure frontend can poll this state
            
            # Save with deduplication to prevent image bloat
            # garbage=4 removes duplicate objects without changing image quality
            # This is key to preventing the size explosion while preserving content
            new_doc.save(out_path, garbage=4, deflate=True, clean=True)
            
            new_doc.close()
            
            # Log file size for monitoring
            file_size = os.path.getsize(out_path)
            logging.info(f"Saved chunk {idx}: {out_path} ({len(page_range)} pages, {file_size/1024:,} KB)")
            
            # Increment chunks completed AFTER successful save
            chunks_completed += 1
            
            # Progress callback for completed chunk - now this chunk is complete
            if progress_callback:
                progress_callback(current_page_count, total_pages, chunks_completed, total_chunks, f"Completed chunk {idx} ({len(page_range)} pages)")
                logging.info(f"Chunk {idx} completed - {chunks_completed}/{total_chunks} chunks done")
        
        doc.close()
        
        # Final progress callback
        if progress_callback:
            progress_callback(total_pages, total_pages, chunks_completed, total_chunks, "Split complete!")
        
        return True
    except Exception as e:
        logging.error(f"Error splitting PDF: {e}")
        if progress_callback:
            progress_callback(0, 0, 0, 0, f"Error: {str(e)}")
        return None

def split_pdf(input_pdf, output_dir, max_pages_per_chunk=None, max_chunk_size_mb=None, no_overwrite=False):
    if not os.path.exists(input_pdf):
        logging.error(f"Input file '{input_pdf}' does not exist.")
        return None
    if not os.path.isdir(output_dir):
        logging.error(f"Output directory '{output_dir}' does not exist.")
        return None
    if max_pages_per_chunk is None and max_chunk_size_mb is None:
        logging.error("Either max_pages_per_chunk or max_chunk_size_mb must be specified.")
        return None
    if max_pages_per_chunk is not None and (not isinstance(max_pages_per_chunk, int) or max_pages_per_chunk < 1):
        logging.error("max_pages_per_chunk must be a positive integer.")
        return None
    if max_chunk_size_mb is not None and (not isinstance(max_chunk_size_mb, (int, float)) or max_chunk_size_mb <= 0):
        logging.error("max_chunk_size_mb must be a positive number.")
        return None
    try:
        doc = fitz.open(input_pdf)
        # Log original file size
        original_size = os.path.getsize(input_pdf) / 1024
        logging.info(f"Opened PDF '{input_pdf}' with {doc.page_count} pages ({original_size:,} KB)")
        total_pages = doc.page_count
        
        # Only check page count limit when using page-based splitting
        if max_pages_per_chunk is not None and total_pages <= max_pages_per_chunk:
            logging.warning(f"PDF has only {total_pages} pages, less than or equal to max_pages_per_chunk ({max_pages_per_chunk}). No split performed.")
            return None
            
        base_name = os.path.basename(input_pdf)
        
        # Create chunks based on the specified method
        if max_pages_per_chunk is not None:
            # Page-based chunking (original method)
            chunks = [range(i, min(i+max_pages_per_chunk, total_pages)) for i in range(0, total_pages, max_pages_per_chunk)]
            logging.info(f"Using page-based chunking: {max_pages_per_chunk} pages per chunk")
        else:
            # Size-based chunking (new method)
            chunks = create_size_based_chunks(doc, max_chunk_size_mb)
            logging.info(f"Using size-based chunking: ~{max_chunk_size_mb}MB per chunk")
        
        # Calculate padding width based on total number of chunks
        padding_width = len(str(len(chunks)))
        for idx, page_range in enumerate(chunks, 1):
            # Zero-pad the index for proper sorting
            padded_idx = str(idx).zfill(padding_width)
            out_path = os.path.join(output_dir, f"{padded_idx}_{base_name}")
            
            # Check if file already exists and no-overwrite is enabled
            if no_overwrite and os.path.exists(out_path):
                file_size = os.path.getsize(out_path)
                logging.info(f"Skipping chunk {idx}: {out_path} already exists ({file_size/1024:,} KB)")
                continue
            
            new_doc = fitz.open()
            
            # Insert pages one at a time to better control image duplication
            # This preserves links and annotations while minimizing duplication
            for page_num in page_range:
                logging.debug(f"Inserting page {page_num + 1} into chunk {idx}")
                # Insert each page individually to minimize cross-page image duplication
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num, 
                                 links=True, annots=True)
            
            # Skip image analysis - it's too slow for large embedded images
            logging.debug(f"Completed inserting all pages for chunk {idx}")
            
            # Save with deduplication to prevent image bloat
            # garbage=4 removes duplicate objects without changing image quality
            # This is key to preventing the size explosion while preserving content
            new_doc.save(out_path, garbage=4, deflate=True, clean=True)
            
            new_doc.close()
            
            # Log file size for monitoring
            file_size = os.path.getsize(out_path)
            logging.info(f"Saved chunk {idx}: {out_path} ({len(page_range)} pages, {file_size/1024:,} KB)")
        doc.close()
        return True
    except Exception as e:
        logging.error(f"Error splitting PDF: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Split PDF files into chunks')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('output_dir', help='Directory to save the split PDF files')
    
    # Mutually exclusive group for chunking method
    chunking_group = parser.add_mutually_exclusive_group(required=True)
    chunking_group.add_argument('--pages', type=int, help='Maximum number of pages per chunk')
    chunking_group.add_argument('--max-size', type=float, help='Maximum size per chunk in MB')
    
    parser.add_argument('--no-overwrite', action='store_true', 
                       help='Skip processing if output files already exist (checkpoint/resume mode)')
    
    args = parser.parse_args()
    
    if args.no_overwrite:
        print("No-overwrite mode enabled - will skip existing chunks")
    
    if args.pages:
        print(f"Starting PDF split: {args.pages} pages per chunk")
        split_pdf(args.input_pdf, args.output_dir, max_pages_per_chunk=args.pages, 
                 no_overwrite=args.no_overwrite)
    elif args.max_size:
        print(f"Starting PDF split: {args.max_size}MB per chunk (size-based)")
        split_pdf(args.input_pdf, args.output_dir, max_chunk_size_mb=args.max_size, 
                 no_overwrite=args.no_overwrite)
