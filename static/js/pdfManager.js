// pdfManager.js
import {state} from './state.js';

let defaultOutputFolder = '';

// Load default output folder on page load
$(document).ready(function() {
  $.get('/api/get_default_output_folder')
    .done(function(data) {
      defaultOutputFolder = data.folder;
      // Set default values in all output folder inputs
      $('#compress-output-folder').val(defaultOutputFolder);
      $('#split-output-folder').val(defaultOutputFolder);
      $('#combine-output-folder').val(defaultOutputFolder);
      $('#flatten-output-folder').val(defaultOutputFolder);
      $('#optimize-output-folder').val(defaultOutputFolder);
      $('#extract-output-folder').val(defaultOutputFolder);
    })
    .fail(function() {
      console.warn('Could not load default output folder');
    });
});

// open the modal with the given id
function openModal(id) {
  $('#' + id).fadeIn(200);
}

// Close modal and reset message
function closeModal(id) {
  $('#' + id).fadeOut(200);
  $('#' + id + ' .tool-modal-message').text('');
  // Clear inputs but preserve radio button states and reset to defaults
  if (id === 'split-modal') {
    $('#split-input').val('');
    $('#split-filename').val('').prop('disabled', true);
    $('#split-output-folder').val(defaultOutputFolder);
    $('#split-max-pages').val('').prop('disabled', true);
    $('#split-max-size').val('').prop('disabled', true);
    // Reset radio buttons to default (pages)
    $('#split-method-pages').prop('checked', true);
    $('#split-pages-row').show();
    $('#split-size-row').hide();
    $('#split-warning').hide();
    splitTotalPages = 0;
  } else if (id === 'compress-modal') {
    // Clear inputs and reset flatten checkbox for compress modal
    $('#compress-input').val('');
    $('#compress-filename').val('').prop('disabled', true);
    $('#compress-output-folder').val(defaultOutputFolder);
    $('#compress-optimize').prop('checked', false);
  } else if (id === 'combine-modal') {
    // Clear inputs and reset flatten checkbox for combine modal
    $('#combine-input').val('');
    $('#combine-filename').val('').prop('disabled', true);
    $('#combine-output-folder').val(defaultOutputFolder);
    $('#combine-optimize').prop('checked', false);
  } else if (id === 'flatten-modal') {
    // Clear inputs for flatten modal
    $('#flatten-input').val('');
    $('#flatten-filename').val('').prop('disabled', true);
    $('#flatten-output-folder').val(defaultOutputFolder);
  } else if (id === 'optimize-modal') {
    // Clear inputs for optimize modal
    $('#optimize-input').val('');
    $('#optimize-filename').val('').prop('disabled', true);
    $('#optimize-output-folder').val(defaultOutputFolder);
    $('#optimize-aggressive').prop('checked', false);
  } else if (id === 'extract-modal') {
    // Clear inputs for extract modal
    $('#extract-input').val('');
    $('#extract-filename').val('').prop('disabled', true);
    $('#extract-output-folder').val(defaultOutputFolder);
    $('#extract-pages').val('');
  } else {
    // For other modals, clear all inputs as before
    $('#' + id + ' input').val('');
  }
  $('#' + id + ' .tool-modal-run').prop('disabled', true);
}

// Show spinner overlay
function showToolSpinner() {
  if ($('#tool-spinner-overlay').length) return;
  $('body').append('<div id="tool-spinner-overlay"><div class="tool-spinner"></div></div>');
}

// Hide spinner overlay
function hideToolSpinner() {
  $('#tool-spinner-overlay').remove();
}

// Show split progress modal
function showSplitProgress() {
  $('#split-progress-modal').fadeIn(200);
  $('#split-cancel-btn').prop('disabled', false).text('Cancel');
  updateSplitProgress(0, 0, 0, 0, 0, 'Initializing...');
}

// Hide split progress modal
function hideSplitProgress() {
  $('#split-progress-modal').fadeOut(200);
  currentSplitJobId = null;
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
  currentSplitJobId = jobId; // Store job ID for cancellation
  
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

// Track total pages for split validation
let splitTotalPages = 0;

// Track current split job ID for cancellation
let currentSplitJobId = null;

// Track current flatten job ID for cancellation
let currentFlattenJobId = null;

// Track flatten progress
function trackFlattenProgress(jobId) {
  currentFlattenJobId = jobId; // Store job ID for cancellation
  
  let lastState = {
    currentPage: 0,
    message: '',
    percentage: 0
  };
  
  const poll = () => {
    $.ajax({
      url: `/api/flatten_progress/${jobId}`,
      type: 'GET',
      success: function(data) {
        console.log('Flatten progress data received:', data); // Debug logging
        
        if (data.error) {
          closeModal('flatten-progress-modal');
          alert('Error: ' + data.error);
          return;
        }
        
        // Update the UI with latest data
        updateFlattenProgress(
          data.current_page || 0,
          data.total_pages || 0,
          data.percentage || 0,
          data.message || 'Processing...'
        );
        
        // Detect important state changes
        const currentMessage = data.message || 'Processing...';
        const isImportantStateChange = (
          (currentMessage.includes('Saving') && !lastState.message.includes('Saving')) ||
          (currentMessage.includes('Complete') && !lastState.message.includes('Complete')) ||
          (Math.abs((data.percentage || 0) - lastState.percentage) > 5)
        );
        
        // Update our state tracking
        lastState = {
          currentPage: data.current_page || 0,
          message: currentMessage,
          percentage: data.percentage || 0
        };
        
        if (data.status === 'complete') {
          setTimeout(() => {
            closeModal('flatten-progress-modal');
            if (data.filename) {
              alert('PDF flattened successfully!\nSaved to: ' + data.filename);
            }
          }, 1000); // Show 100% for a moment before closing
        } else if (data.status === 'cancelled') {
          closeModal('flatten-progress-modal');
          alert('PDF flatten was cancelled.');
        } else if (data.status === 'error') {
          closeModal('flatten-progress-modal');
          alert('Error: ' + (data.message || 'Flatten failed'));
        } else {
          // Adaptive polling
          let pollInterval;
          if (currentMessage.includes('Cancelling') || currentMessage.includes('Cancellation')) {
            pollInterval = 25; // 25ms for cancellation feedback
          } else if (isImportantStateChange) {
            pollInterval = 50; // 50ms for important state changes
          } else if (currentMessage.includes('Saving')) {
            pollInterval = 75; // 75ms during save operations
          } else {
            pollInterval = 100; // 100ms for regular updates
          }
          
          setTimeout(poll, pollInterval);
        }
      },
      error: function(xhr, status, error) {
        console.log('Flatten progress polling error:', xhr.responseText, status, error);
        closeModal('flatten-progress-modal');
        alert('Error: Lost connection to server');
      }
    });
  };
  
  poll();
}

// Update flatten progress display
function updateFlattenProgress(currentPage, totalPages, percentage, message) {
  console.log('Updating flatten progress:', {currentPage, totalPages, percentage, message});
  
  // Update progress bar
  $('#flatten-progress-fill').css('width', percentage + '%');
  $('#flatten-progress-percentage').text(percentage + '%');
  $('#flatten-progress-status').text(message || 'Processing...');
}

// Validate inputs for compress PDF tool
function validateCompressInputs() {
  let file = $('#compress-input')[0].files[0];
  let fname = $('#compress-filename').val();
  let outputFolder = $('#compress-output-folder').val();
  
  // More permissive filename validation - allow most common filename characters
  let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
  let isValidFolder = outputFolder && outputFolder.trim().length > 0;
  let canRun = file && isValidFilename && isValidFolder;
  
  $('#compress-run').prop('disabled', !canRun);
}

// Validate inputs for split PDF tool
function validateSplitInputs() {
  let file = $('#split-input')[0].files[0];
  let fname = $('#split-filename').val();
  let outputFolder = $('#split-output-folder').val();
  let method = $('input[name="split-method"]:checked').val();
  
  let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
  let isValidFolder = outputFolder && outputFolder.trim().length > 0;
  let canRun = file && isValidFilename && isValidFolder && splitTotalPages > 1;
  
  if (method === 'pages') {
    let maxPages = parseInt($('#split-max-pages').val());
    canRun = canRun && maxPages > 0;
  } else if (method === 'size') {
    let maxSize = parseFloat($('#split-max-size').val());
    canRun = canRun && maxSize > 0;
  }
  
  console.log('Validation:', {file: !!file, fname, method, isValidFilename, isValidFolder, splitTotalPages, canRun});
  
  $('#split-run').prop('disabled', !canRun);
}

// Validate inputs for combine PDFs tool
function validateCombineInputs() {
    let files = $('#combine-input')[0].files;
    let fname = $('#combine-filename').val();
    let outputFolder = $('#combine-output-folder').val();
    
    let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
    let isValidFolder = outputFolder && outputFolder.trim().length > 0;
    let canRun = files.length > 0 && isValidFilename && isValidFolder;
    
    $('#combine-run').prop('disabled', !canRun);
}

// Validate inputs for flatten PDF tool
function validateFlattenInputs() {
    let file = $('#flatten-input')[0].files[0];
    let fname = $('#flatten-filename').val();
    let outputFolder = $('#flatten-output-folder').val();
    
    let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
    let isValidFolder = outputFolder && outputFolder.trim().length > 0;
    let canRun = file && isValidFilename && isValidFolder;
    
    $('#flatten-run').prop('disabled', !canRun);
}

// Validate inputs for optimize PDF tool
function validateOptimizeInputs() {
    let file = $('#optimize-input')[0].files[0];
    let fname = $('#optimize-filename').val();
    let outputFolder = $('#optimize-output-folder').val();
    
    let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
    let isValidFolder = outputFolder && outputFolder.trim().length > 0;
    let canRun = file && isValidFilename && isValidFolder;
    
    $('#optimize-run').prop('disabled', !canRun);
}

// Validate inputs for extract pages tool
function validateExtractInputs() {
    let file = $('#extract-input')[0].files[0];
    let fname = $('#extract-filename').val();
    let outputFolder = $('#extract-output-folder').val();
    let pages = $('#extract-pages').val();
    
    let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
    let isValidFolder = outputFolder && outputFolder.trim().length > 0;
    let isValidPages = pages && pages.trim().length > 0;
    let canRun = file && isValidFilename && isValidFolder && isValidPages;
    
    $('#extract-run').prop('disabled', !canRun);
}

// Compress, split, and combine PDF functions
export function compressSplitCombinePDFs(window, document) {
  // --- Modal open/close logic ---
  $('.tool-modal-cancel').on('click', function() {
    closeModal($(this).data('modal'));
  });

  // --- Split cancel button handler ---
  $('#split-cancel-btn').on('click', function() {
    if (currentSplitJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#progress-status').text('Cancellation requested...');
      
      $.ajax({
        url: `/api/cancel_split/${currentSplitJobId}`,
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

  // --- Flatten cancel button handler ---
  $('#flatten-cancel-btn').on('click', function() {
    if (currentFlattenJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#flatten-progress-status').text('Cancellation requested...');
      
      $.ajax({
        url: `/api/cancel_flatten/${currentFlattenJobId}`,
        type: 'POST',
        success: function(data) {
          console.log('Flatten cancel request sent:', data);
          // Show faster feedback
          $('#flatten-progress-status').text('Cancelling operation, please wait...');
          // Progress polling will handle the actual cleanup and modal closing
        },
        error: function(xhr, status, error) {
          console.log('Flatten cancel request error:', error);
          // Re-enable button if cancel request failed
          $('#flatten-cancel-btn').prop('disabled', false).text('Cancel');
          $('#flatten-progress-status').text('Cancel request failed');
        }
      });
    }
  });

  // --- Compress PDF ---
  $('#compress-input').on('change', function() {
    let file = this.files[0];
    if (file) {
      $('#compress-filename').prop('disabled', false);
      let base = file.name.replace(/\.pdf$/i, '');
      $('#compress-filename').val('compressed_' + base);
      // Trigger validation after setting the value
      validateCompressInputs();
    } else {
      $('#compress-filename').val('');
      $('#compress-filename').prop('disabled', true);
      validateCompressInputs();
    }
  });
  $('#compress-filename').on('input', validateCompressInputs);
  $('#compress-output-folder').on('input', validateCompressInputs);
  $('#compress-run').on('click', function() {
    let file = $('#compress-input')[0].files[0];
    let fname = $('#compress-filename').val();
    let outputFolder = $('#compress-output-folder').val();
    let optimize = $('#compress-optimize').is(':checked');
    if (!file || !fname) return;

    console.log('Compress run clicked:', {file: file.name, fname, outputFolder, optimize});

    showToolSpinner();
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('optimize', optimize ? 'true' : 'false');
    $.ajax({
      url: '/api/compress_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        hideToolSpinner();
        if (data.success && data.filename) {
          // Show success message with file location
          closeModal('compress-modal');
          alert('File compressed successfully!\nSaved to: ' + data.filename);
        } else if (!data.success && data.error) {
          $('#compress-message').text('Error: ' + data.error);
        } else {
          $('#compress-message').text('An unknown error occurred.');
        }
      },
      error: function(xhr) {
        hideToolSpinner();
        $('#compress-message').text('Error: ' + xhr.responseText);
      }
    });
  });

  // --- Split PDF ---
  // Split method radio button handling
  $('input[name="split-method"]').on('change', function() {
    let method = $(this).val();
    if (method === 'pages') {
      $('#split-pages-row').show();
      $('#split-size-row').hide();
      $('#split-max-size').val('').prop('disabled', true);
      if ($('#split-input')[0].files[0]) {
        $('#split-max-pages').prop('disabled', false);
      }
    } else if (method === 'size') {
      $('#split-pages-row').hide();
      $('#split-size-row').show();
      $('#split-max-pages').val('').prop('disabled', true);
      if ($('#split-input')[0].files[0]) {
        $('#split-max-size').val('30').prop('disabled', false); // Default 30MB
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
      splitTotalPages = 0;
      validateSplitInputs(); // This will disable the button initially
      
      // Enable the appropriate input based on selected method
      let method = $('input[name="split-method"]:checked').val();
      if (method === 'pages') {
        $('#split-max-pages').prop('disabled', false);
      } else if (method === 'size') {
        $('#split-max-size').prop('disabled', false);
        $('#split-max-size').val('30'); // Default 30MB
      }
      
      // Get page count using PDF.js
      let reader = new FileReader();
      reader.onload = function(ev) {
        if (window.pdfjsLib) {
          console.log('Loading PDF with PDF.js to get page count...');
          window.pdfjsLib.getDocument({data: ev.target.result}).promise.then(function(pdf) {
            splitTotalPages = pdf.numPages;
            console.log('PDF.js loaded successfully. Pages:', splitTotalPages);
            
            if (method === 'pages') {
              let def = 10;
              if (splitTotalPages < 20) def = Math.max(1, Math.floor(splitTotalPages / 2));
              $('#split-max-pages').val(def);
            }
            
            if (splitTotalPages === 1) {
              $('#split-warning').show().text('Warning: PDF has only 1 page. Cannot split.');
              $('#split-run').prop('disabled', true);
            } else {
              $('#split-warning').hide();
              validateSplitInputs(); // Re-validate after getting page count
            }
          }).catch(function(error) {
            console.error('PDF.js failed to load PDF:', error);
            $('#split-warning').show().text('Error: Could not read PDF file. Please try a different file.');
            splitTotalPages = 0;
            validateSplitInputs();
          });
        } else {
          console.error('PDF.js is not available! This should not happen.');
          $('#split-warning').show().text('Error: PDF reader not available. Please refresh the page.');
          splitTotalPages = 0;
          validateSplitInputs();
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
      splitTotalPages = 0; // Reset page count
    }
  });
  $('#split-filename, #split-max-pages, #split-max-size, #split-output-folder').on('input', validateSplitInputs);

  $('#split-run').on('click', function() {
    let file = $('#split-input')[0].files[0];
    let fname = $('#split-filename').val();
    let method = $('input[name="split-method"]:checked').val();
    
    // Fallback if method is undefined
    if (!method) {
      // console.log('Method undefined, checking radio buttons manually');
      if ($('#split-method-pages').prop('checked')) {
        method = 'pages';
      } else if ($('#split-method-size').prop('checked')) {
        method = 'size';
      }
    }
    
    console.log('Split run clicked:', {file: file ? file.name : 'none', fname, method, splitTotalPages});
    
    if (!file || !fname || splitTotalPages === 1) {
      console.log('Validation failed:', {file: !!file, fname: !!fname, splitTotalPages});
      return;
    }
    
    let outputFolder = $('#split-output-folder').val();
    
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_zip', fname);
    formData.append('output_folder', outputFolder);
    
    if (method === 'pages') {
      let maxPages = parseInt($('#split-max-pages').val());
      // console.log('Pages method:', maxPages);
      if (!(maxPages > 0)) {
        console.log('Invalid max pages:', maxPages);
        return;
      }
      formData.append('max_pages_per_chunk', maxPages);
    } else if (method === 'size') {
      let maxSize = parseFloat($('#split-max-size').val());
      // console.log('Size method:', maxSize);
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
          // Legacy response - direct download
          hideSplitProgress();
          closeModal('split-modal');
          window.location = '/download/' + encodeURIComponent(data.zipfile);
        } else if (!data.success && data.error) {
          hideSplitProgress();
          $('#split-message').text('Error: ' + data.error);
        } else {
          hideSplitProgress();
          $('#split-message').text('An unknown error occurred.');
        }
      },
      error: function(xhr) {
        hideSplitProgress();
        $('#split-message').text('Error: ' + xhr.responseText);
      }
    });
  });

  // --- Combine PDFs ---
  $('#combine-input').on('change', function() {
    let files = this.files;
    if (files.length > 0) {
      let base = files[0].name.replace(/\.pdf$/i, '');
      $('#combine-filename').val('combined_' + base);
      $('#combine-filename').prop('disabled', false);
    } else {
      $('#combine-filename').val('');
      $('#combine-filename').prop('disabled', true);
    }
    validateCombineInputs();
  });
  $('#combine-filename').on('input', validateCombineInputs);
  $('#combine-output-folder').on('input', validateCombineInputs);
  $('#combine-run').on('click', function() {
    let files = $('#combine-input')[0].files;
    let fname = $('#combine-filename').val();
    let outputFolder = $('#combine-output-folder').val();
    let optimize = $('#combine-optimize').is(':checked');
    if (!(files.length > 0 && fname)) return;

    console.log('Combine run clicked:', {fileCount: files.length, fname, outputFolder, optimize});

    showToolSpinner();
    let formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('pdf_list', files[i]);
    }
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('optimize', optimize ? 'true' : 'false');
    $.ajax({
      url: '/api/combine_pdfs',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        hideToolSpinner();
        if (data.success && data.filename) {
          // Show success message with file location
          closeModal('combine-modal');
          alert('PDFs combined successfully!\nSaved to: ' + data.filename);
        } else if (!data.success && data.error) {
          $('#combine-message').text('Error: ' + data.error);
        } else {
          $('#combine-message').text('An unknown error occurred.');
        }
      },
      error: function(xhr) {
        hideToolSpinner();
        $('#combine-message').text('Error: ' + xhr.responseText);
      }
    });
  });

  // --- Flatten PDF ---
  $('#flatten-input').on('change', function() {
    let file = this.files[0];
    if (file) {
      let baseName = file.name.replace(/\.pdf$/i, '');
      $('#flatten-filename').val('flattened_' + baseName).prop('disabled', false);
      validateFlattenInputs();
    } else {
      $('#flatten-filename').val('').prop('disabled', true);
      validateFlattenInputs();
    }
  });
  $('#flatten-filename').on('input', validateFlattenInputs);
  $('#flatten-output-folder').on('input', validateFlattenInputs);
  $('#flatten-run').on('click', function() {
    let file = $('#flatten-input')[0].files[0];
    let fname = $('#flatten-filename').val();
    let outputFolder = $('#flatten-output-folder').val();
    if (!file || !fname) return;

    console.log('Flatten run clicked:', {file: file.name, fname, outputFolder});

    // Close the flatten modal and show progress modal
    closeModal('flatten-modal');
    openModal('flatten-progress-modal');

    // Reset progress display
    $('#flatten-progress-fill').width('0%');
    $('#flatten-progress-percentage').text('0%');
    $('#flatten-progress-status').text('Initializing flatten process...');

    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    
    $.ajax({
      url: '/api/flatten_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        if (data.success && data.job_id) {
          // Start tracking progress
          trackFlattenProgress(data.job_id);
        } else {
          closeModal('flatten-progress-modal');
          alert('Error starting flatten: ' + (data.error || 'Unknown error'));
        }
      },
      error: function(xhr) {
        closeModal('flatten-progress-modal');
        alert('Error starting flatten: ' + xhr.responseText);
      }
    });
  });



  // Folder browsing functionality for desktop app
  // Use webview API for proper folder selection
  
  function selectFolder(inputId, validationFunction) {
    // Check if we're running in a webview (desktop app)
    if (window.pywebview && window.pywebview.api) {
      // Use webview folder selection (desktop app)
      window.pywebview.api.select_folder().then(function(folderPath) {
        if (folderPath) {
          $(inputId).val(folderPath);
          validationFunction();
        }
      }).catch(function(error) {
        console.log('Folder selection error:', error);
        // User cancelled - do nothing
      });
    } else {
      // Use Flask API for native folder selection (web app)
      $.ajax({
        url: '/api/select_folder',
        type: 'POST',
        success: function(data) {
          if (data.success && data.folder) {
            $(inputId).val(data.folder);
            validationFunction();
          } else {
            console.log('Folder selection failed:', data.error);
            // User cancelled - do nothing
          }
        },
        error: function(xhr, status, error) {
          console.log('Folder selection API error:', error);
          // API error - do nothing
        }
      });
    }
  }
  
  $('#compress-browse-folder').on('click', function() {
    selectFolder('#compress-output-folder', validateCompressInputs);
  });

  $('#split-browse-folder').on('click', function() {
    selectFolder('#split-output-folder', validateSplitInputs);
  });

  $('#combine-browse-folder').on('click', function() {
    selectFolder('#combine-output-folder', validateCombineInputs);
  });

  $('#flatten-browse-folder').on('click', function() {
    selectFolder('#flatten-output-folder', validateFlattenInputs);
  });

  // --- Optimize PDF ---
  $('#optimize-input').on('change', function() {
    let file = this.files[0];
    if (file) {
      let baseName = file.name.replace(/\.[^/.]+$/, "");
      $('#optimize-filename').val(baseName + '_optimized').prop('disabled', false);
      $('#optimize-output-folder').val(defaultOutputFolder);
      validateOptimizeInputs();
    } else {
      $('#optimize-filename').val('').prop('disabled', true);
      $('#optimize-output-folder').val('');
      validateOptimizeInputs();
    }
  });
  $('#optimize-filename').on('input', validateOptimizeInputs);
  $('#optimize-output-folder').on('input', validateOptimizeInputs);
  $('#optimize-browse-folder').on('click', function() {
    selectFolder('#optimize-output-folder', validateOptimizeInputs);
  });
  $('#optimize-run').on('click', function() {
    let file = $('#optimize-input')[0].files[0];
    let fname = $('#optimize-filename').val();
    let outputFolder = $('#optimize-output-folder').val();
    let aggressive = $('#optimize-aggressive').is(':checked');
    if (!file || !fname) return;

    console.log('Optimize run clicked:', {file: file.name, fname, outputFolder, aggressive});

    showToolSpinner();
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('aggressive', aggressive);
    $.ajax({
      url: '/api/optimize_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        hideToolSpinner();
        if (data.success && data.filename) {
          closeModal('optimize-modal');
          alert('PDF optimized successfully!\nSaved to: ' + data.filename);
        } else if (!data.success && data.error) {
          $('#optimize-message').text('Error: ' + data.error);
        } else {
          $('#optimize-message').text('An unknown error occurred.');
        }
      },
      error: function(xhr) {
        hideToolSpinner();
        $('#optimize-message').text('Error: ' + xhr.responseText);
      }
    });
  });

  // --- Extract Pages ---
  $('#extract-input').on('change', function() {
    let file = this.files[0];
    if (file) {
      let baseName = file.name.replace(/\.[^/.]+$/, "");
      $('#extract-filename').val(baseName + '_extracted').prop('disabled', false);
      $('#extract-output-folder').val(defaultOutputFolder);
      validateExtractInputs();
    } else {
      $('#extract-filename').val('').prop('disabled', true);
      $('#extract-output-folder').val('');
      $('#extract-pages').val('');
      validateExtractInputs();
    }
  });
  $('#extract-filename, #extract-pages').on('input', validateExtractInputs);
  $('#extract-output-folder').on('input', validateExtractInputs);
  $('#extract-browse-folder').on('click', function() {
    selectFolder('#extract-output-folder', validateExtractInputs);
  });
  $('#extract-run').on('click', function() {
    let file = $('#extract-input')[0].files[0];
    let fname = $('#extract-filename').val();
    let outputFolder = $('#extract-output-folder').val();
    let pages = $('#extract-pages').val();
    if (!file || !fname || !pages) return;

    console.log('Extract run clicked:', {file: file.name, fname, outputFolder, pages});

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

  // Expose openModal globally for navbar links
  window.openModal = openModal;
}

// Export the main initialization function that includes all PDF tools
export function initializePDFTools(window, document) {
  compressSplitCombinePDFs(window, document);
}

