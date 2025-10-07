import fitz  # PyMuPDF
import os
import logging
import sys
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TEST_PDF = "C:/users/trippb/Downloads/BLDNR-017613-2025 APPROVED (combined).pdf"

def get_page_sizes(pdf_path, top_n=50):
    if not os.path.exists(pdf_path):
        logging.error(f"File not found: {pdf_path}")
        return []

    doc = fitz.open(pdf_path)
    page_sizes = []

    # Get the page sizes in MB 
    # (include all embedded content - the total should approximately sum to the original file size)
    for page_num in range(doc.page_count):
        try:
            page = doc[page_num]
            page_size_bytes = 0
            
            # Get content streams size
            try:
                content_streams = page.get_contents()
                for stream in content_streams:
                    if hasattr(stream, 'get_length'):
                        page_size_bytes += stream.get_length()
                    else:
                        # Alternative method - get xref and calculate size
                        stream_data = doc.xref_stream(stream)
                        if stream_data:
                            page_size_bytes += len(stream_data)
            except Exception as e:
                logging.warning(f"Could not get content streams for page {page_num + 1}: {e}")
            
            # Get images size
            try:
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]  # xref number
                        # Get image data
                        img_data = doc.extract_image(xref)
                        if img_data and 'image' in img_data:
                            page_size_bytes += len(img_data['image'])
                    except Exception as e:
                        logging.warning(f"Could not get image {img_index} size on page {page_num + 1}: {e}")
            except Exception as e:
                logging.warning(f"Could not get images for page {page_num + 1}: {e}")
            
            # Get fonts size (approximate)
            try:
                font_list = page.get_fonts(full=True)
                for font in font_list:
                    try:
                        font_xref = font[0]
                        if font_xref > 0:
                            # Get font data size
                            font_data = doc.xref_stream(font_xref)
                            if font_data:
                                page_size_bytes += len(font_data)
                    except Exception as e:
                        logging.warning(f"Could not get font size on page {page_num + 1}: {e}")
            except Exception as e:
                logging.warning(f"Could not get fonts for page {page_num + 1}: {e}")
            
            # Get annotations size
            try:
                annotations = page.annots()
                for annot in annotations:
                    try:
                        annot_xref = annot.xref
                        if annot_xref > 0:
                            annot_data = doc.xref_stream(annot_xref)
                            if annot_data:
                                page_size_bytes += len(annot_data)
                    except Exception as e:
                        logging.warning(f"Could not get annotation size on page {page_num + 1}: {e}")
            except Exception as e:
                logging.warning(f"Could not get annotations for page {page_num + 1}: {e}")
            
            # Convert bytes to MB
            page_size_mb = page_size_bytes / (1024 * 1024)
            page_sizes.append((page_num, page_size_mb))
            
            logging.debug(f"Page {page_num + 1}: {page_size_mb:.2f} MB ({page_size_bytes:,} bytes)")
            
        except Exception as e:
            logging.error(f"Error processing page {page_num + 1}: {e}")
            page_sizes.append((page_num, 0.0))

    doc.close()

    # Return list of tuples (page_number, size_in_MB)
    return sorted(page_sizes, key=lambda x: x[1], reverse=True)

if __name__ == "__main__":
    # Check for system argument for PDF file path
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    else:
        pdf_file = TEST_PDF
        top_n = 50
    
    logging.info(f"Analyzing page sizes for: {pdf_file}")
    page_sizes = get_page_sizes(pdf_file, top_n=top_n)
    # save sizes to json in tests/outputs
    output_dir = "tests/outputs"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{timestamp}_page_sizes.json")
    with open(output_file, "w") as f:
        json.dump(page_sizes, f, indent=2)

    if not page_sizes:
        logging.error("No page sizes could be calculated")
        sys.exit(1)
    
    total_calculated_size = sum(size for _, size in page_sizes)
    logging.info(f"Total calculated size: {total_calculated_size:.2f} MB")
    
    top_pages = page_sizes[:top_n]
    logging.info(f"Top {len(top_pages)} largest pages:")
    
    # Report top_n largest pages
    for i, (page_num, size) in enumerate(top_pages, 1):
        logging.info(f"#{i:2d} - Page {page_num + 1:3d}: {size:.2f} MB")