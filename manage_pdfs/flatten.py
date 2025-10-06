#!/usr/bin/env python3
"""
True PDF flattening by converting pages to pixelized images
Renders each page as a high-resolution image and creates a new PDF from the images
"""

import fitz  # PyMuPDF
import sys
import os
import logging
import io
from PIL import Image

logging.basicConfig(level=logging.INFO)

# Usage: python flatten.py input.pdf output.pdf [--dpi 300] [--quality high]

def flatten_pdf(input_path, output_path, dpi=300, quality='high', jpeg_quality=95, progress_callback=None, cancellation_checker=None):
    """
    True PDF flattening by converting each page to a high-resolution pixelized image.
    
    This creates a completely flattened PDF where everything becomes pixels:
    - All text becomes rasterized (no longer selectable or searchable)
    - All interactive elements (forms, buttons, links) become static pixels
    - All vector graphics become rasterized
    - All fonts become pixels (no font embedding issues)
    - All transparency, layers, and complex effects become flat pixels
    - Digital signatures become visual pixels (no longer cryptographically valid)
    - Annotations become permanent visual pixels
    
    Args:
        input_path: Path to input PDF
        output_path: Path to save pixelized PDF
        dpi: Resolution for rasterization (default: 300 DPI for high quality)
        quality: Quality preset - 'low' (150 DPI), 'medium' (200 DPI), 'high' (300 DPI), 'ultra' (600 DPI)
        jpeg_quality: JPEG compression quality 1-100 (default: 95 for minimal quality loss)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(input_path):
        logging.error(f"Error: Input file '{input_path}' does not exist.")
        return False
    
    # Quality presets
    quality_presets = {
        'low': 150,
        'medium': 200, 
        'high': 300,
        'ultra': 600
    }
    
    # Use quality preset if provided
    if quality in quality_presets:
        dpi = quality_presets[quality]
        logging.info(f"Using {quality} quality preset: {dpi} DPI")
    else:
        logging.info(f"Using custom DPI: {dpi}")
    

    
    try:
        logging.info(f"True pixelized flattening of '{input_path}' at {dpi} DPI...")
        
        # Open source PDF
        source_doc = fitz.open(input_path)
        page_count = source_doc.page_count
        
        logging.info(f"Processing {page_count} pages...")
        
        # Initial progress callback
        if progress_callback:
            if not progress_callback(0, page_count, 0, "Starting PDF flattening..."):
                logging.info("Flatten operation cancelled during initialization")
                source_doc.close()
                return False
        
        # Create new empty PDF document for the flattened pages
        flattened_doc = fitz.open()
        
        for page_num in range(page_count):
            # Check for cancellation before each page
            if cancellation_checker and cancellation_checker():
                logging.info(f"Flatten operation cancelled before processing page {page_num + 1}")
                try:
                    source_doc.close()
                    flattened_doc.close()
                except:
                    pass  # Ignore errors during cancellation cleanup
                return False
            
            logging.info(f"Pixelizing page {page_num + 1}/{page_count}...")
            
            # Progress callback for current page
            if progress_callback:
                if not progress_callback(page_num, page_count, int((page_num / page_count) * 100), f"Flattening page {page_num + 1} of {page_count}..."):
                    logging.info(f"Flatten operation cancelled while processing page {page_num + 1}")
                    try:
                        source_doc.close()
                        flattened_doc.close()
                    except:
                        pass  # Ignore errors during cancellation cleanup
                    return False
            
            # Get the page
            page = source_doc[page_num]
            
            # Get page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Calculate matrix for the desired DPI
            # Default PyMuPDF resolution is 72 DPI, so scale accordingly
            scale = dpi / 72.0
            matrix = fitz.Matrix(scale, scale)
            
            # Render page to pixmap (image) at high resolution
            # This converts EVERYTHING to pixels: text, vector graphics, forms, annotations, etc.
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Convert pixmap to image data
            if jpeg_quality < 100:
                # Use PIL for JPEG compression
                img_data = pixmap.tobytes("png")
                pil_image = Image.open(io.BytesIO(img_data))
                
                # Convert to RGB if needed and apply JPEG compression
                if pil_image.mode in ("RGBA", "LA", "P"):
                    # Convert transparency to white background for JPEG
                    background = Image.new("RGB", pil_image.size, (255, 255, 255))
                    if pil_image.mode == "P":
                        pil_image = pil_image.convert("RGBA")
                    background.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode in ("RGBA", "LA") else None)
                    pil_image = background
                
                # Save as JPEG with specified quality
                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format="JPEG", quality=jpeg_quality, optimize=True)
                img_data = img_buffer.getvalue()
                pil_image = None  # Clean up
            else:
                # Use PNG directly from PyMuPDF (always lossless)
                img_data = pixmap.tobytes("png")
            
            # Create a new page in the flattened document with the same dimensions
            new_page = flattened_doc.new_page(width=page_width, height=page_height)
            
            # Insert the pixelized image into the new page
            # This fills the entire page with the rasterized version
            img_rect = fitz.Rect(0, 0, page_width, page_height)
            new_page.insert_image(img_rect, stream=img_data)
            
            # Clean up
            pixmap = None
            
            # Progress callback after page completion
            current_page = page_num + 1
            if progress_callback:
                if not progress_callback(current_page, page_count, int((current_page / page_count) * 100), f"Flattening page {current_page} of {page_count}..."):
                    logging.info(f"Flatten operation cancelled after completing page {current_page}")
                    try:
                        source_doc.close()
                        flattened_doc.close()
                    except:
                        pass  # Ignore errors during cancellation cleanup
                    return False
        
        # Close source document
        source_doc.close()
        
        # Final progress callback before saving
        if progress_callback:
            if not progress_callback(page_count, page_count, 95, "Saving flattened PDF..."):
                logging.info("Flatten operation cancelled before saving")
                try:
                    flattened_doc.close()
                except:
                    pass
                return False
        
        # Save the completely pixelized PDF
        logging.info(f"Saving pixelized PDF with {page_count} rasterized pages...")
        flattened_doc.save(output_path, garbage=4, deflate=True, clean=True)
        flattened_doc.close()
        
        # Calculate file sizes
        input_size = os.path.getsize(input_path) / (1024 * 1024)
        output_size = os.path.getsize(output_path) / (1024 * 1024)
        
        logging.info(f"Pixelized flattening completed!")
        logging.info(f"Original size: {input_size:.2f} MB")
        logging.info(f"Pixelized size: {output_size:.2f} MB")
        logging.info(f"All content converted to {dpi} DPI pixels")
        logging.info(f"Text is no longer selectable or searchable")
        logging.info(f"All interactive elements are now static pixels")
        logging.info(f"Pixelized PDF saved to '{output_path}'")
        
        # Final completion callback
        if progress_callback:
            progress_callback(page_count, page_count, 100, "Flatten complete!")
        
        return True
        
    except Exception as e:
        logging.error(f"Error flattening PDF: {e}")
        return False
    
if __name__ == "__main__":
    if len(sys.argv) < 3:
        logging.error("Usage: python flatten.py input.pdf output.pdf [options]")
        logging.error("Options:")
        logging.error("  --dpi <number>: Resolution for pixelization (default: 300)")
        logging.error("  --quality <preset>: Quality preset - low/medium/high/ultra (overrides --dpi)")
        logging.error("  --jpeg-quality <1-100>: JPEG compression quality (default: 95)")
        logging.error("  --help: Show this help message")
        logging.error("")
        logging.error("Quality presets:")
        logging.error("  low: 150 DPI (smaller files, lower quality)")
        logging.error("  medium: 200 DPI (balanced)")
        logging.error("  high: 300 DPI (good quality, default)")
        logging.error("  ultra: 600 DPI (maximum quality, larger files)")
        logging.error("")
        logging.error("This tool converts PDFs to completely pixelized versions:")
        logging.error("  - All text becomes non-selectable pixels")
        logging.error("  - All interactive elements become static pixels")
        logging.error("  - All vector graphics become rasterized")
        logging.error("  - Perfect visual preservation with zero interactivity")
        sys.exit(1)
    
    # Show help if requested
    if "--help" in sys.argv:
        print("PDF True Pixelized Flattening Tool")
        print("=" * 40)
        print("Converts PDFs to completely rasterized versions where everything becomes pixels.")
        print("\nFeatures:")
        print("  ✓ Converts all text to non-selectable pixels")
        print("  ✓ Removes all interactivity (forms, buttons, links)")
        print("  ✓ Rasterizes all vector graphics")
        print("  ✓ Flattens all layers and transparency")
        print("  ✓ Preserves exact visual appearance")
        print("  ✓ Eliminates font embedding issues")
        print("  ✓ Maximum compatibility across viewers")
        print("\nUse cases:")
        print("  • Creating truly flat PDFs for archival")
        print("  • Removing all interactive content permanently")
        print("  • Converting complex PDFs to simple image-based ones")
        print("  • Ensuring consistent appearance across all devices")
        sys.exit(0)
    
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    
    # Parse optional arguments
    dpi = 300  # Default DPI
    quality = None
    jpeg_quality = 95
    
    for i, arg in enumerate(sys.argv):
        if arg == "--dpi" and i + 1 < len(sys.argv):
            try:
                dpi = int(sys.argv[i + 1])
                if dpi < 50 or dpi > 1200:
                    logging.warning(f"DPI {dpi} is outside recommended range (50-1200). Using anyway.")
            except ValueError:
                logging.error(f"Invalid DPI value: {sys.argv[i + 1]}")
                sys.exit(1)
        elif arg == "--quality" and i + 1 < len(sys.argv):
            quality = sys.argv[i + 1].lower()
            if quality not in ['low', 'medium', 'high', 'ultra']:
                logging.error(f"Invalid quality preset: {quality}. Use: low, medium, high, or ultra")
                sys.exit(1)
        elif arg == "--jpeg-quality" and i + 1 < len(sys.argv):
            try:
                jpeg_quality = int(sys.argv[i + 1])
                if jpeg_quality < 1 or jpeg_quality > 100:
                    logging.error("JPEG quality must be between 1 and 100")
                    sys.exit(1)
            except ValueError:
                logging.error(f"Invalid JPEG quality value: {sys.argv[i + 1]}")
                sys.exit(1)
    
    # Run the pixelized flattening
    success = flatten_pdf(input_pdf, output_pdf, dpi=dpi, quality=quality, jpeg_quality=jpeg_quality)
    
    if not success:
        sys.exit(1)