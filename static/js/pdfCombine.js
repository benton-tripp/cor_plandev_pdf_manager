// pdfCombine.js - PDF combining functionality
import { state, closeModal } from './state.js';
import { showToolSpinner, hideToolSpinner, validateFilename, validateFolder } from './utils.js';

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

// Initialize combine PDF functionality
export function initializeCombine() {
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
}