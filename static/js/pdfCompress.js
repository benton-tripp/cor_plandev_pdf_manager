// pdfCompress.js - PDF compression functionality
import { state, closeModal } from './state.js';
import { showToolSpinner, hideToolSpinner, validateFilename, validateFolder } from './utils.js';

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

// Initialize compress PDF functionality
export function initializeCompress() {
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
}