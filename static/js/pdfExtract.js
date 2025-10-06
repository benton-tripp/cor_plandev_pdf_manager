// pdfExtract.js - PDF page extraction functionality
import { state, setState, closeModal } from './state.js';
import { showToolSpinner, hideToolSpinner, validateFilename, validateFolder } from './utils.js';

// Track total pages for extract validation
let extractTotalPages = 0;

// Parse page numbers from a string format
function parsePageNumbers(pageString) {
    const pages = [];
    
    if (!pageString || !pageString.trim()) {
        return { pages: [], error: 'No pages specified' };
    }
    
    // Split by commas first
    const parts = pageString.split(',');
    
    for (let part of parts) {
        part = part.trim();
        if (!part) continue;
        
        if (part.includes('-')) {
            // Handle range like "3-7"
            const rangeParts = part.split('-');
            if (rangeParts.length !== 2) {
                return { pages: [], error: `Invalid range format: '${part}'. Use format like '3-7'` };
            }
            
            const start = parseInt(rangeParts[0].trim());
            const end = parseInt(rangeParts[1].trim());
            
            if (isNaN(start) || isNaN(end)) {
                return { pages: [], error: `Invalid numbers in range: '${part}'` };
            }
            
            if (start > end) {
                return { pages: [], error: `Invalid range: '${part}'. Start page must be less than or equal to end page` };
            }
            
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
        } else {
            // Handle single page number
            const pageNum = parseInt(part);
            if (isNaN(pageNum)) {
                return { pages: [], error: `Invalid page number: '${part}'. Only numbers, commas, and hyphens are allowed` };
            }
            pages.push(pageNum);
        }
    }
    
    // Remove duplicates and sort
    const uniquePages = [...new Set(pages)].sort((a, b) => a - b);
    
    // Validate against total pages if we have that info
    if (extractTotalPages > 0) {
        const invalidPages = uniquePages.filter(p => p < 1 || p > extractTotalPages);
        if (invalidPages.length > 0) {
            return { 
                pages: [], 
                error: `Invalid page number(s): ${invalidPages.join(', ')}. This PDF has ${extractTotalPages} pages (valid range: 1-${extractTotalPages})` 
            };
        }
    }
    
    return { pages: uniquePages, error: null };
}

// Validate inputs for extract pages tool
function validateExtractInputs() {
    let file = $('#extract-input')[0].files[0];
    let fname = $('#extract-filename').val();
    let outputFolder = $('#extract-output-folder').val();
    let pages = $('#extract-pages').val();
    
    // Clear previous error messages
    $('#extract-message').text('');
    
    let isValidFilename = validateFilename(fname);
    let isValidFolder = validateFolder(outputFolder);
    
    // Validate page numbers only if we have a file selected
    let isValidPages = false;
    if (pages && pages.trim().length > 0) {
        if (!file) {
            // If there are page numbers but no file, don't validate page numbers yet
            isValidPages = false;
        } else {
            const parseResult = parsePageNumbers(pages);
            if (parseResult.error) {
                $('#extract-message').text(parseResult.error);
                isValidPages = false;
            } else if (parseResult.pages.length === 0) {
                $('#extract-message').text('No valid pages specified');
                isValidPages = false;
            } else {
                isValidPages = true;
            }
        }
    }
    
    let canRun = file && isValidFilename && isValidFolder && isValidPages;
    
    $('#extract-run').prop('disabled', !canRun);
}

// Initialize extract PDF functionality
export function initializeExtract() {
  $('#extract-input').on('change', function() {
    let file = this.files[0];
    if (file) {
      let baseName = file.name.replace(/\.[^/.]+$/, "");
      $('#extract-filename').val(baseName + '_extracted').prop('disabled', false);
      $('#extract-output-folder').val(state.defaultOutputFolder);
      
      // Reset page count and clear any previous messages
      extractTotalPages = 0;
      $('#extract-message').text('');
      
      // Get page count using PDF.js
      let reader = new FileReader();
      reader.onload = function(ev) {
        if (window.pdfjsLib) {
          const loadingTask = pdfjsLib.getDocument({data: ev.target.result});
          loadingTask.promise.then(pdf => {
            extractTotalPages = pdf.numPages;
            console.log('Extract PDF page count:', extractTotalPages);
            
            // Re-validate with actual page count
            validateExtractInputs();
          }).catch(error => {
            console.error('PDF.js failed to load PDF for extract:', error);
            extractTotalPages = 0;
            $('#extract-message').text('Could not read PDF file. Please check if this is a valid PDF.');
            validateExtractInputs();
          });
        } else {
          console.error('PDF.js library not loaded for extract');
          extractTotalPages = 0;
          $('#extract-message').text('PDF processing library not available.');
        }
      };
      reader.readAsArrayBuffer(file);
      
      validateExtractInputs();
    } else {
      $('#extract-filename').val('').prop('disabled', true);
      $('#extract-output-folder').val('');
      $('#extract-pages').val('');
      extractTotalPages = 0;
      $('#extract-message').text(''); // Clear any previous messages
      validateExtractInputs();
    }
  });
  
  $('#extract-filename, #extract-pages').on('input', validateExtractInputs);
  $('#extract-output-folder').on('input', validateExtractInputs);
  
  $('#extract-run').on('click', function() {
    let file = $('#extract-input')[0].files[0];
    let fname = $('#extract-filename').val();
    let outputFolder = $('#extract-output-folder').val();
    let pages = $('#extract-pages').val();
    
    // Clear any previous error messages
    $('#extract-message').text('');
    
    if (!file || !fname || !pages) {
      $('#extract-message').text('Please fill in all required fields.');
      return;
    }

    // Final validation of page numbers
    const parseResult = parsePageNumbers(pages);
    if (parseResult.error) {
      $('#extract-message').text(parseResult.error);
      return;
    }
    
    if (parseResult.pages.length === 0) {
      $('#extract-message').text('No valid pages specified.');
      return;
    }

    console.log('Extract run clicked:', {file: file.name, fname, outputFolder, pages, validPages: parseResult.pages});

    showToolSpinner();
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('pages', pages);
    $.ajax({
      url: '/api/extract_pages',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        hideToolSpinner();
        if (data.success && data.filename) {
          closeModal('extract-modal');
          alert('Pages extracted successfully!\nSaved to: ' + data.filename);
        } else if (!data.success && data.error) {
          $('#extract-message').text('Error: ' + data.error);
        } else {
          $('#extract-message').text('An unknown error occurred.');
        }
      },
      error: function(xhr) {
        hideToolSpinner();
        $('#extract-message').text('Error: ' + xhr.responseText);
      }
    });
  });
}