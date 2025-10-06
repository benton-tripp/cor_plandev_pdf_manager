// pdfCombine.js - PDF combining functionality
import { state, setState, closeModal } from './state.js';
import { openModal, validateFilename, validateFolder } from './utils.js';

// Validate inputs for combine PDFs tool
function validateCombineInputs() {
    let files = $('#combine-input')[0].files;
    let fname = $('#combine-filename').val();
    let outputFolder = $('#combine-output-folder').val();
    
    let isValidFilename = validateFilename(fname);
    let isValidFolder = validateFolder(outputFolder);
    let canRun = files.length > 0 && isValidFilename && isValidFolder;
    
    $('#combine-run').prop('disabled', !canRun);
}

// Poll combine progress
function pollCombineProgress() {
  const poll = () => {
    if (!state.currentCombineJobId || state.currentCombineJobId === 'pending') {
      return;
    }
    
    $.ajax({
      url: `/api/combine_progress/${state.currentCombineJobId}`,
      type: 'GET',
      success: function(data) {
        console.log('Combine progress:', data);
        if (data.status === 'complete') {
          // User shouldn't be able to press cancel here
          $('#combine-cancel-btn').prop('disabled', true).text('Cancel');
          // Show completion message briefly
          updateCombineProgress('PDF combination completed!');
          setState('currentCombineJobId', null);
          setState('currentCombineRequest', null);
          
          setTimeout(() => {
            closeModal('combine-progress-modal');
            if (data.filename) {
              alert('PDFs combined successfully!\nSaved to: ' + data.filename);
            } else {
              alert('PDFs combined successfully!');
            }
          }, 1000);
          // Re-enable cancel button for future use
          $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
        } else if (data.status === 'cancelled') {
          setState('currentCombineJobId', null);
          setState('currentCombineRequest', null);
          closeModal('combine-progress-modal');
          // Don't show alert for user-initiated cancellation
          // Re-enable cancel button for future use
          $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
          
        } else if (data.status === 'error') {
          setState('currentCombineJobId', null);
          setState('currentCombineRequest', null);
          closeModal('combine-progress-modal');
          alert('Error: ' + (data.message || 'Combination failed'));
          
          // Re-enable cancel button for future use
          $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
        } else {
          // Still processing
          updateCombineProgress(data.message);
          setTimeout(poll, 1000);
        }
      },
      error: function(xhr, status, error) {
        console.error('Error polling combine progress:', error);
        // Re-enable cancel button and clear job ID and request on error
        $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
        setState('currentCombineJobId', null);
        setState('currentCombineRequest', null);
        closeModal('combine-progress-modal');
        alert('Error: Lost connection to server');
      }
    });
  };
  
  poll();
}

// Update combine progress display
function updateCombineProgress(message) {
  console.log('Updating combine progress:', {message});
  $('#combine-progress-status').text(message || 'Processing...');
}

// Initialize combine cancel button handler
function initializeCombineCancel() {
  $('#combine-cancel-btn').on('click', function() {
    if (state.currentCombineJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#combine-progress-status').text('Cancellation requested...');
      
      // If job is still pending (during startup), abort request and close modal immediately
      if (state.currentCombineJobId === 'pending') {
        // Abort the ongoing request if it exists
        if (state.currentCombineRequest) {
          state.currentCombineRequest.abort();
          setState('currentCombineRequest', null);
        }
        closeModal('combine-progress-modal');
        setState('currentCombineJobId', null);
        return;
      }
      
      $.ajax({
        url: `/api/cancel_combine/${state.currentCombineJobId}`,
        type: 'POST',
        success: function(data) {
          console.log('Combine cancel request sent:', data);
          // Show faster feedback
          $('#combine-progress-status').text('Cancelling operation, please wait...');
          // Progress polling will handle the actual cleanup and modal closing
        },
        error: function(xhr, status, error) {
          console.error('Error cancelling combine:', error);
          // Re-enable cancel button on error
          $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
          $('#combine-progress-status').text('Error cancelling operation');
        }
      });
    }
  });
}

// Initialize combine PDF functionality
export function initializeCombine() {
  // Store validation function globally for browser tracking
  window.validateCombineInputs = validateCombineInputs;
  
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
    
    // Clear any previous error messages
    $('#combine-message').text('');
    
    if (!(files.length > 0 && fname)) {
      $('#combine-message').text('Please fill in all required fields.');
      return;
    }

    console.log('Combine run clicked:', {fileCount: files.length, fname, outputFolder, optimize});
    console.log('Files array:', files);
    console.log('Files details:');
    for (let i = 0; i < files.length; i++) {
      console.log(`File ${i}:`, files[i].name, 'type:', files[i].type, 'size:', files[i].size);
    }

    // Create FormData BEFORE closing modal to preserve file references
    let formData = new FormData();
    console.log('About to append files, count:', files.length);
    for (let i = 0; i < files.length; i++) {
      console.log('Appending file:', files[i].name, 'size:', files[i].size);
      formData.append('pdf_list', files[i]);
    }
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('optimize', optimize ? 'true' : 'false');

    // Close the combine modal and show progress modal
    closeModal('combine-modal');
    openModal('combine-progress-modal');
    
    // Reset progress display and ensure cancel button is enabled
    $('#combine-progress-status').text('Starting PDF combination...');
    $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
    
    // Set a temporary job ID so cancel button works during startup
    setState('currentCombineJobId', 'pending');

    // Debug FormData contents
    console.log('FormData contents:');
    for (let pair of formData.entries()) {
      console.log(pair[0] + ':', pair[1]);
    }
    
    let combineRequest = $.ajax({
      url: '/api/combine_pdfs',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        // Check if we were cancelled during startup
        if (state.currentCombineJobId === null) {
          console.log('Combine was cancelled during startup, ignoring response');
          // If we got a job ID back but were cancelled, cancel it immediately
          if (data.success && data.job_id) {
            $.ajax({
              url: `/api/cancel_combine/${data.job_id}`,
              type: 'POST',
              success: function() {
                console.log('Successfully cancelled combine job during startup');
              }
            });
          }
          return;
        }
        
        if (data.success && data.job_id) {
          setState('currentCombineJobId', data.job_id);
          setState('currentCombineRequest', null);
          pollCombineProgress();
        } else {
          $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
          setState('currentCombineJobId', null);
          setState('currentCombineRequest', null);
          closeModal('combine-progress-modal');
          if (data.error) {
            alert('Error: ' + data.error);
          } else {
            alert('An unknown error occurred.');
          }
        }
      },
      error: function(xhr, status, error) {
        $('#combine-cancel-btn').prop('disabled', false).text('Cancel');
        setState('currentCombineJobId', null);
        setState('currentCombineRequest', null);
        closeModal('combine-progress-modal');
        if (status === 'abort') {
          console.log('Combine request was aborted');
        } else {
          alert('Error: ' + (xhr.responseText || error));
        }
      }
    });
    
    setState('currentCombineRequest', combineRequest);
  });
  
  // Initialize cancel button
  initializeCombineCancel();
}