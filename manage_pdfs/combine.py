import fitz
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

def combine_pdfs(pdf_list, output_path):
    if not isinstance(pdf_list, list) or len(pdf_list) == 0:
        logging.error("pdf_list must be a non-empty list of file paths.")
        return False
    for i, pdf in enumerate(pdf_list):
        if not os.path.exists(pdf):
            logging.error(f"Input file '{pdf}' does not exist.")
            return False
        else:
            logging.info(f"PDF file {i+1}/{len(pdf_list)}: '{pdf}'")
    try:
        combined = fitz.open()
        for pdf in pdf_list:
            doc = fitz.open(pdf)
            combined.insert_pdf(doc, links=True, annots=True)
            doc.close()
            logging.info(f"Added '{pdf}' ({combined.page_count} total pages)")
        # Save with garbage collection and object stream compression
        logging.info(f"Saving combined PDF to '{output_path}'...")
        combined.save(output_path, garbage=4, deflate=True, clean=True)
        combined.close()
        logging.info(f"Combined PDF saved successfully.")
        return True
    except Exception as e:
        logging.error(f"Error combining PDFs: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        logging.error("Usage: python combine.py file1.pdf file2.pdf ... output.pdf")
        sys.exit(1)
    pdf_files = sys.argv[1:-1]
    output_pdf = sys.argv[-1]
    combine_pdfs(pdf_files, output_pdf)
