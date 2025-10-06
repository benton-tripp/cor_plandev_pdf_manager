// pdfExtract.js - PDF page extraction functionality
import { state, setState, closeModal } from './state.js';
import { openModal, validateFilename, validateFolder } from './utils.js';

// Track total pages for extract validation
let extractTotalPages = 0;

// Track extract progress
function trackExtractProgress(jobId) {
  setState('currentExtractJobId', jobId); // Store job ID for cancellation
  
  const poll = () => {
    $.ajax({
      url: `/api/extract_progress/${jobId}`,
      type: 'GET',
      success: function(data) {
        console.log('Extract progress data received:', data);

        if (data.error) {
          closeModal('extract-progress-modal');
          alert('Error: ' + data.error);
          return;
        }
        
        // Update the UI with latest data
        updateExtractProgress(data.message || 'Processing...');
        
        if (data.status === 'complete') {
          // User shouldn't be able to press cancel here
          $('#extract-cancel-btn').prop('disabled', true).text('Cancel');
          setState('currentExtractJobId', null);
          setState('currentExtractRequest', null);
          setTimeout(() => {
            closeModal('extract-progress-modal');
            if (data.filename) {
              alert('Pages extracted successfully!\nSaved to: ' + data.filename);
            }
          }, 1000); // Show completion message for a moment
          // Re-enable cancel button and clear job ID and request
          $('#extract-cancel-btn').prop('disabled', false).text('Cancel');
        } else if (data.status === 'cancelled') {
          // Re-enable cancel button and clear job ID and request
          $('#extract-cancel-btn').prop('disabled', false).text('Cancel');
          setState('currentExtractJobId', null);
          setState('currentExtractRequest', null);
          closeModal('extract-progress-modal');
          alert('Page extraction was cancelled.');
        } else if (data.status === 'error') {
          // Re-enable cancel button and clear job ID and request
          $('#extract-cancel-btn').prop('disabled', false).text('Cancel');
          setState('currentExtractJobId', null);
          setState('currentExtractRequest', null);
          closeModal('extract-progress-modal');
          alert('Error: ' + (data.message || 'Extract failed'));
        } else {
          // Continue polling
          setTimeout(poll, 500); // Poll every 500ms
        }
      },
      error: function(xhr, status, error) {
        console.log('Extract progress polling error:', xhr.responseText, status, error);
        // Re-enable cancel button and clear job ID and request on error
        $('#extract-cancel-btn').prop('disabled', false).text('Cancel');
        setState('currentExtractJobId', null);
        setState('currentExtractRequest', null);
        closeModal('extract-progress-modal');
        alert('Error: Lost connection to server');
      }
    });
  };
  
  poll();
}

// Update extract progress display
function updateExtractProgress(message) {
  console.log('Updating extract progress:', {message});
  $('#extract-progress-status').text(message || 'Processing...');
}

// Initialize extract cancel button handler
function initializeExtractCancel() {
  $('#extract-cancel-btn').on('click', function() {
    if (state.currentExtractJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#extract-progress-status').text('Cancellation requested...');
      
      // If job is still pending (during startup), abort request and close modal immediately
      if (state.currentExtractJobId === 'pending') {
        // Abort the ongoing request if it exists
        if (state.currentExtractRequest) {
          state.currentExtractRequest.abort();
          setState('currentExtractRequest', null);
        }
        closeModal('extract-progress-modal');
        setState('currentExtractJobId', null);
        return;
      }
      
      $.ajax({
        url: `/api/cancel_extract/${state.currentExtractJobId}`,
        type: 'POST',
        success: function(data) {
          console.log('Extract cancel request sent:', data);
          // Show faster feedback
          $('#extract-progress-status').text('Cancelling operation, please wait...');
          // Progress polling will handle the actual cleanup and modal closing
        },
        error: function(xhr, status, error) {
          console.log('Extract cancel request error:', error);
          // Re-enable button if cancel request failed
          $('#extract-cancel-btn').prop('disabled', false).text('Cancel');
          $('#extract-progress-status').text('Cancel request failed');
        }
      });
    }
  });
}

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

    // Close the extract modal and show progress modal
    closeModal('extract-modal');
    openModal('extract-progress-modal');
    
    // Reset progress display and ensure cancel button is enabled
    $('#extract-progress-status').text('Starting page extraction...');
    $('#extract-cancel-btn').prop('disabled', false).text('Cancel');
    
    // Set a temporary job ID so cancel button works during startup
    setState('currentExtractJobId', 'pending');

    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('pages', pages);
    
    let extractRequest = $.ajax({
      url: '/api/extract_pages',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        // Check if we were cancelled during startup
        if (state.currentExtractJobId === null) {
          console.log('Extract was cancelled during startup, ignoring response');
          // If we got a job ID back but were cancelled, cancel it immediately
          if (data.success && data.job_id) {
            $.ajax({
              url: `/api/cancel_extract/${data.job_id}`,
              type: 'POST',
              success: function() {
                console.log('Cancelled extract job that started after user cancellation');
              }
            });
          }
          return;
        }
        
        if (data.success && data.job_id) {
          // Update with real job ID and start tracking progress
          setState('currentExtractJobId', data.job_id);
          trackExtractProgress(data.job_id);
        } else {
          setState('currentExtractJobId', null);
          setState('currentExtractRequest', null);
          closeModal('extract-progress-modal');
          alert('Error starting extraction: ' + (data.error || 'Unknown error'));
        }
      },
      error: function(xhr, status, error) {
        console.log('Extract request error:', {status, error, xhr_status: xhr.status, currentJobId: state.currentExtractJobId});
        
        // Only show error if we weren't cancelled during startup
        if (state.currentExtractJobId !== null) {
          setState('currentExtractJobId', null);
          setState('currentExtractRequest', null);
          closeModal('extract-progress-modal');
          
          // Check if this was an aborted request (user cancelled)
          if (status === 'abort' || xhr.status === 0) {
            // Request was aborted - don't show error message
            console.log('Extract request was aborted by user cancellation');
          } else {
            // Actual error occurred - try to parse the response
            let errorMessage = 'Unknown error occurred';
            try {
              if (xhr.responseText) {
                const response = JSON.parse(xhr.responseText);
                errorMessage = response.error || xhr.responseText;
              } else if (error) {
                errorMessage = error;
              }
            } catch (e) {
              errorMessage = xhr.responseText || error || 'Unknown error occurred';
            }
            alert('Error starting extraction: ' + errorMessage);
          }
        } else {
          // Request was cancelled during startup - just log it
          console.log('Extract request completed after user cancellation - ignoring error');
        }
      }
    });
    
    // Store the request so we can abort it if needed
    setState('currentExtractRequest', extractRequest);
  });

  // Initialize cancel button functionality
  initializeExtractCancel();
}