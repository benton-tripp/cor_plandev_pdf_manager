// pdfCompress.js - PDF compression functionality
import { state, setState, closeModal } from './state.js';
import { openModal, validateFilename, validateFolder } from './utils.js';

// Validate inputs for compress PDF tool
function validateCompressInputs() {
  let file = $('#compress-input')[0].files[0];
  let fname = $('#compress-filename').val();
  let outputFolder = $('#compress-output-folder').val();
  
  let isValidFilename = validateFilename(fname);
  let isValidFolder = validateFolder(outputFolder);
  let canRun = file && isValidFilename && isValidFolder;
  
  $('#compress-run').prop('disabled', !canRun);
}

// Poll compress progress
function pollCompressProgress() {
  const poll = () => {
    if (!state.currentCompressJobId || state.currentCompressJobId === 'pending') {
      return;
    }
    
    $.ajax({
      url: `/api/compress_progress/${state.currentCompressJobId}`,
      type: 'GET',
      success: function(data) {
        console.log('Compress progress:', data);
        if (data.status in ['complete', 'cancelled', 'error']) {
          // User shouldn't be able to press cancel here
          $('#compress-cancel-btn').prop('disabled', true).text('Cancel');
        }
        if (data.status === 'complete') {
          // Show completion message briefly
          updateCompressProgress('PDF compression completed!');
          resetCompressState();
          
          setTimeout(() => {
            closeModal('compress-progress-modal');
            if (data.filename) {
              alert('PDF compressed successfully!\nSaved to: ' + data.filename);
            } else {
              alert('PDF compressed successfully!');
            }
          }, 1000);
          
        } else if (data.status === 'cancelled') {
          resetCompressState();
          closeModal('compress-progress-modal');
          // Don't show alert for user-initiated cancellation
          
        } else if (data.status === 'error') {
          resetCompressState();
          closeModal('compress-progress-modal');
          alert('Error: ' + (data.message || 'Compression failed'));
          
        } else {
          // Still processing
          updateCompressProgress(data.message);
          setTimeout(poll, 1000);
        }
      },
      error: function(xhr, status, error) {
        console.error('Error polling compress progress:', error);
        resetCompressState();
        closeModal('compress-progress-modal');
        alert('Error: Lost connection to server');
      }
    });
  };
  
  poll();
}

// Update compress progress display
function updateCompressProgress(message) {
  console.log('Updating compress progress:', {message});
  console.log('Setting UI text to:', message || 'Processing...');
  $('#compress-progress-status').text(message || 'Processing...');
}

// Reset compress state completely
function resetCompressState() {
  console.log('Resetting compress state');
  setState('currentCompressJobId', null);
  setState('currentCompressRequest', null);
  $('#compress-cancel-btn').prop('disabled', false).text('Cancel');
}

// Initialize compress cancel button handler
function initializeCompressCancel() {
  $('#compress-cancel-btn').on('click', function() {
    if (state.currentCompressJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#compress-progress-status').text('Cancellation requested...');
      
      // If job is still pending (during startup), abort request and close modal immediately
      if (state.currentCompressJobId === 'pending') {
        // Set state to null first to signal cancellation to the success handler
        setState('currentCompressJobId', null);
        
        // Abort the ongoing request if it exists
        if (state.currentCompressRequest) {
          state.currentCompressRequest.abort();
          setState('currentCompressRequest', null);
        }
        closeModal('compress-progress-modal');
        return;
      }
      
      $.ajax({
        url: `/api/cancel_compress/${state.currentCompressJobId}`,
        type: 'POST',
        success: function(data) {
          console.log('Compress cancel request sent:', data);
          // Show faster feedback
          $('#compress-progress-status').text('Cancelling operation, please wait...');
          // Progress polling will handle the actual cleanup and modal closing
        },
        error: function(xhr, status, error) {
          console.error('Error cancelling compress:', error);
          // Re-enable cancel button on error
          $('#compress-cancel-btn').prop('disabled', false).text('Cancel');
          $('#compress-progress-status').text('Error cancelling operation');
          
          // Reset state after a delay to allow user to see the error
          setTimeout(() => {
            resetCompressState();
            closeModal('compress-progress-modal');
          }, 1000);
        }
      });
    }
  });
}

// Initialize compress PDF functionality
export function initializeCompress() {
  // Reset compress state on initialization
  resetCompressState();
  
  // Store validation function globally for browser tracking
  window.validateCompressInputs = validateCompressInputs;
  
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
    // Prevent multiple simultaneous operations
    if (state.currentCompressJobId && state.currentCompressJobId !== null) {
      console.log('Compress operation already in progress, ignoring click');
      return;
    }
    
    let file = $('#compress-input')[0].files[0];
    let fname = $('#compress-filename').val();
    let outputFolder = $('#compress-output-folder').val();
    let optimize = $('#compress-optimize').is(':checked');
    
    // Clear any previous error messages
    $('#compress-message').text('');
    
    if (!file || !fname) {
      $('#compress-message').text('Please fill in all required fields.');
      return;
    }

    console.log('Compress run clicked:', {file: file.name, fname, outputFolder, optimize});

    // Close the compress modal and show progress modal
    closeModal('compress-modal');
    openModal('compress-progress-modal');
    
    // Reset progress display and ensure cancel button is enabled
    $('#compress-progress-status').text('Starting PDF compression...');
    $('#compress-cancel-btn').prop('disabled', false).text('Cancel');
    
    // Set a temporary job ID so cancel button works during startup
    setState('currentCompressJobId', 'pending');

    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('output_folder', outputFolder);
    formData.append('optimize', optimize ? 'true' : 'false');
    
    let compressRequest = $.ajax({
      url: '/api/compress_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        // Check if we were cancelled during startup
        if (state.currentCompressJobId === null) {
          console.log('Compress was cancelled during startup, ignoring response');
          // If we got a job ID back but were cancelled, cancel it immediately
          if (data.success && data.job_id) {
            console.log('Cancelling background job:', data.job_id);
            $.ajax({
              url: `/api/cancel_compress/${data.job_id}`,
              type: 'POST',
              success: function() {
                console.log('Successfully cancelled compress job during startup');
              },
              error: function(xhr, status, error) {
                console.error('Failed to cancel startup job:', error);
              }
            });
          }
          return;
        }
        
        if (data.success && data.job_id) {
          setState('currentCompressJobId', data.job_id);
          setState('currentCompressRequest', null);
          pollCompressProgress();
        } else {
          resetCompressState();
          closeModal('compress-progress-modal');
          if (data.error) {
            alert('Error: ' + data.error);
          } else {
            alert('An unknown error occurred.');
          }
        }
      },
      error: function(xhr, status, error) {
        resetCompressState();
        closeModal('compress-progress-modal');
        if (status === 'abort') {
          console.log('Compress request was aborted');
        } else {
          alert('Error: ' + (xhr.responseText || error));
        }
      }
    });
    
    setState('currentCompressRequest', compressRequest);
  });
  
  // Initialize cancel button
  initializeCompressCancel();
}