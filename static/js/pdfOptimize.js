// pdfOptimize.js - PDF optimization functionality
import { state, setState, closeModal } from './state.js';
import { openModal, validateFilename, validateFolder } from './utils.js';

// Validate inputs for optimize PDF tool
function validateOptimizeInputs() {
    let file = $('#optimize-input')[0].files[0];
    let fname = $('#optimize-filename').val();
    let outputFolder = $('#optimize-output-folder').val();
    
    let isValidFilename = validateFilename(fname);
    let isValidFolder = validateFolder(outputFolder);
    let canRun = file && isValidFilename && isValidFolder;
    
    $('#optimize-run').prop('disabled', !canRun);
}

// Poll optimize progress
function pollOptimizeProgress() {
  const poll = () => {
    if (!state.currentOptimizeJobId || state.currentOptimizeJobId === 'pending') {
      return;
    }
    
    $.ajax({
      url: `/api/optimize_progress/${state.currentOptimizeJobId}`,
      type: 'GET',
      success: function(data) {
        console.log('Optimize progress:', data);
        if (data.status === 'complete') {
          // User shouldn't be able to press cancel here
          $('#optimize-cancel-btn').prop('disabled', true).text('Cancel');
          // Show completion message briefly
          updateOptimizeProgress('PDF optimization completed!');
          setState('currentOptimizeJobId', null);
          setState('currentOptimizeRequest', null);
          
          setTimeout(() => {
            closeModal('optimize-progress-modal');
            if (data.filename) {
              alert('PDF optimized successfully!\nSaved to: ' + data.filename);
            } else {
              alert('PDF optimized successfully!');
            }
          }, 1000);
          // Re-enable cancel button for future use
          $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
        } else if (data.status === 'cancelled') {
          setState('currentOptimizeJobId', null);
          setState('currentOptimizeRequest', null);
          closeModal('optimize-progress-modal');
          // Don't show alert for user-initiated cancellation
          // Re-enable cancel button for future use
          $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
          
        } else if (data.status === 'error') {
          setState('currentOptimizeJobId', null);
          setState('currentOptimizeRequest', null);
          closeModal('optimize-progress-modal');
          alert('Error: ' + (data.message || 'Optimization failed'));
          
          // Re-enable cancel button for future use
          $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
        } else {
          // Still processing
          updateOptimizeProgress(data.message);
          setTimeout(poll, 1000);
        }
      },
      error: function(xhr, status, error) {
        console.error('Error polling optimize progress:', error);
        // Re-enable cancel button and clear job ID and request on error
        $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
        setState('currentOptimizeJobId', null);
        setState('currentOptimizeRequest', null);
        closeModal('optimize-progress-modal');
        alert('Error: Lost connection to server');
      }
    });
  };
  
  poll();
}

// Update optimize progress display
function updateOptimizeProgress(message) {
  console.log('Updating optimize progress:', {message});
  $('#optimize-progress-status').text(message || 'Processing...');
}

// Initialize optimize cancel button handler
function initializeOptimizeCancel() {
  $('#optimize-cancel-btn').on('click', function() {
    if (state.currentOptimizeJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#optimize-progress-status').text('Cancellation requested...');
      
      // If job is still pending (during startup), abort request and close modal immediately
      if (state.currentOptimizeJobId === 'pending') {
        // Abort the ongoing request if it exists
        if (state.currentOptimizeRequest) {
          state.currentOptimizeRequest.abort();
          setState('currentOptimizeRequest', null);
        }
        closeModal('optimize-progress-modal');
        setState('currentOptimizeJobId', null);
        return;
      }
      
      $.ajax({
        url: `/api/cancel_optimize/${state.currentOptimizeJobId}`,
        type: 'POST',
        success: function(data) {
          console.log('Optimize cancel request sent:', data);
          // Show faster feedback
          $('#optimize-progress-status').text('Cancelling operation, please wait...');
          // Progress polling will handle the actual cleanup and modal closing
        },
        error: function(xhr, status, error) {
          console.error('Error cancelling optimize:', error);
          // Re-enable cancel button on error
          $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
          $('#optimize-progress-status').text('Error cancelling operation');
        }
      });
    }
  });
}

// Initialize optimize PDF functionality
export function initializeOptimize() {
  // Store validation function globally for browser tracking
  window.validateOptimizeInputs = validateOptimizeInputs;
  
  $('#optimize-input').on('change', function() {
    let file = this.files[0];
    if (file) {
      let baseName = file.name.replace(/\.[^/.]+$/, "");
      $('#optimize-filename').val(baseName + '_optimized').prop('disabled', false);
      $('#optimize-output-folder').val(state.defaultOutputFolder);
      validateOptimizeInputs();
    } else {
      $('#optimize-filename').val('').prop('disabled', true);
      $('#optimize-output-folder').val('');
      validateOptimizeInputs();
    }
  });
  
  $('#optimize-filename').on('input', validateOptimizeInputs);
  $('#optimize-output-folder').on('input', validateOptimizeInputs);
  
  $('#optimize-run').on('click', function() {
    let file = $('#optimize-input')[0].files[0];
    let fname = $('#optimize-filename').val();
    let outputFolder = $('#optimize-output-folder').val();
    let aggressive = $('#optimize-aggressive').is(':checked');
    
    // Clear any previous error messages
    $('#optimize-message').text('');
    
    if (!file || !fname) {
      $('#optimize-message').text('Please fill in all required fields.');
      return;
    }

    console.log('Optimize run clicked:', {file: file.name, fname, outputFolder, aggressive});

    // Close the optimize modal and show progress modal
    closeModal('optimize-modal');
    openModal('optimize-progress-modal');
    
    // Reset progress display and ensure cancel button is enabled
    $('#optimize-progress-status').text('Starting PDF optimization...');
    $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
    
    // Set a temporary job ID so cancel button works during startup
    setState('currentOptimizeJobId', 'pending');

    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('aggressive', aggressive);
    
    let optimizeRequest = $.ajax({
      url: '/api/optimize_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        // Check if we were cancelled during startup
        if (state.currentOptimizeJobId === null) {
          console.log('Optimize was cancelled during startup, ignoring response');
          // If we got a job ID back but were cancelled, cancel it immediately
          if (data.success && data.job_id) {
            $.ajax({
              url: `/api/cancel_optimize/${data.job_id}`,
              type: 'POST',
              success: function() {
                console.log('Successfully cancelled optimize job during startup');
              }
            });
          }
          return;
        }
        
        if (data.success && data.job_id) {
          setState('currentOptimizeJobId', data.job_id);
          setState('currentOptimizeRequest', null);
          pollOptimizeProgress();
        } else {
          $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
          setState('currentOptimizeJobId', null);
          setState('currentOptimizeRequest', null);
          closeModal('optimize-progress-modal');
          if (data.error) {
            alert('Error: ' + data.error);
          } else {
            alert('An unknown error occurred.');
          }
        }
      },
      error: function(xhr, status, error) {
        $('#optimize-cancel-btn').prop('disabled', false).text('Cancel');
        setState('currentOptimizeJobId', null);
        setState('currentOptimizeRequest', null);
        closeModal('optimize-progress-modal');
        if (status === 'abort') {
          console.log('Optimize request was aborted');
        } else {
          alert('Error: ' + (xhr.responseText || error));
        }
      }
    });
    
    setState('currentOptimizeRequest', optimizeRequest);
  });
  
  // Initialize cancel button
  initializeOptimizeCancel();
}