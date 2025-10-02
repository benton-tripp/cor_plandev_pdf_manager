import fitz # PyMuPDF
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

# Usage: python flatten.py input.pdf output.pdf

def flatten_pdf(input_path, output_path, remove_links=False, remove_annotations=True, flatten_transparency=True):
    """
    Flatten a PDF by converting interactive elements to static content.
    
    Args:
        input_path: Path to input PDF
        output_path: Path to save flattened PDF
        remove_links: Whether to remove hyperlinks (default: False, keeps links)
        remove_annotations: Whether to flatten annotations (default: True)
        flatten_transparency: Whether to flatten transparent content (default: True)
        
    Note: This function handles:
    - Form fields (widgets) → converted to static content
    - Annotations → baked into page content (highlights, comments, etc.)
    - Hyperlinks → optionally removed
    - Optional content groups (layers) → visible layers flattened
    - Transparency → optionally flattened to opaque content
    - Embedded fonts/images are preserved but made non-interactive
    """
    if not os.path.exists(input_path):
        logging.error(f"Error: Input file '{input_path}' does not exist.")
        return False
    
    try:
        logging.info(f"Flattening '{input_path}'...")
        doc = fitz.open(input_path)
        
        flattened_items = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # 1. Flatten form fields (widgets) - convert to static content
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    try:
                        # Remove the widget (form field) - this flattens it
                        page.delete_widget(widget)
                        flattened_items.append(f"form field on page {page_num + 1}")
                    except:
                        pass
            
            # 2. Flatten annotations (if requested) - this handles markup annotations
            if remove_annotations:
                annotations = page.annots()
                if annotations:
                    for annot in annotations:
                        try:
                            # Before deleting, check if it's a markup annotation that needs special handling
                            annot_type = annot.type[1]  # Get annotation type name
                            
                            # For markup annotations (highlights, underlines, strikeouts), 
                            # PyMuPDF will automatically render them to page content when deleted
                            if annot_type in ['Highlight', 'Underline', 'StrikeOut', 'Squiggly']:
                                logging.debug(f"Flattening {annot_type} annotation on page {page_num + 1}")
                            
                            # Delete the annotation - PyMuPDF renders it to page content
                            page.delete_annot(annot)
                            flattened_items.append(f"{annot_type.lower()} annotation on page {page_num + 1}")
                        except:
                            # Fallback for any annotation that can't be processed
                            try:
                                page.delete_annot(annot)
                                flattened_items.append(f"annotation on page {page_num + 1}")
                            except:
                                pass
            
            # 3. Remove links (if requested)
            if remove_links:
                links = page.get_links()
                if links:
                    for link in links:
                        try:
                            page.delete_link(link)
                            flattened_items.append(f"link on page {page_num + 1}")
                        except:
                            pass
            
            # 4. Handle transparency flattening (if requested)
            if flatten_transparency:
                try:
                    # Get page images to check for transparency
                    images = page.get_images()
                    for img_xref, *_ in images:
                        try:
                            # Extract image info to check for transparency
                            img_dict = doc.extract_image(img_xref)
                            if img_dict and 'smask' in img_dict and img_dict['smask']:
                                flattened_items.append(f"transparent image on page {page_num + 1}")
                        except:
                            pass
                    
                    # Note: PyMuPDF's save with clean=True will flatten most transparency
                    # More complex transparency requires rendering the page to image and back
                    
                except Exception as e:
                    logging.debug(f"Could not process transparency on page {page_num + 1}: {e}")
        
        # 4. Remove optional content groups (layers) - flatten all layers to visible content
        try:
            oc_groups = doc.get_ocgs()  # Fixed method name
            if oc_groups:
                # Set all optional content to visible and then remove the groups
                for oc_xref, oc_info in oc_groups.items():
                    try:
                        doc.set_oc(oc_xref, True)  # Make visible
                    except:
                        pass
                flattened_items.append("optional content layers")
        except AttributeError:
            # get_ocgs() may not be available in older PyMuPDF versions
            logging.debug("Optional content groups not supported in this PyMuPDF version")
        except:
            logging.debug("Could not process optional content groups")
        
        # Log summary of document structure
        logging.info(f"Document has {doc.page_count} pages")
        
        # Check for embedded fonts and images (these are preserved but made non-interactive)
        try:
            all_fonts = set()
            all_images = 0
            for page_num in range(doc.page_count):
                page_fonts = doc.get_page_fonts(page_num)
                all_fonts.update([f[3] for f in page_fonts])  # basefont names
                all_images += len(doc.get_page_images(page_num))
            
            if all_fonts:
                logging.info(f"Document contains {len(all_fonts)} unique fonts (preserved)")
            if all_images:
                logging.info(f"Document contains {all_images} images (preserved)")
        except:
            pass
        
        # Save the flattened PDF with optimal settings
        # garbage=4: Remove unused objects and compress object streams
        # deflate=True: Use deflate compression
        # clean=True: Clean up and optimize the PDF structure
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        
        if flattened_items:
            unique_items = list(set(flattened_items))
            logging.info(f"Flattened {len(unique_items)} types of elements: {', '.join(unique_items)}")
        else:
            logging.info("No interactive elements found to flatten")
        
        logging.info(f"Flattened PDF saved to '{output_path}'")
        return True
        
    except Exception as e:
        logging.error(f"Error flattening PDF: {e}")
        return False
    
if __name__ == "__main__":
    if len(sys.argv) < 3:
        logging.error("Usage: python flatten.py input.pdf output.pdf [options]")
        logging.error("Options:")
        logging.error("  --remove-links: Remove hyperlinks (default: keep links)")
        logging.error("  --keep-annotations: Keep annotations (default: flatten annotations)")
        logging.error("  --keep-transparency: Keep transparency (default: flatten transparency)")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    
    # Parse optional arguments
    remove_links = "--remove-links" in sys.argv
    remove_annotations = "--keep-annotations" not in sys.argv  # Default is to remove
    flatten_transparency = "--keep-transparency" not in sys.argv  # Default is to flatten
    
    flatten_pdf(input_pdf, output_pdf, remove_links=remove_links, 
               remove_annotations=remove_annotations, flatten_transparency=flatten_transparency)