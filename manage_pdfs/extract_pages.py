#!/usr/bin/env python3
"""
Simple PDF page extraction utility
Extracts specific pages by page numbers from a PDF file
"""

import fitz  # PyMuPDF
import argparse
import os
import sys

def extract_pages(input_pdf, output_pdf, page_numbers):
    """
    Extract specific pages from a PDF file
    
    Args:
        input_pdf (str): Path to input PDF file
        output_pdf (str): Path to output PDF file
        page_numbers (list): List of page numbers to extract (1-indexed)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Open the input PDF
        doc = fitz.open(input_pdf)
        total_pages = doc.page_count
        
        print(f"Input PDF has {total_pages} pages")
        
        # Validate page numbers
        valid_pages = []
        for page_num in page_numbers:
            if 1 <= page_num <= total_pages:
                valid_pages.append(page_num - 1)  # Convert to 0-indexed
            else:
                print(f"Warning: Page {page_num} is out of range (1-{total_pages}), skipping")
        
        if not valid_pages:
            print("Error: No valid pages to extract")
            return False
        
        # Create new document with selected pages
        new_doc = fitz.open()
        
        for page_idx in valid_pages:
            print(f"Extracting page {page_idx + 1}")
            new_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
        
        # Save the new document
        new_doc.save(output_pdf)
        new_doc.close()
        doc.close()
        
        print(f"Successfully extracted {len(valid_pages)} pages to: {output_pdf}")
        return True
        
    except Exception as e:
        print(f"Error extracting pages: {e}")
        return False

def parse_page_numbers(page_string):
    """
    Parse page numbers from a string format
    Supports: "1,3,5", "1-5", "1,3-7,10"
    
    Args:
        page_string (str): String containing page numbers/ranges
        
    Returns:
        list: List of individual page numbers
    """
    pages = []
    
    # Split by commas first
    parts = page_string.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            # Handle range like "3-7"
            try:
                start, end = part.split('-', 1)
                start = int(start.strip())
                end = int(end.strip())
                pages.extend(range(start, end + 1))
            except ValueError:
                print(f"Warning: Invalid range format '{part}', skipping")
        else:
            # Handle single page number
            try:
                pages.append(int(part))
            except ValueError:
                print(f"Warning: Invalid page number '{part}', skipping")
    
    return sorted(list(set(pages)))  # Remove duplicates and sort

def main():
    parser = argparse.ArgumentParser(description='Extract specific pages from a PDF file')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('output_pdf', help='Path to the output PDF file')
    parser.add_argument('pages', help='Page numbers to extract (e.g., "1,3,5" or "1-5" or "1,3-7,10")')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input file '{args.input_pdf}' does not exist")
        sys.exit(1)
    
    # Parse page numbers
    page_numbers = parse_page_numbers(args.pages)
    
    if not page_numbers:
        print("Error: No valid page numbers provided")
        sys.exit(1)
    
    print(f"Extracting pages: {page_numbers}")
    
    # Extract pages
    success = extract_pages(args.input_pdf, args.output_pdf, page_numbers)
    
    if success:
        print("Page extraction completed successfully!")
        sys.exit(0)
    else:
        print("Page extraction failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()