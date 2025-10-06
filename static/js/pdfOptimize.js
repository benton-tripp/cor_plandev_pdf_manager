// pdfOptimize.js - PDF optimization functionality
import { state, closeModal } from './state.js';
import { showToolSpinner, hideToolSpinner, validateFilename, validateFolder } from './utils.js';

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

// Initialize optimize PDF functionality
export function initializeOptimize() {
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
}