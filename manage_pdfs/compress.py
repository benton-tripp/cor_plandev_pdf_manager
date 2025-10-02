import fitz # PyMuPDF
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

# Usage: python compress.py input.pdf output.pdf

def compress_pdf(input_path, output_path):
    if not os.path.exists(input_path):
        logging.error(f"Error: Input file '{input_path}' does not exist.")
        return False
    try:
        logging.info(f"Compressing '{input_path}'...")
        doc = fitz.open(input_path)
        # Save with garbage collection and object stream compression
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        logging.info(f"Compressed PDF saved to '{output_path}'")
        return True
    except Exception as e:
        logging.error(f"Error compressing PDF: {e}")
        return False

# Main entry point for command line usage
if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.error("Usage: python compress.py input.pdf output.pdf")
        sys.exit(1)
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    compress_pdf(input_pdf, output_pdf)
