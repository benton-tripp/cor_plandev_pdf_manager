// pdfExtract.js - PDF page extraction functionality
import { state, closeModal } from './state.js';
import { showToolSpinner, hideToolSpinner, validateFilename, validateFolder } from './utils.js';

// Validate inputs for extract pages tool
function validateExtractInputs() {
    let file = $('#extract-input')[0].files[0];
    let fname = $('#extract-filename').val();
    let outputFolder = $('#extract-output-folder').val();
    let pages = $('#extract-pages').val();
    
    let isValidFilename = validateFilename(fname);
    let isValidFolder = validateFolder(outputFolder);
    let isValidPages = pages && pages.trim().length > 0;
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
}