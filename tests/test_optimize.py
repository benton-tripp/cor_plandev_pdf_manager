import fitz  # PyMuPDF
import sys
import os
import logging
import csv
from collections import defaultdict
from datetime import datetime

# Add parent directory to path to import optimize module
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'manage_pdfs')))
# from optimize import optimize_pdf, analyze_pdf_bloat

# Set up logging to file
LOG_DIR = 'tests/logs'
CSV_DIR = 'tests/outputs'
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(LOG_DIR, f'optimize_test_{timestamp}.log')
csv_filename = os.path.join(CSV_DIR, f'optimize_results_{timestamp}.csv')

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Keep some output for status
    ]
)

# Create a separate logger for detailed file logging only
file_logger = logging.getLogger('file_only')
file_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_logger.addHandler(file_handler)
file_logger.propagate = False

TEST_INPUT_PDF = 'tests/test_pdfs/BLDNR-017613-2025_APPROVED_largest_50.pdf'
OUTPUT_DIR = 'tests/test_pdfs/'

# CSV Headers for results tracking
CSV_HEADERS = [
    # Basic test info
    'timestamp', 'test_type', 'input_file', 'input_size_kb', 'input_size_mb', 'input_pages', 
    'input_objects', 'optimization_method', 'optimization_params', 'output_file', 'output_size_kb', 
    'output_size_mb', 'output_pages', 'output_objects', 'size_change_kb', 'size_change_percent',
    'objects_change', 'success', 'error_message',
    
    # Input PDF content analysis
    'input_annotations', 'input_widgets', 'input_images', 'input_fonts', 'input_drawings',
    'input_signature_fields', 'input_content_streams', 'input_optional_content_layers',
    'input_text_length', 'input_has_signature_text', 'input_has_stamp_text', 'input_small_images',
    'input_encrypted', 'input_needs_pass',
    
    # Output PDF content analysis (if available)
    'output_annotations', 'output_widgets', 'output_images', 'output_fonts', 'output_drawings',
    'output_signature_fields', 'output_content_streams', 'output_optional_content_layers', 
    'output_text_length', 'output_has_signature_text', 'output_has_stamp_text', 'output_small_images',
    
    # Content preservation analysis
    'text_content_preserved', 'text_length_change', 'metadata_preserved', 'annotations_preserved', 
    'images_preserved', 'widgets_preserved', 'drawings_preserved', 'signature_fields_preserved',
    'content_streams_preserved', 'optional_content_preserved', 'signature_text_preserved',
    'stamp_text_preserved',
    
    # Analysis metrics
    'potential_max_savings_percent', 'already_compressed', 'content_analysis_errors', 'notes'
]

def get_csv_defaults():
    """Get default values for all CSV fields"""
    return {
        # Basic test info
        'timestamp': '',
        'test_type': '',
        'input_file': '',
        'input_size_kb': 0.0,
        'input_size_mb': 0.0,
        'input_pages': 0,
        'input_objects': 0,
        'optimization_method': '',
        'optimization_params': '',
        'output_file': '',
        'output_size_kb': 0.0,
        'output_size_mb': 0.0,
        'output_pages': 0,
        'output_objects': 0,
        'size_change_kb': 0.0,
        'size_change_percent': 0.0,
        'objects_change': 0,
        'success': False,
        'error_message': '',
        
        # Input PDF content analysis
        'input_annotations': 0,
        'input_widgets': 0,
        'input_images': 0,
        'input_fonts': 0,
        'input_drawings': 0,
        'input_signature_fields': 0,
        'input_content_streams': 0,
        'input_optional_content_layers': 0,
        'input_text_length': 0,
        'input_has_signature_text': False,
        'input_has_stamp_text': False,
        'input_small_images': 0,
        'input_encrypted': False,
        'input_needs_pass': False,
        
        # Output PDF content analysis
        'output_annotations': 0,
        'output_widgets': 0,
        'output_images': 0,
        'output_fonts': 0,
        'output_drawings': 0,
        'output_signature_fields': 0,
        'output_content_streams': 0,
        'output_optional_content_layers': 0,
        'output_text_length': 0,
        'output_has_signature_text': False,
        'output_has_stamp_text': False,
        'output_small_images': 0,
        
        # Content preservation analysis
        'text_content_preserved': True,  # Default to True (assume preserved unless proven otherwise)
        'text_length_change': 0,
        'metadata_preserved': True,
        'annotations_preserved': True,
        'images_preserved': True,
        'widgets_preserved': True,
        'drawings_preserved': True,
        'signature_fields_preserved': True,
        'content_streams_preserved': True,
        'optional_content_preserved': True,
        'signature_text_preserved': True,
        'stamp_text_preserved': True,
        
        # Analysis metrics
        'potential_max_savings_percent': 0.0,
        'already_compressed': False,
        'content_analysis_errors': 0,
        'notes': ''
    }

def write_csv_result(data):
    """Write a single test result to CSV"""
    file_exists = os.path.exists(csv_filename)
    
    with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        # Start with defaults and update with provided data
        row_data = get_csv_defaults()
        row_data.update(data)
        
        # Ensure all CSV headers are present
        final_row_data = {header: row_data.get(header, get_csv_defaults()[header]) for header in CSV_HEADERS}
        writer.writerow(final_row_data)

def calculate_potential_savings(pdf_path, output_dir):
    """Calculate potential maximum savings for a PDF"""
    try:
        if not os.path.exists(pdf_path):
            return 0.0
        
        original_size = os.path.getsize(pdf_path)
        
        # Create a test file with maximum compression
        doc = fitz.open(pdf_path)
        max_compress_path = os.path.join(output_dir, 'temp_max_compress.pdf')
        doc.save(max_compress_path, deflate=True, clean=True, garbage=4)
        doc.close()
        
        if os.path.exists(max_compress_path):
            max_compressed_size = os.path.getsize(max_compress_path)
            potential_savings = ((original_size - max_compressed_size) / original_size) * 100
            
            # Clean up temp file
            try:
                os.remove(max_compress_path)
            except:
                pass
            
            return max(0.0, potential_savings)  # Don't return negative savings
        else:
            return 0.0
            
    except Exception as e:
        return 0.0

def get_content_analysis_csv_data(pdf_path, prefix='input'):
    """Get comprehensive content analysis data for CSV logging"""
    default_data = {
        f'{prefix}_annotations': 0,
        f'{prefix}_widgets': 0,
        f'{prefix}_images': 0,
        f'{prefix}_fonts': 0,
        f'{prefix}_drawings': 0,
        f'{prefix}_signature_fields': 0,
        f'{prefix}_content_streams': 0,
        f'{prefix}_optional_content_layers': 0,
        f'{prefix}_text_length': 0,
        f'{prefix}_has_signature_text': False,
        f'{prefix}_has_stamp_text': False,
        f'{prefix}_small_images': 0,
        f'{prefix}_encrypted': False,
        f'{prefix}_needs_pass': False
    }
    
    if not os.path.exists(pdf_path):
        return default_data
    
    try:
        # First try to get data from analyze_pdf_bloat if available
        try:
            analysis = analyze_pdf_bloat(pdf_path)
            if analysis:
                default_data.update({
                    f'{prefix}_annotations': analysis.get('annotations', 0),
                    f'{prefix}_widgets': analysis.get('widgets', 0),
                    f'{prefix}_images': analysis.get('images', 0),
                    f'{prefix}_fonts': analysis.get('fonts', {}).get('unique_fonts', 0)
                })
        except:
            pass
        
        # Comprehensive manual analysis
        doc = fitz.open(pdf_path)
        
        # Document-level properties
        default_data[f'{prefix}_encrypted'] = doc.is_encrypted
        default_data[f'{prefix}_needs_pass'] = doc.needs_pass
        
        # Analyze first few pages for detailed content
        total_annotations = 0
        total_widgets = 0
        total_images = 0
        total_drawings = 0
        total_signature_fields = 0
        total_content_streams = 0
        total_text_length = 0
        has_signature_text = False
        has_stamp_text = False
        small_images = 0
        
        # Signature/stamp text indicators
        signature_indicators = [
            'digitally signed', 'leidy.garcia', 'raleighnc.gov', 'city of raleigh', 
            'authorized', 'disclosure', 'signature'
        ]
        stamp_indicators = ['04/17/2025', 'APPROVED', 'BLDNR-017613-2025', 'stamp']
        
        # Check optional content layers (document level)
        try:
            oc_groups = dict(doc.get_ocgs()) if hasattr(doc, 'get_ocgs') else {}
            default_data[f'{prefix}_optional_content_layers'] = len(oc_groups)
        except:
            default_data[f'{prefix}_optional_content_layers'] = 0
        
        # Analyze pages (check first 3 pages or all if fewer)
        pages_to_check = min(3, doc.page_count)
        for page_num in range(pages_to_check):
            page = doc[page_num]
            
            # Count annotations
            annotations = [an for an in page.annots()]
            total_annotations += len(annotations)
            
            # Count and analyze widgets/form fields
            widgets = [w for w in page.widgets()]
            total_widgets += len(widgets)
            
            # Count signature fields specifically
            for widget in widgets:
                try:
                    if hasattr(widget, 'field_type_string') and widget.field_type_string == 'Signature':
                        total_signature_fields += 1
                except:
                    pass
            
            # Count and analyze images
            images = page.get_images()
            total_images += len(images)
            
            # Count small images (potential stamps/logos)
            for img_info in images:
                try:
                    xref = img_info[0]
                    img_dict = doc.extract_image(xref)
                    width = img_dict.get('width', 0)
                    height = img_dict.get('height', 0)
                    if isinstance(width, int) and isinstance(height, int):
                        if width < 200 and height < 200:
                            small_images += 1
                except:
                    pass
            
            # Count drawings/vector graphics
            try:
                drawings = page.get_drawings()
                total_drawings += len(drawings)
            except:
                pass
            
            # Count content streams
            try:
                content_streams = [co for co in page.get_contents()]
                total_content_streams += len(content_streams)
            except:
                pass
            
            # Analyze text content
            try:
                text = page.get_text()
                total_text_length += len(text)
                
                # Check for signature/stamp text
                text_lower = text.lower()
                if not has_signature_text:
                    has_signature_text = any(indicator in text_lower for indicator in signature_indicators)
                if not has_stamp_text:
                    has_stamp_text = any(indicator in text or indicator.lower() in text_lower for indicator in stamp_indicators)
            except:
                pass
        
        # Update data with totals
        if total_annotations > default_data[f'{prefix}_annotations']:
            default_data[f'{prefix}_annotations'] = total_annotations
        if total_widgets > default_data[f'{prefix}_widgets']:
            default_data[f'{prefix}_widgets'] = total_widgets
        if total_images > default_data[f'{prefix}_images']:
            default_data[f'{prefix}_images'] = total_images
        
        default_data.update({
            f'{prefix}_drawings': total_drawings,
            f'{prefix}_signature_fields': total_signature_fields,
            f'{prefix}_content_streams': total_content_streams,
            f'{prefix}_text_length': total_text_length,
            f'{prefix}_has_signature_text': has_signature_text,
            f'{prefix}_has_stamp_text': has_stamp_text,
            f'{prefix}_small_images': small_images
        })
        
        doc.close()
        
    except Exception as e:
        # Log error but continue with defaults
        default_data[f'{prefix}_annotations'] = f'ERROR: {str(e)}'
    
    return default_data

def log_and_print(message, level='info', print_also=False):
    """Log to file and optionally print to console"""
    if level == 'info':
        file_logger.info(message)
    elif level == 'warning':
        file_logger.warning(message)
    elif level == 'error':
        file_logger.error(message)
    elif level == 'debug':
        file_logger.debug(message)
    
    if print_also:
        print(message)

def get_file_info(pdf_path):
    """Get detailed information about a PDF file"""
    if not os.path.exists(pdf_path):
        return None
    
    file_size = os.path.getsize(pdf_path)
    doc = fitz.open(pdf_path)
    
    info = {
        'file_size_bytes': file_size,
        'file_size_mb': file_size / (1024 * 1024),
        'file_size_kb': file_size / 1024,
        'pages': doc.page_count,
        'xref_length': doc.xref_length(),
        'metadata': doc.metadata,
        'is_pdf': doc.is_pdf,
        'needs_pass': doc.needs_pass,
        'is_encrypted': doc.is_encrypted,
        'page_count': doc.page_count
    }
    
    doc.close()
    return info

def test_individual_optimizations(input_pdf):
    """Test each optimization method individually to see their effects"""
    
    print(f"\n{'='*80}")
    print(f"TESTING INDIVIDUAL OPTIMIZATION METHODS")
    print(f"{'='*80}")
    
    log_and_print(f"Testing individual optimization methods on: {input_pdf}")
    
    if not os.path.exists(input_pdf):
        log_and_print(f"ERROR: Input file '{input_pdf}' does not exist!", 'error', True)
        return
    
    # Get baseline info
    baseline_info = get_file_info(input_pdf)
    baseline_msg = f"BASELINE FILE INFO: Size: {baseline_info['file_size_kb']:.2f} KB ({baseline_info['file_size_mb']:.3f} MB), Pages: {baseline_info['pages']}, Objects: {baseline_info['xref_length']}, Encrypted: {baseline_info['is_encrypted']}"
    log_and_print(baseline_msg, print_also=True)
    
    # Analyze content
    analysis = analyze_pdf_bloat(input_pdf)
    if analysis:
        analysis_msg = f"Content analysis: {analysis['fonts']['unique_fonts']} unique fonts, {analysis['images']} images, {analysis['annotations']} annotations, {analysis['widgets']} widgets"
        log_and_print(analysis_msg, print_also=True)
        if analysis['fonts']['duplicated_fonts']:
            log_and_print(f"Duplicated fonts: {len(analysis['fonts']['duplicated_fonts'])}", print_also=True)
    
    # Get content data for CSV logging
    input_content_analysis = get_content_analysis_csv_data(input_pdf, 'input')
    
    doc = fitz.open(input_pdf)
    
    # Test different garbage collection levels
    garbage_levels = [
        (0, "No garbage collection"),
        (1, "Basic garbage collection"),
        (2, "Remove unused objects"),
        (3, "Moderate cleanup"),
        (4, "Aggressive cleanup")
    ]
    
    print("\nTesting garbage collection levels...")
    log_and_print("TESTING GARBAGE COLLECTION LEVELS")
    
    for level, description in garbage_levels:
        test_file = os.path.join(OUTPUT_DIR, f'test_garbage_{level}.pdf')
        csv_data = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'garbage_collection',
            'input_file': os.path.basename(input_pdf),
            'input_size_kb': baseline_info['file_size_kb'],
            'input_size_mb': baseline_info['file_size_mb'],
            'input_pages': baseline_info['pages'],
            'input_objects': baseline_info['xref_length'],
            'optimization_method': f'garbage_level_{level}',
            'optimization_params': f'garbage={level}',
            'output_file': os.path.basename(test_file),
            **input_content_analysis
        }
        
        try:
            doc_copy = fitz.open(input_pdf)  # Fresh copy
            doc_copy.save(test_file, garbage=level)
            doc_copy.close()
            
            info = get_file_info(test_file)
            size_change = info['file_size_kb'] - baseline_info['file_size_kb']
            percent_change = (size_change / baseline_info['file_size_kb']) * 100
            objects_change = info['xref_length'] - baseline_info['xref_length']
            
            # Get basic output analysis and preservation data
            output_content_data = get_content_analysis_csv_data(test_file, 'output')
            preservation_data = get_basic_preservation_data(input_pdf, test_file)
            
            # Check if already compressed (size increased with compression)
            already_compressed = size_change > 0 and level > 0
            
            # Calculate potential savings
            potential_savings = calculate_potential_savings(input_pdf, OUTPUT_DIR)
            
            # Update CSV data with results
            csv_data.update({
                'output_size_kb': info['file_size_kb'],
                'output_size_mb': info['file_size_mb'],
                'output_pages': info['pages'],
                'output_objects': info['xref_length'],
                'size_change_kb': size_change,
                'size_change_percent': percent_change,
                'objects_change': objects_change,
                'success': True,
                'already_compressed': already_compressed,
                'potential_max_savings_percent': potential_savings,
                'notes': description,
                **output_content_data,
                **preservation_data
            })
            
            result_msg = f"Level {level} ({description}): {info['file_size_kb']:.2f} KB (Δ {size_change:+.2f} KB, {percent_change:+.1f}%), Objects: {info['xref_length']} (Δ {objects_change:+d})"
            log_and_print(result_msg, print_also=True)
            
        except Exception as e:
            error_msg = f"Level {level} FAILED: {e}"
            log_and_print(error_msg, 'error', True)
            potential_savings = calculate_potential_savings(input_pdf, OUTPUT_DIR)
            csv_data.update({
                'success': False,
                'error_message': str(e),
                'potential_max_savings_percent': potential_savings,
                'already_compressed': False,
                'notes': description
            })
        
        write_csv_result(csv_data)
    
    # Test compression options
    print("\nTesting compression options...")
    log_and_print("TESTING COMPRESSION OPTIONS")
    
    compression_tests = [
        ({'deflate': False, 'clean': False}, "No compression/cleaning"),
        ({'deflate': True, 'clean': False}, "Deflate only"),
        ({'deflate': False, 'clean': True}, "Clean only"),
        ({'deflate': True, 'clean': True}, "Deflate + Clean"),
        ({'deflate': True, 'clean': True, 'garbage': 3}, "Deflate + Clean + Garbage(3)"),
        ({'deflate': True, 'clean': True, 'garbage': 4}, "Deflate + Clean + Garbage(4)"),
    ]
    
    for options, description in compression_tests:
        test_file = os.path.join(OUTPUT_DIR, f'test_compress_{hash(str(options))}.pdf')
        csv_data = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'compression',
            'input_file': os.path.basename(input_pdf),
            'input_size_kb': baseline_info['file_size_kb'],
            'input_size_mb': baseline_info['file_size_mb'],
            'input_pages': baseline_info['pages'],
            'input_objects': baseline_info['xref_length'],
            'optimization_method': 'compression_combination',
            'optimization_params': str(options),
            'output_file': os.path.basename(test_file),
            **input_content_analysis
        }
        
        try:
            doc_copy = fitz.open(input_pdf)
            doc_copy.save(test_file, **options)
            doc_copy.close()
            
            info = get_file_info(test_file)
            size_change = info['file_size_kb'] - baseline_info['file_size_kb']
            percent_change = (size_change / baseline_info['file_size_kb']) * 100
            objects_change = info['xref_length'] - baseline_info['xref_length']
            
            # Get basic output analysis and preservation data
            comp_output_content_data = get_content_analysis_csv_data(test_file, 'output')
            comp_preservation_data = get_basic_preservation_data(input_pdf, test_file)
            
            # Check if already compressed (deflate=True but size increased)
            already_compressed = size_change > 0 and options.get('deflate', False)
            
            # Calculate potential savings
            potential_savings = calculate_potential_savings(input_pdf, OUTPUT_DIR)
            
            # Update CSV data with results
            csv_data.update({
                'output_size_kb': info['file_size_kb'],
                'output_size_mb': info['file_size_mb'],
                'output_pages': info['pages'],
                'output_objects': info['xref_length'],
                'size_change_kb': size_change,
                'size_change_percent': percent_change,
                'objects_change': objects_change,
                'success': True,
                'already_compressed': already_compressed,
                'potential_max_savings_percent': potential_savings,
                'notes': description,
                **comp_output_content_data,
                **comp_preservation_data
            })
            
            result_msg = f"{description}: {info['file_size_kb']:.2f} KB (Δ {size_change:+.2f} KB, {percent_change:+.1f}%), Objects: {info['xref_length']} (Δ {objects_change:+d})"
            log_and_print(result_msg, print_also=True)
            
        except Exception as e:
            error_msg = f"{description} FAILED: {e}"
            log_and_print(error_msg, 'error', True)
            potential_savings = calculate_potential_savings(input_pdf, OUTPUT_DIR)
            csv_data.update({
                'success': False,
                'error_message': str(e),
                'potential_max_savings_percent': potential_savings,
                'already_compressed': False,
                'notes': description
            })
        
        write_csv_result(csv_data)
    
    # Test different save formats
    print("\nTesting save format options...")
    log_and_print("TESTING SAVE FORMAT OPTIONS")
    
    format_tests = [
        ({'ascii': True}, "ASCII encoding"),
        ({'ascii': False}, "Binary encoding"),
        ({'expand': True}, "Expanded operators"), 
        ({'expand': False}, "Compressed operators"),
        ({'pretty': True}, "Pretty formatting"),
        ({'pretty': False}, "Compact formatting"),
    ]
    
    for options, description in format_tests:
        test_file = os.path.join(OUTPUT_DIR, f'test_format_{hash(str(options))}.pdf')
        base_options = {'deflate': True, 'clean': True, 'garbage': 3}
        base_options.update(options)
        
        csv_data = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'format_options',
            'input_file': os.path.basename(input_pdf),
            'input_size_kb': baseline_info['file_size_kb'],
            'input_size_mb': baseline_info['file_size_mb'],
            'input_pages': baseline_info['pages'],
            'input_objects': baseline_info['xref_length'],
            'optimization_method': 'format_option',
            'optimization_params': str(base_options),
            'output_file': os.path.basename(test_file),
            **input_content_analysis
        }
        
        try:
            doc_copy = fitz.open(input_pdf)
            doc_copy.save(test_file, **base_options)
            doc_copy.close()
            
            info = get_file_info(test_file)
            size_change = info['file_size_kb'] - baseline_info['file_size_kb']
            percent_change = (size_change / baseline_info['file_size_kb']) * 100
            objects_change = info['xref_length'] - baseline_info['xref_length']
            
            # Get basic output analysis and preservation data
            format_output_content_data = get_content_analysis_csv_data(test_file, 'output')
            format_preservation_data = get_basic_preservation_data(input_pdf, test_file)
            
            # Check if already compressed
            already_compressed = size_change > 0 and base_options.get('deflate', False)
            
            # Calculate potential savings
            potential_savings = calculate_potential_savings(input_pdf, OUTPUT_DIR)
            
            # Update CSV data with results
            csv_data.update({
                'output_size_kb': info['file_size_kb'],
                'output_size_mb': info['file_size_mb'],
                'output_pages': info['pages'],
                'output_objects': info['xref_length'],
                'size_change_kb': size_change,
                'size_change_percent': percent_change,
                'objects_change': objects_change,
                'success': True,
                'already_compressed': already_compressed,
                'potential_max_savings_percent': potential_savings,
                'notes': description,
                **format_output_content_data,
                **format_preservation_data
            })
            
            result_msg = f"{description}: {info['file_size_kb']:.2f} KB (Δ {size_change:+.2f} KB, {percent_change:+.1f}%)"
            log_and_print(result_msg)
            
        except Exception as e:
            error_msg = f"{description} FAILED: {e}"
            log_and_print(error_msg, 'error', True)
            potential_savings = calculate_potential_savings(input_pdf, OUTPUT_DIR)
            csv_data.update({
                'success': False,
                'error_message': str(e),
                'potential_max_savings_percent': potential_savings,
                'already_compressed': False,
                'notes': description
            })
        
        write_csv_result(csv_data)
    
    doc.close()

def get_basic_preservation_data(original_path, optimized_path):
    """Get basic content preservation data for tests that don't run full analysis"""
    preservation_data = {
        'text_content_preserved': True,
        'text_length_change': 0,
        'metadata_preserved': True,
        'annotations_preserved': True,
        'images_preserved': True,
        'widgets_preserved': True,
        'drawings_preserved': True,
        'signature_fields_preserved': True,
        'content_streams_preserved': True,
        'optional_content_preserved': True,
        'signature_text_preserved': True,
        'stamp_text_preserved': True,
        'content_analysis_errors': 0
    }
    
    try:
        if not (os.path.exists(original_path) and os.path.exists(optimized_path)):
            preservation_data['content_analysis_errors'] = 1
            return preservation_data
        
        orig_doc = fitz.open(original_path)
        opt_doc = fitz.open(optimized_path)
        
        # Basic checks
        if orig_doc.page_count != opt_doc.page_count:
            preservation_data['content_analysis_errors'] += 1
        
        # Check first page content
        if orig_doc.page_count > 0 and opt_doc.page_count > 0:
            orig_page = orig_doc[0]
            opt_page = opt_doc[0]
            
            # Text preservation
            orig_text = orig_page.get_text()
            opt_text = opt_page.get_text()
            preservation_data['text_content_preserved'] = orig_text == opt_text
            preservation_data['text_length_change'] = len(opt_text) - len(orig_text)
            
            # Count-based preservation checks
            orig_annots = len([an for an in orig_page.annots()])
            opt_annots = len([an for an in opt_page.annots()])
            preservation_data['annotations_preserved'] = orig_annots == opt_annots
            
            orig_images = len(orig_page.get_images())
            opt_images = len(opt_page.get_images())
            preservation_data['images_preserved'] = orig_images == opt_images
            
            orig_widgets = len([w for w in orig_page.widgets()])
            opt_widgets = len([w for w in opt_page.widgets()])
            preservation_data['widgets_preserved'] = orig_widgets == opt_widgets
            
            try:
                orig_drawings = len(orig_page.get_drawings())
                opt_drawings = len(opt_page.get_drawings())
                preservation_data['drawings_preserved'] = orig_drawings == opt_drawings
            except:
                preservation_data['content_analysis_errors'] += 1
        
        orig_doc.close()
        opt_doc.close()
        
    except Exception as e:
        preservation_data['content_analysis_errors'] += 1
        # Set all preservation to False if we can't analyze
        for key in preservation_data:
            if key.endswith('_preserved'):
                preservation_data[key] = False
    
    return preservation_data

def compare_pdf_content_detailed(original_path, optimized_path):
    """Detailed comparison of PDF content before and after optimization"""
    
    print("\nStarting detailed content comparison...")
    log_and_print("DETAILED CONTENT COMPARISON")
    
    # Default preservation data
    preservation_data = {
        'text_content_preserved': True,
        'text_length_change': 0,
        'metadata_preserved': True,
        'annotations_preserved': True,
        'images_preserved': True,
        'widgets_preserved': True,
        'drawings_preserved': True,
        'signature_fields_preserved': True,
        'content_streams_preserved': True,
        'optional_content_preserved': True,
        'signature_text_preserved': True,
        'stamp_text_preserved': True,
        'content_analysis_errors': 0
    }
    
    try:
        orig_doc = fitz.open(original_path)
        opt_doc = fitz.open(optimized_path)
        
        doc_comparison = f"Document-level comparison: Pages: {orig_doc.page_count} → {opt_doc.page_count}, Objects: {orig_doc.xref_length()} → {opt_doc.xref_length()}"
        log_and_print(doc_comparison, print_also=True)
        
        # Check metadata preservation
        orig_meta = orig_doc.metadata
        opt_meta = opt_doc.metadata
        
        meta_differences = []
        for key in orig_meta:
            if orig_meta[key] != opt_meta.get(key, ''):
                meta_differences.append(f"{key}: '{orig_meta[key]}' → '{opt_meta.get(key, 'REMOVED')}'")
        
        preservation_data['metadata_preserved'] = len(meta_differences) == 0
        
        if meta_differences:
            log_and_print(f"⚠ Metadata changes detected ({len(meta_differences)} changes)", print_also=True)
            for diff in meta_differences[:3]:  # Show first 3
                log_and_print(f"  {diff}")
        else:
            log_and_print("✓ Metadata preserved", print_also=True)
        
        # Check optional content preservation (document level)
        try:
            orig_oc = dict(orig_doc.get_ocgs()) if hasattr(orig_doc, 'get_ocgs') else {}
            opt_oc = dict(opt_doc.get_ocgs()) if hasattr(opt_doc, 'get_ocgs') else {}
            preservation_data['optional_content_preserved'] = len(orig_oc) == len(opt_oc)
        except:
            preservation_data['content_analysis_errors'] += 1
        
        # Aggregate counters
        total_orig_text_length = 0
        total_opt_text_length = 0
        total_orig_annots = 0
        total_opt_annots = 0
        total_orig_images = 0
        total_opt_images = 0
        total_orig_widgets = 0
        total_opt_widgets = 0
        total_orig_drawings = 0
        total_opt_drawings = 0
        total_orig_sig_fields = 0
        total_opt_sig_fields = 0
        total_orig_content_streams = 0
        total_opt_content_streams = 0
        
        # Text content indicators
        signature_indicators = [
            'digitally signed', 'leidy.garcia', 'raleighnc.gov', 'city of raleigh', 
            'authorized', 'disclosure', 'signature'
        ]
        stamp_indicators = ['04/17/2025', 'APPROVED', 'BLDNR-017613-2025', 'stamp']
        
        orig_has_sig_text = False
        opt_has_sig_text = False
        orig_has_stamp_text = False
        opt_has_stamp_text = False
        
        # Page-by-page comparison
        pages_to_check = min(3, orig_doc.page_count, opt_doc.page_count)
        for page_num in range(pages_to_check):
            orig_page = orig_doc[page_num]
            opt_page = opt_doc[page_num]
            
            log_and_print(f"Page {page_num + 1} comparison:")
            
            # Text comparison
            try:
                orig_text = orig_page.get_text()
                opt_text = opt_page.get_text()
                
                total_orig_text_length += len(orig_text)
                total_opt_text_length += len(opt_text)
                
                if orig_text == opt_text:
                    log_and_print(f"  ✓ Text content identical ({len(orig_text)} chars)")
                else:
                    log_and_print(f"  ⚠ Text differs: {len(orig_text)} → {len(opt_text)} chars", print_also=True)
                    preservation_data['text_content_preserved'] = False
                    if len(orig_text) > len(opt_text):
                        log_and_print("    Content appears to be REMOVED", print_also=True)
                    elif len(opt_text) > len(orig_text):
                        log_and_print("    Content appears to be ADDED", print_also=True)
                
                # Check for signature/stamp text preservation
                orig_text_lower = orig_text.lower()
                opt_text_lower = opt_text.lower()
                
                if any(indicator in orig_text_lower for indicator in signature_indicators):
                    orig_has_sig_text = True
                    if not any(indicator in opt_text_lower for indicator in signature_indicators):
                        preservation_data['signature_text_preserved'] = False
                
                if any(indicator in orig_text or indicator.lower() in orig_text_lower for indicator in stamp_indicators):
                    orig_has_stamp_text = True
                    if not any(indicator in opt_text or indicator.lower() in opt_text_lower for indicator in stamp_indicators):
                        preservation_data['stamp_text_preserved'] = False
            except:
                preservation_data['content_analysis_errors'] += 1
                preservation_data['text_content_preserved'] = False
            
            # Annotations comparison
            try:
                orig_annots = [an for an in orig_page.annots()]
                opt_annots = [an for an in opt_page.annots()]
                
                total_orig_annots += len(orig_annots)
                total_opt_annots += len(opt_annots)
                
                if len(orig_annots) == len(opt_annots):
                    log_and_print(f"  ✓ Annotations preserved ({len(orig_annots)})")
                else:
                    log_and_print(f"  ⚠ Annotations changed: {len(orig_annots)} → {len(opt_annots)}", print_also=True)
                    preservation_data['annotations_preserved'] = False
            except:
                preservation_data['content_analysis_errors'] += 1
                preservation_data['annotations_preserved'] = False
            
            # Images comparison
            try:
                orig_images = orig_page.get_images()
                opt_images = opt_page.get_images()
                
                total_orig_images += len(orig_images)
                total_opt_images += len(opt_images)
                
                if len(orig_images) == len(opt_images):
                    log_and_print(f"  ✓ Images preserved ({len(orig_images)})")
                else:
                    log_and_print(f"  ⚠ Images changed: {len(orig_images)} → {len(opt_images)}", print_also=True)
                    preservation_data['images_preserved'] = False
            except:
                preservation_data['content_analysis_errors'] += 1
                preservation_data['images_preserved'] = False
            
            # Widgets comparison
            try:
                orig_widgets = [w for w in orig_page.widgets()]
                opt_widgets = [w for w in opt_page.widgets()]
                
                total_orig_widgets += len(orig_widgets)
                total_opt_widgets += len(opt_widgets)
                
                # Count signature fields specifically
                orig_sig_fields = sum(1 for w in orig_widgets 
                                    if hasattr(w, 'field_type_string') and w.field_type_string == 'Signature')
                opt_sig_fields = sum(1 for w in opt_widgets 
                                   if hasattr(w, 'field_type_string') and w.field_type_string == 'Signature')
                
                total_orig_sig_fields += orig_sig_fields
                total_opt_sig_fields += opt_sig_fields
                
                if len(orig_widgets) == len(opt_widgets):
                    log_and_print(f"  ✓ Form fields preserved ({len(orig_widgets)})")
                else:
                    log_and_print(f"  ⚠ Form fields changed: {len(orig_widgets)} → {len(opt_widgets)}", print_also=True)
                    preservation_data['widgets_preserved'] = False
                
                if orig_sig_fields != opt_sig_fields:
                    preservation_data['signature_fields_preserved'] = False
                    log_and_print(f"  ⚠ Signature fields changed: {orig_sig_fields} → {opt_sig_fields}", print_also=True)
            except:
                preservation_data['content_analysis_errors'] += 1
                preservation_data['widgets_preserved'] = False
                preservation_data['signature_fields_preserved'] = False
            
            # Drawings comparison
            try:
                orig_drawings = orig_page.get_drawings()
                opt_drawings = opt_page.get_drawings()
                
                total_orig_drawings += len(orig_drawings)
                total_opt_drawings += len(opt_drawings)
                
                if len(orig_drawings) == len(opt_drawings):
                    log_and_print(f"  ✓ Vector graphics preserved ({len(orig_drawings)})")
                else:
                    log_and_print(f"  ⚠ Vector graphics changed: {len(orig_drawings)} → {len(opt_drawings)}", print_also=True)
                    preservation_data['drawings_preserved'] = False
            except:
                preservation_data['content_analysis_errors'] += 1
                preservation_data['drawings_preserved'] = False
            
            # Content streams comparison
            try:
                orig_streams = [co for co in orig_page.get_contents()]
                opt_streams = [co for co in opt_page.get_contents()]
                
                total_orig_content_streams += len(orig_streams)
                total_opt_content_streams += len(opt_streams)
                
                if len(orig_streams) != len(opt_streams):
                    preservation_data['content_streams_preserved'] = False
                    log_and_print(f"  ⚠ Content streams changed: {len(orig_streams)} → {len(opt_streams)}", print_also=True)
            except:
                preservation_data['content_analysis_errors'] += 1
                preservation_data['content_streams_preserved'] = False
        
        # Update preservation data with final counts
        preservation_data['text_length_change'] = total_opt_text_length - total_orig_text_length
        
        # If original had signature/stamp text but we couldn't find it in optimized, mark as not preserved
        if orig_has_sig_text and not any(indicator in opt_text_lower for indicator in signature_indicators):
            preservation_data['signature_text_preserved'] = False
        if orig_has_stamp_text and not any(indicator in opt_text or indicator.lower() in opt_text_lower for indicator in stamp_indicators):
            preservation_data['stamp_text_preserved'] = False
        
        orig_doc.close()
        opt_doc.close()
        
    except Exception as e:
        log_and_print(f"Error during detailed comparison: {e}", 'error', True)
        preservation_data['content_analysis_errors'] += 1
        # Set all preservation to False if major error
        for key in preservation_data:
            if key.endswith('_preserved'):
                preservation_data[key] = False
    
    return preservation_data

def test_optimize_function():
    """Test the actual optimize_pdf function with different settings"""
    
    print(f"\n{'='*80}")
    print("TESTING OPTIMIZE_PDF FUNCTION")
    print(f"{'='*80}")
    
    log_and_print("Testing optimize_pdf function with different settings")
    
    if not os.path.exists(TEST_INPUT_PDF):
        log_and_print(f"ERROR: Test input file '{TEST_INPUT_PDF}' does not exist!", 'error', True)
        return
    
    baseline_info = get_file_info(TEST_INPUT_PDF)
    
    # First, diagnose the original PDF content
    diagnose_pdf_content(TEST_INPUT_PDF, "ORIGINAL PDF")
    
    # Test conservative optimization
    conservative_output = os.path.join(OUTPUT_DIR, 'optimized_conservative.pdf')
    print("\nTesting CONSERVATIVE optimization...")
    log_and_print("Testing CONSERVATIVE optimization")
    success = optimize_pdf(TEST_INPUT_PDF, conservative_output, aggressive=False)
    
    # Prepare CSV data for conservative test
    input_content_data = get_content_analysis_csv_data(TEST_INPUT_PDF, 'input')
    conservative_csv_data = {
        'timestamp': datetime.now().isoformat(),
        'test_type': 'optimize_function',
        'input_file': os.path.basename(TEST_INPUT_PDF),
        'input_size_kb': baseline_info['file_size_kb'],
        'input_size_mb': baseline_info['file_size_mb'],
        'input_pages': baseline_info['pages'],
        'input_objects': baseline_info['xref_length'],
        'optimization_method': 'conservative',
        'optimization_params': 'aggressive=False',
        'output_file': os.path.basename(conservative_output),
        **input_content_data
    }
    
    if success and os.path.exists(conservative_output):
        conservative_info = get_file_info(conservative_output)
        size_change = conservative_info['file_size_kb'] - baseline_info['file_size_kb']
        percent_change = (size_change / baseline_info['file_size_kb']) * 100
        objects_change = conservative_info['xref_length'] - baseline_info['xref_length']
        
        # Get output content analysis
        output_content_data = get_content_analysis_csv_data(conservative_output, 'output')
        
        # Get content preservation analysis
        preservation_data = compare_pdf_content_detailed(TEST_INPUT_PDF, conservative_output)
        
        # Calculate potential savings
        potential_savings = calculate_potential_savings(TEST_INPUT_PDF, OUTPUT_DIR)
        
        # Update CSV data with results
        conservative_csv_data.update({
            'output_size_kb': conservative_info['file_size_kb'],
            'output_size_mb': conservative_info['file_size_mb'],
            'output_pages': conservative_info['pages'],
            'output_objects': conservative_info['xref_length'],
            'size_change_kb': size_change,
            'size_change_percent': percent_change,
            'objects_change': objects_change,
            'success': True,
            'potential_max_savings_percent': potential_savings,
            'already_compressed': size_change > 0,  # If size increased, was already compressed
            'notes': 'Conservative optimization using optimize_pdf function',
            **output_content_data,
            **preservation_data
        })
        
        conservative_results = f"CONSERVATIVE RESULTS: {baseline_info['file_size_kb']:.2f} KB → {conservative_info['file_size_kb']:.2f} KB (Δ {size_change:+.2f} KB, {percent_change:+.1f}%), Objects: {baseline_info['xref_length']} → {conservative_info['xref_length']} (Δ {objects_change:+d})"
        log_and_print(conservative_results, print_also=True)
        
        # Diagnose the conservative optimized version
        diagnose_pdf_content(conservative_output, "CONSERVATIVE OPTIMIZED")
        
    else:
        log_and_print("CONSERVATIVE optimization FAILED!", 'error', True)
        potential_savings = calculate_potential_savings(TEST_INPUT_PDF, OUTPUT_DIR)
        conservative_csv_data.update({
            'success': False,
            'error_message': 'optimize_pdf function failed',
            'potential_max_savings_percent': potential_savings,
            'already_compressed': False,
            'notes': 'Conservative optimization using optimize_pdf function'
        })
    
    write_csv_result(conservative_csv_data)
    
    # Test aggressive optimization
    aggressive_output = os.path.join(OUTPUT_DIR, 'optimized_aggressive.pdf')
    print("\nTesting AGGRESSIVE optimization...")
    log_and_print("Testing AGGRESSIVE optimization")
    success = optimize_pdf(TEST_INPUT_PDF, aggressive_output, aggressive=True)
    
    # Prepare CSV data for aggressive test (reuse input analysis)
    aggressive_csv_data = {
        'timestamp': datetime.now().isoformat(),
        'test_type': 'optimize_function',
        'input_file': os.path.basename(TEST_INPUT_PDF),
        'input_size_kb': baseline_info['file_size_kb'],
        'input_size_mb': baseline_info['file_size_mb'],
        'input_pages': baseline_info['pages'],
        'input_objects': baseline_info['xref_length'],
        'optimization_method': 'aggressive',
        'optimization_params': 'aggressive=True',
        'output_file': os.path.basename(aggressive_output),
        **input_content_data
    }
    
    if success and os.path.exists(aggressive_output):
        aggressive_info = get_file_info(aggressive_output)
        size_change = aggressive_info['file_size_kb'] - baseline_info['file_size_kb']
        percent_change = (size_change / baseline_info['file_size_kb']) * 100
        objects_change = aggressive_info['xref_length'] - baseline_info['xref_length']
        
        # Get output content analysis
        aggressive_output_content_data = get_content_analysis_csv_data(aggressive_output, 'output')
        
        # Get content preservation analysis
        aggressive_preservation_data = compare_pdf_content_detailed(TEST_INPUT_PDF, aggressive_output)
        
        # Calculate potential savings (reuse from conservative test)
        potential_savings = calculate_potential_savings(TEST_INPUT_PDF, OUTPUT_DIR)
        
        # Update CSV data with results
        aggressive_csv_data.update({
            'output_size_kb': aggressive_info['file_size_kb'],
            'output_size_mb': aggressive_info['file_size_mb'],
            'output_pages': aggressive_info['pages'],
            'output_objects': aggressive_info['xref_length'],
            'size_change_kb': size_change,
            'size_change_percent': percent_change,
            'objects_change': objects_change,
            'success': True,
            'potential_max_savings_percent': potential_savings,
            'already_compressed': size_change > 0,  # If size increased, was already compressed
            'notes': 'Aggressive optimization using optimize_pdf function',
            **aggressive_output_content_data,
            **aggressive_preservation_data
        })
        
        aggressive_results = f"AGGRESSIVE RESULTS: {baseline_info['file_size_kb']:.2f} KB → {aggressive_info['file_size_kb']:.2f} KB (Δ {size_change:+.2f} KB, {percent_change:+.1f}%), Objects: {baseline_info['xref_length']} → {aggressive_info['xref_length']} (Δ {objects_change:+d})"
        log_and_print(aggressive_results, print_also=True)
        
        # Compare conservative vs aggressive
        if os.path.exists(conservative_output):
            conservative_info = get_file_info(conservative_output)
            diff = aggressive_info['file_size_kb'] - conservative_info['file_size_kb']
            log_and_print(f"Aggressive vs Conservative: {diff:+.2f} KB difference", print_also=True)
        
        # Diagnose the aggressive optimized version
        diagnose_pdf_content(aggressive_output, "AGGRESSIVE OPTIMIZED")
        
    else:
        log_and_print("AGGRESSIVE optimization FAILED!", 'error', True)
        potential_savings = calculate_potential_savings(TEST_INPUT_PDF, OUTPUT_DIR)
        aggressive_csv_data.update({
            'success': False,
            'error_message': 'optimize_pdf function failed',
            'potential_max_savings_percent': potential_savings,
            'already_compressed': False,
            'notes': 'Aggressive optimization using optimize_pdf function'
        })
    
    write_csv_result(aggressive_csv_data)

def diagnose_pdf_content(pdf_path, description="PDF"):
    """Diagnostic analysis of PDF content to understand what might be affected by optimization"""
    
    print(f"\nDiagnosing content: {description}")
    log_and_print(f"CONTENT DIAGNOSIS: {description}")
    
    try:
        doc = fitz.open(pdf_path)
        
        # Check first few pages for detailed analysis
        for page_num in range(min(2, doc.page_count)):  # Check first 2 pages
            page = doc[page_num]
            log_and_print(f"PAGE {page_num + 1} CONTENT ANALYSIS:")
            
            # 1. Check annotations (stamps, signatures, etc.)
            annotations = [an for an in page.annots()]
            if annotations:
                log_and_print(f"  Annotations: {len(annotations)} found", print_also=True)
                for i, annot in enumerate(annotations):
                    try:
                        annot_type = annot.type[1] if len(annot.type) > 1 else "Unknown"
                        rect = annot.rect
                        log_and_print(f"    {i+1}. {annot_type} at {rect}")
                        
                        # Get annotation content
                        try:
                            content = annot.info.get('content', '')
                            if content:
                                log_and_print(f"        Content: {content[:50]}...")
                        except:
                            pass
                    except Exception as e:
                        log_and_print(f"    {i+1}. Could not read annotation: {e}")
            else:
                log_and_print("  Annotations: None found")
            
            # 2. Check for signature fields and widgets
            try:
                widgets = [w for w in page.widgets()]
                if widgets:
                    log_and_print(f"  Interactive elements: {len(widgets)} found", print_also=True)
                    for widget in widgets:
                        widget_type = getattr(widget, 'field_type_string', 'Unknown')
                        widget_name = getattr(widget, 'field_name', 'Unnamed')
                        log_and_print(f"    {widget_type} field: {widget_name} at {widget.rect}")
                        
                        if widget_type == 'Signature':
                            log_and_print(f"        ⚠ SIGNATURE FIELD - may be affected by optimization", print_also=True)
                else:
                    log_and_print("  Interactive elements: None found")
            except Exception as e:
                log_and_print(f"  Interactive elements: Could not check ({e})")
            
            # 3. Check for drawings/vector graphics (stamps, watermarks)
            try:
                drawings = [dr for dr in page.get_drawings()]
                if drawings:
                    log_and_print(f"  Vector drawings: {len(drawings)} found", print_also=True)
                    for i, drawing in enumerate(drawings[:3]):  # Show first 3
                        drawing_type = drawing.get('type', 'unknown')
                        drawing_rect = drawing.get('rect', 'unknown position')
                        log_and_print(f"    {i+1}. {drawing_type} at {drawing_rect}")
                        if 'stroke' in drawing or 'fill' in drawing:
                            log_and_print(f"        ⚠ VECTOR GRAPHIC - optimization may affect appearance", print_also=True)
                else:
                    log_and_print("  Vector drawings: None found")
            except Exception as e:
                log_and_print(f"  Vector drawings: Could not analyze ({e})")
            
            # 4. Check text content for signature/stamp indicators
            try:
                text = page.get_text()
                
                # Look for signature/stamp related content
                signature_indicators = [
                    'digitally signed', 'leidy.garcia', 'raleighnc.gov', 'city of raleigh', 
                    'authorized', 'disclosure', 'approved', 'stamp'
                ]
                
                stamp_indicators = ['04/17/2025', 'APPROVED', 'BLDNR-017613-2025']
                
                found_sig_content = []
                found_stamp_content = []
                
                lines = text.split('\n')
                for line in lines:
                    line_lower = line.lower().strip()
                    
                    # Check for signature content
                    for indicator in signature_indicators:
                        if indicator in line_lower and line.strip():
                            found_sig_content.append(line.strip()[:100])
                            break
                    
                    # Check for stamp content
                    for indicator in stamp_indicators:
                        if indicator in line and line.strip():
                            found_stamp_content.append(line.strip()[:100])
                            break
                
                if found_sig_content:
                    log_and_print("  ⚠ SIGNATURE/DISCLOSURE TEXT found:", print_also=True)
                    for content in found_sig_content[:3]:  # Show first 3
                        log_and_print(f"    '{content}'")
                
                if found_stamp_content:
                    log_and_print("  ⚠ STAMP/APPROVAL TEXT found:", print_also=True)
                    for content in found_stamp_content[:3]:  # Show first 3
                        log_and_print(f"    '{content}'")
                
                if not found_sig_content and not found_stamp_content:
                    log_and_print("  Text content: No signature/stamp text detected")
                    
            except Exception as e:
                log_and_print(f"  Text analysis: Could not extract text ({e})")
            
            # 5. Check images (may contain embedded stamps)
            images = [im for im in page.get_images()]
            if images:
                log_and_print(f"  Images: {len(images)} found", print_also=True)
                for i, img_info in enumerate(images[:2]):  # Check first 2 images
                    try:
                        xref = img_info[0]
                        img_dict = doc.extract_image(xref)
                        width = img_dict.get('width', '?')
                        height = img_dict.get('height', '?')
                        ext = img_dict.get('ext', '?')
                        
                        # Small images might be stamps/logos
                        if isinstance(width, int) and isinstance(height, int):
                            if width < 200 and height < 200:
                                log_and_print(f"    {i+1}. {width}x{height} {ext} ⚠ SMALL IMAGE - possibly stamp/logo", print_also=True)
                            else:
                                log_and_print(f"    {i+1}. {width}x{height} {ext}")
                        else:
                            log_and_print(f"    {i+1}. {width}x{height} {ext}")
                    except:
                        log_and_print(f"    {i+1}. Could not extract image details")
            else:
                log_and_print("  Images: None found")
            
            # 6. Check for optional content (layers) - stamps might be on layers
            try:
                oc_groups = dict(doc.get_ocgs()) if hasattr(doc, 'get_ocgs') else {}
                if oc_groups:
                    log_and_print(f"  Optional content layers: {len(oc_groups)} found", print_also=True)
                    for oc_xref, oc_info in list(oc_groups.items())[:3]:  # Show first 3
                        log_and_print(f"    Layer: {oc_info}")
                        log_and_print(f"        ⚠ LAYERED CONTENT - optimization may affect visibility", print_also=True)
                else:
                    log_and_print("  Optional content layers: None found")
            except:
                log_and_print("  Optional content layers: Could not check")
        
        doc.close()
        
    except Exception as e:
        log_and_print(f"Error during content diagnosis: {e}", 'error', True)

def analyze_why_no_optimization(pdf_path):
    """Analyze why a PDF might not be optimizing well"""
    
    print("\nAnalyzing optimization limitations...")
    log_and_print("ANALYZING WHY OPTIMIZATION MAY BE LIMITED")
    
    analysis = analyze_pdf_bloat(pdf_path)
    if not analysis:
        log_and_print("Could not analyze PDF", 'error', True)
        return
    
    reasons = []
    
    # Check file size
    if analysis['original_size_mb'] < 1.0:
        reasons.append(f"Small file size ({analysis['original_size_mb']:.2f} MB) - limited optimization potential")
    
    # Check for optimization opportunities
    if analysis['fonts']['unique_fonts'] <= 3:
        reasons.append("Few unique fonts - limited font deduplication opportunities")
    
    if len(analysis['fonts']['duplicated_fonts']) == 0:
        reasons.append("No duplicated fonts found - already optimized font usage")
    
    if analysis['images'] == 0:
        reasons.append("No images - cannot optimize image compression")
    
    if analysis['annotations'] == 0 and analysis['widgets'] == 0:
        reasons.append("No annotations or form fields - fewer objects to clean up")
    
    # Test if the PDF is already compressed
    doc = fitz.open(pdf_path)
    original_size = os.path.getsize(pdf_path)
    
    # Save with minimal settings to see baseline
    test_path = os.path.join(OUTPUT_DIR, 'minimal_test.pdf')
    doc.save(test_path, deflate=False, clean=False, garbage=0)
    minimal_size = os.path.getsize(test_path)
    
    # Save with maximum compression
    max_test_path = os.path.join(OUTPUT_DIR, 'max_test.pdf')
    doc.save(max_test_path, deflate=True, clean=True, garbage=4)
    max_compressed_size = os.path.getsize(max_test_path)
    
    doc.close()
    
    # Calculate compression ratios
    if minimal_size > original_size * 1.1:  # 10% larger
        reasons.append("PDF is already well-compressed (adding compression makes it larger)")
    
    potential_savings = ((original_size - max_compressed_size) / original_size) * 100
    if potential_savings < 5:
        reasons.append(f"Maximum possible optimization is only {potential_savings:.1f}%")
    
    log_and_print("Possible reasons for limited optimization:", print_also=True)
    for i, reason in enumerate(reasons, 1):
        log_and_print(f"  {i}. {reason}", print_also=True)
    
    if not reasons:
        log_and_print("  PDF should have good optimization potential - check optimization settings", print_also=True)
    
    compression_analysis = f"Compression Analysis: Original: {original_size/1024:.2f} KB, Uncompressed: {minimal_size/1024:.2f} KB, Max compressed: {max_compressed_size/1024:.2f} KB, Max potential savings: {potential_savings:.1f}%"
    log_and_print(compression_analysis, print_also=True)
    
    # Run content diagnosis to understand what might be affected
    diagnose_pdf_content(pdf_path, "Original PDF")
    
    # Also diagnose the optimized version if it exists
    optimized_path = max_test_path
    if os.path.exists(optimized_path):
        diagnose_pdf_content(optimized_path, "Optimized PDF")
        
        # Compare content between original and optimized
        log_and_print("CONTENT COMPARISON: ORIGINAL vs OPTIMIZED")
        
        try:
            original_doc = fitz.open(pdf_path)
            optimized_doc = fitz.open(optimized_path)
            
            # Compare first page text content
            orig_text = original_doc[0].get_text()
            opt_text = optimized_doc[0].get_text()
            
            if orig_text != opt_text:
                log_and_print("⚠ WARNING: Text content differs between original and optimized!", print_also=True)
                log_and_print(f"  Original text length: {len(orig_text)} chars", print_also=True)
                log_and_print(f"  Optimized text length: {len(opt_text)} chars", print_also=True)
            else:
                log_and_print("✓ Text content preserved in optimization", print_also=True)
            
            # Compare annotations
            orig_annots = len([an for an in original_doc[0].annots()])
            opt_annots = len([an for an in optimized_doc[0].annots()])
            
            if orig_annots != opt_annots:
                log_and_print(f"⚠ WARNING: Annotation count changed from {orig_annots} to {opt_annots}", print_also=True)
            else:
                log_and_print(f"✓ Annotations preserved ({orig_annots} annotations)", print_also=True)
            
            # Compare images
            orig_images = len(original_doc[0].get_images())
            opt_images = len(optimized_doc[0].get_images())
            
            if orig_images != opt_images:
                log_and_print(f"⚠ WARNING: Image count changed from {orig_images} to {opt_images}", print_also=True)
            else:
                log_and_print(f"✓ Images preserved ({orig_images} images)", print_also=True)
            
            original_doc.close()
            optimized_doc.close()
            
        except Exception as e:
            log_and_print(f"Could not compare content: {e}", 'error', True)
    
    # Clean up test files
    try:
        os.remove(test_path)
        os.remove(max_test_path)
    except:
        pass

def test_different_pdfs():
    """Test optimization on different types of PDFs if available"""
    
    print(f"\n{'='*80}")
    print("TESTING DIFFERENT PDF TYPES")
    print(f"{'='*80}")
    
    log_and_print("Testing different PDF types")
    
    # Look for different test files
    test_files_dir = os.path.dirname(TEST_INPUT_PDF)
    if os.path.exists(test_files_dir):
        pdf_files = [f for f in os.listdir(test_files_dir) if f.lower().endswith('.pdf')]
        
        log_and_print(f"Found {len(pdf_files)} PDF files in test directory:", print_also=True)
        for pdf_file in pdf_files:
            pdf_path = os.path.join(test_files_dir, pdf_file)
            info = get_file_info(pdf_path)
            if info:
                file_info = f"{pdf_file}: {info['file_size_kb']:.2f} KB, {info['pages']} pages"
                log_and_print(file_info, print_also=True)
                
                # Quick optimization test
                output_path = os.path.join(OUTPUT_DIR, f'opt_{pdf_file}')
                input_content_data = get_content_analysis_csv_data(pdf_path, 'input')
                
                csv_data = {
                    'timestamp': datetime.now().isoformat(),
                    'test_type': 'different_pdf_types',
                    'input_file': pdf_file,
                    'input_size_kb': info['file_size_kb'],
                    'input_size_mb': info['file_size_mb'],
                    'input_pages': info['pages'],
                    'input_objects': info['xref_length'],
                    'optimization_method': 'aggressive',
                    'optimization_params': 'aggressive=True',
                    'output_file': os.path.basename(output_path),
                    **input_content_data
                }
                
                success = optimize_pdf(pdf_path, output_path, aggressive=True)
                if success:
                    opt_info = get_file_info(output_path)
                    change = ((opt_info['file_size_kb'] - info['file_size_kb']) / info['file_size_kb']) * 100
                    objects_change = opt_info['xref_length'] - info['xref_length']
                    size_change_kb = opt_info['file_size_kb'] - info['file_size_kb']
                    
                    # Get output content analysis and preservation data
                    output_content_data = get_content_analysis_csv_data(output_path, 'output')
                    preservation_data = compare_pdf_content_detailed(pdf_path, output_path)
                    
                    csv_data.update({
                        'output_size_kb': opt_info['file_size_kb'],
                        'output_size_mb': opt_info['file_size_mb'],
                        'output_pages': opt_info['pages'],
                        'output_objects': opt_info['xref_length'],
                        'size_change_kb': size_change_kb,
                        'size_change_percent': change,
                        'objects_change': objects_change,
                        'success': True,
                        'notes': f'Tested from {test_files_dir}',
                        **output_content_data,
                        **preservation_data
                    })
                    
                    result_msg = f"  → Optimized: {opt_info['file_size_kb']:.2f} KB ({change:+.1f}%)"
                    log_and_print(result_msg, print_also=True)
                    
                    # If optimization was minimal, analyze why
                    if abs(change) < 5:
                        analyze_why_no_optimization(pdf_path)
                else:
                    csv_data.update({
                        'success': False,
                        'error_message': 'optimize_pdf function failed',
                        'notes': f'Tested from {test_files_dir}'
                    })
                
                write_csv_result(csv_data)
    else:
        log_and_print(f"Test files directory '{test_files_dir}' not found", print_also=True)
        
        # Try to find any PDFs in the current directory or common locations
        search_dirs = [
            os.getcwd(),
            os.path.join(os.getcwd(), "tests"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents")
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                pdf_files = [f for f in os.listdir(search_dir) if f.lower().endswith('.pdf')]
                if pdf_files:
                    log_and_print(f"Found PDFs in {search_dir}:", print_also=True)
                    for pdf_file in pdf_files[:3]:  # Test first 3 PDFs found
                        pdf_path = os.path.join(search_dir, pdf_file)
                        info = get_file_info(pdf_path)
                        if info and info['file_size_mb'] < 50:  # Skip very large files
                            file_info = f"{pdf_file}: {info['file_size_kb']:.2f} KB, {info['pages']} pages"
                            log_and_print(file_info, print_also=True)
                            
                            output_path = os.path.join(OUTPUT_DIR, f'found_{pdf_file}')
                            found_input_content_data = get_content_analysis_csv_data(pdf_path, 'input')
                            
                            csv_data = {
                                'timestamp': datetime.now().isoformat(),
                                'test_type': 'found_pdf_types',
                                'input_file': pdf_file,
                                'input_size_kb': info['file_size_kb'],
                                'input_size_mb': info['file_size_mb'],
                                'input_pages': info['pages'],
                                'input_objects': info['xref_length'],
                                'optimization_method': 'aggressive',
                                'optimization_params': 'aggressive=True',
                                'output_file': os.path.basename(output_path),
                                **found_input_content_data
                            }
                            
                            success = optimize_pdf(pdf_path, output_path, aggressive=True)
                            if success:
                                opt_info = get_file_info(output_path)
                                change = ((opt_info['file_size_kb'] - info['file_size_kb']) / info['file_size_kb']) * 100
                                objects_change = opt_info['xref_length'] - info['xref_length']
                                size_change_kb = opt_info['file_size_kb'] - info['file_size_kb']
                                
                                # Get output content analysis and preservation data
                                found_output_content_data = get_content_analysis_csv_data(output_path, 'output')
                                found_preservation_data = compare_pdf_content_detailed(pdf_path, output_path)
                                
                                csv_data.update({
                                    'output_size_kb': opt_info['file_size_kb'],
                                    'output_size_mb': opt_info['file_size_mb'],
                                    'output_pages': opt_info['pages'],
                                    'output_objects': opt_info['xref_length'],
                                    'size_change_kb': size_change_kb,
                                    'size_change_percent': change,
                                    'objects_change': objects_change,
                                    'success': True,
                                    'notes': f'Found in {search_dir}',
                                    **found_output_content_data,
                                    **found_preservation_data
                                })
                                
                                result_msg = f"  → Optimized: {opt_info['file_size_kb']:.2f} KB ({change:+.1f}%)"
                                log_and_print(result_msg, print_also=True)
                                
                                if abs(change) < 5:
                                    analyze_why_no_optimization(pdf_path)
                            else:
                                csv_data.update({
                                    'success': False,
                                    'error_message': 'optimize_pdf function failed',
                                    'notes': f'Found in {search_dir}'
                                })
                            
                            write_csv_result(csv_data)
                    break



def test_optimize_pdf():
    """Main test function that runs all optimization tests"""
    
    print(f"{'='*80}")
    print("PDF OPTIMIZATION TESTING SUITE")
    print(f"{'='*80}")
    
    log_and_print("Starting PDF Optimization Testing Suite", print_also=True)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Test the main optimization function on sample PDF
    test_optimize_function()
    
    # Test on original sample if it exists
    if os.path.exists(TEST_INPUT_PDF):
        print("\nTesting individual optimization methods on sample PDF...")
        log_and_print("TESTING INDIVIDUAL OPTIMIZATION METHODS ON SAMPLE PDF")
        test_individual_optimizations(TEST_INPUT_PDF)
    else:
        log_and_print(f"WARNING: Sample PDF '{TEST_INPUT_PDF}' not found!", print_also=True)
        log_and_print("Looking for any PDFs in the tests directory...", print_also=True)
    
    # Test on different PDF types
    test_different_pdfs()
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print(f"{'='*80}")
    
    completion_msg = f"Testing complete. Check the output directory '{OUTPUT_DIR}' for all generated test files."
    log_and_print(completion_msg, print_also=True)
    
    # Summary and recommendations
    log_and_print("ANALYSIS SUMMARY & RECOMMENDATIONS", print_also=True)
    log_and_print("If optimization shows minimal file size reduction:", print_also=True)
    log_and_print("1. The PDF may already be well-optimized", print_also=True)
    log_and_print("2. The PDF contains mostly compressed images or text", print_also=True)
    log_and_print("3. Try more aggressive settings in the optimize_pdf function", print_also=True)
    log_and_print("4. Consider PDFs with forms, annotations, or embedded fonts for better results", print_also=True)

if __name__ == "__main__":
    test_optimize_pdf()

