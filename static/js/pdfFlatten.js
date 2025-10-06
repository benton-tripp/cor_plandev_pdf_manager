// pdfFlatten.js - PDF flattening functionality
import { state, setState, closeModal } from './state.js';
import { openModal, validateFilename, validateFolder } from './utils.js';

// Track flatten progress
function trackFlattenProgress(jobId) {
  setState('currentFlattenJobId', jobId); // Store job ID for cancellation
  
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

// Validate inputs for flatten PDF tool
function validateFlattenInputs() {
    let file = $('#flatten-input')[0].files[0];
    let fname = $('#flatten-filename').val();
    let outputFolder = $('#flatten-output-folder').val();
    
    let isValidFilename = validateFilename(fname);
    let isValidFolder = validateFolder(outputFolder);
    let canRun = file && isValidFilename && isValidFolder;
    
    $('#flatten-run').prop('disabled', !canRun);
}

// Initialize flatten cancel button handler
function initializeFlattenCancel() {
  $('#flatten-cancel-btn').on('click', function() {
    if (state.currentFlattenJobId) {
      // Disable button immediately to prevent multiple clicks
      $(this).prop('disabled', true).text('Cancelling...');
      
      // Show immediate feedback to user
      $('#flatten-progress-status').text('Cancellation requested...');
      
      $.ajax({
        url: `/api/cancel_flatten/${state.currentFlattenJobId}`,
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
}

// Initialize flatten PDF functionality
export function initializeFlatten() {
  // Store validation function globally for browser tracking
  window.validateFlattenInputs = validateFlattenInputs;
  
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
    $('#flatten-progress-status').text('Starting flatten process...');

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

  // Initialize cancel button functionality
  initializeFlattenCancel();
}