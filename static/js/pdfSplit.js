// pdfSplit.js - PDF splitting functionality
import { state, setState, closeModal } from './state.js';
import { validateFilename, validateFolder } from './utils.js';

// Show split progress modal
function showSplitProgress() {
  $('#split-progress-modal').fadeIn(200);
  $('#split-cancel-btn').prop('disabled', false).text('Cancel');
  updateSplitProgress(0, 0, 0, 0, 0, 'Initializing...');
}

// Hide split progress modal
function hideSplitProgress() {
  $('#split-progress-modal').fadeOut(200);
  setState('currentSplitJobId', null);
}

// Update split progress
function updateSplitProgress(currentPage, totalPages, currentChunk, totalChunks, percentage, message) {
  console.log('Updating progress:', {currentPage, totalPages, currentChunk, totalChunks, percentage, message}); // Debug logging
  
  // Better page display
  if (totalPages > 0) {
    $('#progress-pages').text(`Page ${currentPage} of ${totalPages} processed`);
  } else {
    $('#progress-pages').text('Initializing...');
  }
  
  // Better chunk display - show current completion status with context
  if (totalChunks > 0) {
    if (message && message.includes('Starting chunk')) {
      $('#progress-chunks').text(`${currentChunk} of ${totalChunks} chunks complete (starting chunk ${currentChunk + 1})`);
    } else if (message && message.includes('Saving chunk')) {
      $('#progress-chunks').text(`${currentChunk} of ${totalChunks} chunks complete (saving chunk ${currentChunk + 1})`);
    } else {
      $('#progress-chunks').text(`${currentChunk} of ${totalChunks} chunks complete`);
    }
  } else {
    $('#progress-chunks').text('Calculating chunks...');
  }
  
  $('#progress-fill').css('width', percentage + '%');
  $('#progress-percentage').text(percentage + '%');
  $('#progress-status').text(message);
}

// Poll for split progress with adaptive polling for important state changes
function pollSplitProgress(jobId) {
  setState('currentSplitJobId', jobId); // Store job ID for cancellation
  
  let lastState = {
    currentPage: 0,
    currentChunk: 0,
    message: '',
    percentage: 0
  };
  
  const poll = () => {
    $.ajax({
      url: `/api/split_progress/${jobId}`,
      type: 'GET',
      success: function(data) {
        console.log('Progress data received:', data); // Debug logging
        
        if (data.error) {
          hideSplitProgress();
          $('#split-message').text('Error: ' + data.error);
          return;
        }
        
        // Always update the UI with latest data
        updateSplitProgress(
          data.current_page || 0,
          data.total_pages || 0,
          data.current_chunk || 0,
          data.total_chunks || 0,
          data.percentage || 0,
          data.message || 'Processing...'
        );
        
        // Detect important state changes (non-page updates)
        const currentMessage = data.message || 'Processing...';
        const isImportantStateChange = (
          // New chunk operations (starting or saving)
          (currentMessage.includes('Starting chunk') && !lastState.message.includes('Starting chunk')) ||
          (currentMessage.includes('Saving chunk') && !lastState.message.includes('Saving chunk')) ||
          // Zip creation or completion phases
          (currentMessage.includes('Creating zip') && !lastState.message.includes('Creating zip')) ||
          (currentMessage.includes('Complete') && !lastState.message.includes('Complete')) ||
          // Chunk progress changes (not just page changes)
          (data.current_chunk !== lastState.currentChunk) ||
          // Significant percentage jumps (like going to zip creation phase)
          (Math.abs((data.percentage || 0) - lastState.percentage) > 10)
        );
        
        // Update our state tracking
        lastState = {
          currentPage: data.current_page || 0,
          currentChunk: data.current_chunk || 0,
          message: currentMessage,
          percentage: data.percentage || 0
        };
        
        if (data.status === 'complete') {
          setTimeout(() => {
            hideSplitProgress();
            closeModal('split-modal');
            if (data.zipfile) {
              alert('PDF split successfully!\nSaved to: ' + data.zipfile);
            }
          }, 1000); // Show 100% for a moment before closing
        } else if (data.status === 'cancelled') {
          hideSplitProgress();
          closeModal('split-modal');
          alert('PDF split was cancelled.');
        } else if (data.status === 'error') {
          hideSplitProgress();
          $('#split-message').text('Error: ' + (data.message || 'Split failed'));
        } else {
          // Adaptive polling: faster for important state changes, regular for page updates
          let pollInterval;
          if (currentMessage.includes('Cancelling') || currentMessage.includes('Cancellation')) {
            // Very fast polling when cancellation is in progress
            pollInterval = 25; // 25ms for cancellation feedback
            console.log('Cancellation detected, using very fast polling (25ms):', currentMessage);
          } else if (isImportantStateChange) {
            // More frequent polling when important operations are happening
            pollInterval = 50; // 50ms for critical state changes
            console.log('Important state change detected, using fast polling (50ms):', currentMessage);
          } else if (currentMessage.includes('Saving') || currentMessage.includes('Creating')) {
            // Medium polling during save/create operations
            pollInterval = 75; // 75ms during save operations
          } else {
            // Regular polling for page processing
            pollInterval = 100; // 100ms for regular page updates
          }
          
          setTimeout(poll, pollInterval);
        }
      },
      error: function(xhr, status, error) {
        console.log('Progress polling error:', xhr.responseText, status, error); // Debug logging
        hideSplitProgress();
        $('#split-message').text('Error: Lost connection to server');
      }
    });
  };
  
  poll();
}

// Validate inputs for split PDF tool
function validateSplitInputs() {
  let file = $('#split-input')[0].files[0];
  let fname = $('#split-filename').val();
  let outputFolder = $('#split-output-folder').val();
  let method = $('input[name="split-method"]:checked').val();
  
  let isValidFilename = validateFilename(fname);
  let isValidFolder = validateFolder(outputFolder);
  let canRun = file && isValidFilename && isValidFolder && state.splitTotalPages > 1;
  
  if (method === 'pages') {
    let maxPages = parseInt($('#split-max-pages').val());
    canRun = canRun && maxPages > 0;
  } else if (method === 'size') {
    let maxSize = parseFloat($('#split-max-size').val());
    canRun = canRun && maxSize > 0;
  }
  
  console.log('Validation:', {file: !!file, fname, method, isValidFilename, isValidFolder, splitTotalPages: state.splitTotalPages, canRun});
  
  $('#split-run').prop('disabled', !canRun);
}

// Initialize split cancel button handler
function initializeSplitCancel() {
  $('#split-cancel-btn').on('click', function() {
    if (state.currentSplitJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#progress-status').text('Cancellation requested...');
      
      $.ajax({
        url: `/api/cancel_split/${state.currentSplitJobId}`,
        type: 'POST',
        success: function(data) {
          console.log('Cancel request sent:', data);
          // Show faster feedback
          $('#progress-status').text('Cancelling operation, please wait...');
          // Progress polling will handle the actual cleanup and modal closing
        },
        error: function(xhr, status, error) {
          console.log('Cancel request error:', error);
          // Re-enable button if cancel request failed
          $('#split-cancel-btn').prop('disabled', false).text('Cancel');
          $('#progress-status').text('Cancel request failed');
        }
      });
    }
  });
}

// Initialize split PDF functionality
export function initializeSplit() {
  // Store validation function globally for browser tracking
  window.validateSplitInputs = validateSplitInputs;
  
  // Split method radio button handling
  $('input[name="split-method"]').on('change', function() {
    let method = $(this).val();
    if (method === 'pages') {
      $('#split-pages-row').show();
      $('#split-size-row').hide();
      $('#split-max-size').val('').prop('disabled', true);
      if ($('#split-input')[0].files[0]) {
        $('#split-max-pages').prop('disabled', false);
        // Set default pages if we have page count
        if (state.splitTotalPages > 0) {
          let defaultPages = 20;
          if (state.splitTotalPages < 40) {
            defaultPages = Math.max(1, Math.floor(state.splitTotalPages / 2));
          }
          $('#split-max-pages').val(defaultPages);
        }
      }
    } else if (method === 'size') {
      $('#split-pages-row').hide();
      $('#split-size-row').show();
      $('#split-max-pages').val('').prop('disabled', true);
      if ($('#split-input')[0].files[0]) {
        $('#split-max-size').prop('disabled', false).val('30'); // Default 30MB
      }
    }
    validateSplitInputs();
  });

  $('#split-input').on('change', function() {
    let file = this.files[0];
    if (file) {
      $('#split-filename').prop('disabled', false);
      // Default zip filename: split_<original>.zip
      let base = file.name.replace(/\.pdf$/i, '');
      $('#split-filename').val('split_' + base);
      
      // Reset splitTotalPages and trigger initial validation
      setState('splitTotalPages', 0);
      validateSplitInputs(); // This will disable the button initially
      
      // Enable the appropriate input based on selected method
      let method = $('input[name="split-method"]:checked').val();
      if (method === 'pages') {
        $('#split-max-pages').prop('disabled', false);
      } else if (method === 'size') {
        $('#split-max-size').prop('disabled', false);
      }
      
      // Get page count using PDF.js
      let reader = new FileReader();
      reader.onload = function(ev) {
        if (window.pdfjsLib) {
          const loadingTask = pdfjsLib.getDocument({data: ev.target.result});
          loadingTask.promise.then(pdf => {
            const pageCount = pdf.numPages;
            setState('splitTotalPages', pageCount);
            console.log('PDF page count from PDF.js:', pageCount);
            
            // Set default values based on selected method and page count
            let method = $('input[name="split-method"]:checked').val();
            if (method === 'pages') {
              let defaultPages = 20;
              if (pageCount < 40) {
                defaultPages = Math.max(1, Math.floor(pageCount / 2));
              }
              $('#split-max-pages').val(defaultPages);
            } else if (method === 'size') {
              $('#split-max-size').val('30'); // Default 30MB
            }
            
            // Show warning if only 1 page
            if (pageCount === 1) {
              $('#split-warning').text('This PDF has only 1 page and cannot be split.').show();
            } else {
              $('#split-warning').hide();
            }
            
            // Re-validate with actual page count
            validateSplitInputs();
          }).catch(error => {
            console.error('PDF.js failed to load PDF:', error);
            setState('splitTotalPages', 0);
            $('#split-warning').text('Could not determine page count. Please check if this is a valid PDF.').show();
            validateSplitInputs();
          });
        } else {
          console.error('PDF.js library not loaded');
          setState('splitTotalPages', 0);
          $('#split-warning').text('PDF processing library not available.').show();
        }
      };
      reader.readAsArrayBuffer(file);
    } else {
      $('#split-filename').val('');
      $('#split-filename').prop('disabled', true);
      $('#split-max-pages').val('').prop('disabled', true);
      $('#split-max-size').val('').prop('disabled', true);
      $('#split-run').prop('disabled', true);
      $('#split-warning').hide();
      setState('splitTotalPages', 0); // Reset page count
    }
  });
  
  $('#split-filename, #split-max-pages, #split-max-size, #split-output-folder').on('input', validateSplitInputs);

  $('#split-run').on('click', function() {
    let file = $('#split-input')[0].files[0];
    let fname = $('#split-filename').val();
    let method = $('input[name="split-method"]:checked').val();
    
    // Fallback if method is undefined
    if (!method) {
      if ($('#split-method-pages').prop('checked')) {
        method = 'pages';
      } else if ($('#split-method-size').prop('checked')) {
        method = 'size';
      }
    }
    
    console.log('Split run clicked:', {file: file ? file.name : 'none', fname, method, splitTotalPages: state.splitTotalPages});
    
    if (!file || !fname || state.splitTotalPages === 1) {
      console.log('Validation failed:', {file: !!file, fname: !!fname, splitTotalPages: state.splitTotalPages});
      return;
    }
    
    let outputFolder = $('#split-output-folder').val();
    
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_zip', fname);
    formData.append('output_folder', outputFolder);
    
    if (method === 'pages') {
      let maxPages = parseInt($('#split-max-pages').val());
      if (!(maxPages > 0)) {
        console.log('Invalid max pages:', maxPages);
        return;
      }
      formData.append('max_pages_per_chunk', maxPages);
    } else if (method === 'size') {
      let maxSize = parseFloat($('#split-max-size').val());
      if (!(maxSize > 0)) {
        console.log('Invalid max size:', maxSize);
        return;
      }
      formData.append('max_size_mb', maxSize);
    } else {
      console.log('No valid method selected:', method);
      return;
    }
    
    showSplitProgress();
    
    $.ajax({
      url: '/api/split_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        console.log('Split success response:', data);
        
        if (data.job_id) {
          // Start polling for progress
          pollSplitProgress(data.job_id);
        } else if (data.success && data.zipfile) {
          hideSplitProgress();
          closeModal('split-modal');
          alert('PDF split successfully!\nSaved to: ' + data.zipfile);
        } else {
          hideSplitProgress();
          $('#split-message').text('Error: ' + (data.error || 'Unknown error'));
        }
      },
      error: function(xhr) {
        hideSplitProgress();
        $('#split-message').text('Error: ' + xhr.responseText);
      }
    });
  });

  // Initialize cancel button functionality
  initializeSplitCancel();
}