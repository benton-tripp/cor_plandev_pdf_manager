#!/usr/bin/env python3
"""
Diagnostic script to analyze PDF content and identify what might be causing stamp/watermark loss
"""

import fitz  # PyMuPDF
import sys
import os

def diagnose_pdf(input_path):
    """Diagnose PDF content to understand stamp/watermark structure"""
    
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        return
    
    try:
        doc = fitz.open(input_path)
        print(f"Analyzing PDF: {input_path}")
        print(f"Pages: {doc.page_count}")
        print("=" * 50)
        
        # Check first few pages for detailed analysis
        for page_num in range(min(3, doc.page_count)):
            page = doc[page_num]
            print(f"\nPAGE {page_num + 1} ANALYSIS:")
            print("-" * 30)
            
            # 1. Check annotations
            annotations = [an for an in page.annots()]
            if annotations:
                print(f"Annotations found: {len(annotations)}")
                for i, annot in enumerate(annotations):
                    try:
                        annot_type = annot.type[1]
                        rect = annot.rect
                        print(f"  {i+1}. {annot_type} at {rect}")
                        
                        # Get annotation content if available
                        try:
                            content = annot.info.get('content', '')
                            if content:
                                print(f"      Content: {content[:50]}...")
                        except:
                            pass
                            
                    except Exception as e:
                        print(f"  {i+1}. Could not read annotation: {e}")
            else:
                print("No annotations found")
                
            # 2. Check for digital signatures
            try:
                # Check if this page has signature fields or signature content
                sig_fields = []
                try:
                    # Look for signature widgets/fields
                    widgets = page.widgets()
                    for widget in widgets:
                        if widget.field_type_string == 'Signature':
                            sig_fields.append(widget)
                            print(f"Found signature field: {widget.field_name} at {widget.rect}")
                except:
                    pass
                
                if not sig_fields:
                    print("No signature fields found")
                else:
                    print(f"Found {len(sig_fields)} signature fields")
                    
            except Exception as e:
                print(f"Could not check signatures: {e}")
            
            # 3. Check XObjects and content streams (fixed)
            try:
                # Get page content more carefully
                content_streams = []
                try:
                    # Try to get the page's content streams
                    content_streams = [co for co in page.get_contents()]
                except:
                    pass
                
                if content_streams:
                    print(f"Page has {len(content_streams)} content streams")
                    
                    for i, stream in enumerate(content_streams):
                        try:
                            # Get stream data properly
                            if hasattr(stream, 'get_data'):
                                content_bytes = stream.get_data()
                            else:
                                # Alternative method for different PyMuPDF versions
                                content_bytes = doc.xref_stream(stream)
                            
                            content_str = content_bytes.decode('utf-8', errors='ignore')
                            
                            # Look for signature/disclosure content
                            signature_keywords = ['digitally signed', 'signature', 'authorized', 'city of raleigh', 'disclosure', 'leidy.garcia']
                            found_keywords = [k for k in signature_keywords if k.lower() in content_str.lower()]
                            
                            if found_keywords:
                                print(f"  Stream {i+1} contains signature/disclosure content: {found_keywords}")
                                # Show relevant portion
                                lines = content_str.split('\n')
                                for line in lines[:10]:  # First 10 lines
                                    if any(k.lower() in line.lower() for k in signature_keywords):
                                        print(f"    Content: {line.strip()[:100]}...")
                                        
                        except Exception as e:
                            print(f"  Could not read content stream {i+1}: {e}")
                else:
                    print("No content streams found")
            except Exception as e:
                print(f"Could not analyze page content: {e}")
            
            # 4. Check for embedded document signatures
            try:
                # Check document-level signatures
                if hasattr(doc, 'signature_fields'):
                    sig_fields = [sf for sf in doc.signature_fields()]
                    if sig_fields:
                        print(f"Document has {len(sig_fields)} document-level signature fields")
                        for field in sig_fields:
                            print(f"  Signature field: {field}")
                else:
                    print("No document-level signature check available")
            except Exception as e:
                print(f"Could not check document signatures: {e}")
            
            # 5. Check for drawings/vector graphics
            try:
                drawings = [dr for dr in page.get_drawings()]
                if drawings:
                    print(f"Vector drawings found: {len(drawings)}")
                    for i, drawing in enumerate(drawings[:3]):  # Show first 3
                        print(f"  Drawing {i+1}: {drawing.get('type', 'unknown')} at {drawing.get('rect', 'unknown position')}")
                else:
                    print("No vector drawings found")
            except Exception as e:
                print(f"Could not analyze drawings: {e}")
            
            # 4. Check images
            images = [im for im in page.get_images()]
            if images:
                print(f"Images found: {len(images)}")
                for i, img_info in enumerate(images[:3]):  # Show first 3
                    try:
                        xref = img_info[0]
                        img_dict = doc.extract_image(xref)
                        print(f"  Image {i+1}: {img_dict.get('width', '?')}x{img_dict.get('height', '?')} {img_dict.get('ext', '?')}")
                    except:
                        print(f"  Image {i+1}: Could not extract details")
            else:
                print("No images found")
            
            # 7. Check text content for signature/disclosure content
            try:
                text = page.get_text()
                
                # Look for signature-related content
                signature_indicators = ['digitally signed', 'leidy.garcia', 'raleighnc.gov', 'city of raleigh', 'authorized', 'disclosure']
                found_sig_content = False
                
                lines = text.split('\n')
                for line in lines:
                    line_lower = line.lower().strip()
                    if any(indicator in line_lower for indicator in signature_indicators):
                        if not found_sig_content:
                            print("Found digital signature/disclosure content in page text:")
                            found_sig_content = True
                        print(f"  Signature text: '{line.strip()}'")
                
                # Also check for the stamp content
                if "04/17/2025" in text or "APPROVED" in text.upper():
                    print("Found stamp-like text content in page text")
                    for line in lines:
                        if "04/17/2025" in line or "APPROVED" in line.upper():
                            if len(line.strip()) > 0 and line.strip() not in [l.strip() for l in lines if any(indicator in l.lower() for indicator in signature_indicators)]:
                                print(f"  Stamp text: '{line.strip()}'")
                
                if not found_sig_content and not any("04/17/2025" in line or "APPROVED" in line.upper() for line in lines):
                    print("No signature or stamp text found in extracted text")
                    
            except Exception as e:
                print(f"Could not extract text: {e}")
            
            # 8. Check for optional content (layers)
            try:
                oc_groups = [og for og in doc.get_ocgs()]
                if oc_groups:
                    print(f"Optional content groups (layers): {len(oc_groups)}")
                    for oc_xref, oc_info in oc_groups.items():
                        print(f"  Layer: {oc_info}")
                else:
                    print("No optional content layers")
            except:
                print("Could not check optional content")
                
            # 9. Check for form fields and interactive elements
            try:
                widgets = [w for w in page.widgets()]
                if widgets:
                    print(f"Interactive elements found: {len(widgets)}")
                    for widget in widgets:
                        widget_type = widget.field_type_string if hasattr(widget, 'field_type_string') else 'Unknown'
                        widget_name = widget.field_name if hasattr(widget, 'field_name') else 'Unnamed'
                        print(f"  {widget_type} field: {widget_name} at {widget.rect}")
                else:
                    print("No interactive form fields found")
            except Exception as e:
                print(f"Could not check form fields: {e}")
        
        doc.close()
        
    except Exception as e:
        print(f"Error analyzing PDF: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_pdf.py input.pdf")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    diagnose_pdf(input_pdf)