// pdfManager.js - Main PDF manager coordination// pdfManager.js - Main PDF manager coordination

import { state, initializeDefaultFolder, closeModal } from './state.js';import { state, initializeDefaultFolder, closeModal } from './state.js';

import { openModal, selectFolder } from './utils.js';import { openModal, selectFolder } from './utils.js';

import { initializeCompress } from './pdfCompress.js';import { initializeCompress } from './pdfCompress.js';

import { initializeSplit } from './pdfSplit.js';import { initializeSplit } from './pdfSplit.js';

import { initializeCombine } from './pdfCombine.js';import { initializeCombine } from './pdfCombine.js';

import { initializeFlatten } from './pdfFlatten.js';import { initializeFlatten } from './pdfFlatten.js';

import { initializeOptimize } from './pdfOptimize.js';import { initializeOptimize } from './pdfOptimize.js';

import { initializeExtract } from './pdfExtract.js';import { initializeExtract } from './pdfExtract.js';



// Load default output folder on page load// Load default output folder on page load

$(document).ready(function() {$(document).ready(function() {

  initializeDefaultFolder();  initializeDefaultFolder();

});});



// Initialize all PDF tools// Initialize all PDF tools

export function compressSplitCombinePDFs(window, document) {export function compressSplitCombinePDFs(window, document) {

  // --- Modal open/close logic ---  // --- Modal open/close logic ---

  $('.tool-modal-cancel').on('click', function() {  $('.tool-modal-cancel').on('click', function() {

    closeModal($(this).data('modal'));    closeModal($(this).data('modal'));

  });  });



  // Initialize all PDF tools  // Initialize all PDF tools

  initializeCompress();  initializeCompress();

  initializeSplit();  initializeSplit();

  initializeCombine();  initializeCombine();

  initializeFlatten();  initializeFlatten();

  initializeOptimize();  initializeOptimize();

  initializeExtract();  initializeExtract();



  // Set up folder browsing functionality for all tools  // Set up folder browsing functionality for all tools

  $('#compress-browse-folder, #split-browse-folder, #combine-browse-folder, #flatten-browse-folder, #optimize-browse-folder, #extract-browse-folder').on('click', function() {  $('#compress-browse-folder, #split-browse-folder, #combine-browse-folder, #flatten-browse-folder, #optimize-browse-folder, #extract-browse-folder').on('click', function() {

    const toolType = $(this).attr('id').split('-')[0]; // extract tool type from button id    const toolType = $(this).attr('id').split('-')[0]; // extract tool type from button id

    selectFolder(`#${toolType}-output-folder`);    selectFolder(`#${toolType}-output-folder`);

  });  });



  // Expose openModal globally for navbar links  // Expose openModal globally for navbar links

  window.openModal = openModal;  window.openModal = openModal;

}}



// Export the main initialization function that includes all PDF tools// Export the main initialization function that includes all PDF tools

export function initializePDFTools(window, document) {export function initializePDFTools(window, document) {

  compressSplitCombinePDFs(window, document);  compressSplitCombinePDFs(window, document);

}}
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

