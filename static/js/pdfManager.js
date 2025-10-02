// pdfManager.js
import {state} from './state.js';

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
    $('#compress-flatten').prop('checked', false);
  } else if (id === 'combine-modal') {
    // Clear inputs and reset flatten checkbox for combine modal
    $('#combine-input').val('');
    $('#combine-filename').val('').prop('disabled', true);
    $('#combine-flatten').prop('checked', false);
  } else if (id === 'flatten-modal') {
    // Clear inputs and reset checkboxes for flatten modal
    $('#flatten-input').val('');
    $('#flatten-filename').val('').prop('disabled', true);
    $('#flatten-remove-links').prop('checked', false);
    $('#flatten-keep-annotations').prop('checked', false);
    $('#flatten-keep-transparency').prop('checked', false);
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
  updateSplitProgress(0, 0, 0, 0, 0, 'Initializing...');
}

// Hide split progress modal
function hideSplitProgress() {
  $('#split-progress-modal').fadeOut(200);
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
  
  // Better chunk display
  if (totalChunks > 0) {
    if (message && message.includes('Completed chunk')) {
      $('#progress-chunks').text(`${currentChunk} of ${totalChunks} chunks complete`);
    } else if (message && (message.includes('Saving chunk') || message.includes('Processed page'))) {
      $('#progress-chunks').text(`Working on chunk ${currentChunk + 1} of ${totalChunks}`);
    } else {
      $('#progress-chunks').text(`0 of ${totalChunks} chunks complete`);
    }
  } else {
    $('#progress-chunks').text('Calculating chunks...');
  }
  
  $('#progress-fill').css('width', percentage + '%');
  $('#progress-percentage').text(percentage + '%');
  $('#progress-status').text(message);
}

// Poll for split progress
function pollSplitProgress(jobId) {
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
        
        updateSplitProgress(
          data.current_page || 0,
          data.total_pages || 0,
          data.current_chunk || 0,
          data.total_chunks || 0,
          data.percentage || 0,
          data.message || 'Processing...'
        );
        
        if (data.status === 'complete') {
          setTimeout(() => {
            hideSplitProgress();
            closeModal('split-modal');
            if (data.zipfile) {
              window.location = '/download/' + encodeURIComponent(data.zipfile);
            }
          }, 1000); // Show 100% for a moment before closing
        } else if (data.status === 'error') {
          hideSplitProgress();
          $('#split-message').text('Error: ' + (data.message || 'Split failed'));
        } else {
          // Continue polling - faster polling for better synchronization
          setTimeout(poll, 250); // Poll every 250ms (4 times per second)
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

// Validate inputs for compress PDF tool
function validateCompressInputs() {
  let file = $('#compress-input')[0].files[0];
  let fname = $('#compress-filename').val();
  
  // More permissive filename validation - allow most common filename characters
  let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
  let canRun = file && isValidFilename;
  
  $('#compress-run').prop('disabled', !canRun);
}

// Validate inputs for split PDF tool
function validateSplitInputs() {
  let file = $('#split-input')[0].files[0];
  let fname = $('#split-filename').val();
  let method = $('input[name="split-method"]:checked').val();
  
  let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
  let canRun = file && isValidFilename && splitTotalPages > 1;
  
  if (method === 'pages') {
    let maxPages = parseInt($('#split-max-pages').val());
    canRun = canRun && maxPages > 0;
  } else if (method === 'size') {
    let maxSize = parseFloat($('#split-max-size').val());
    canRun = canRun && maxSize > 0;
  }
  
  console.log('Validation:', {file: !!file, fname, method, isValidFilename, splitTotalPages, canRun});
  
  $('#split-run').prop('disabled', !canRun);
}

// Validate inputs for combine PDFs tool
function validateCombineInputs() {
    let files = $('#combine-input')[0].files;
    let fname = $('#combine-filename').val();
    
    let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
    let canRun = files.length > 0 && isValidFilename;
    
    $('#combine-run').prop('disabled', !canRun);
}

// Validate inputs for flatten PDF tool
function validateFlattenInputs() {
    let file = $('#flatten-input')[0].files[0];
    let fname = $('#flatten-filename').val();
    
    let isValidFilename = fname && fname.trim().length > 0 && !/[<>:"/\\|?*]/.test(fname);
    let canRun = file && isValidFilename;
    
    $('#flatten-run').prop('disabled', !canRun);
}

// Compress, split, and combine PDF functions
export function compressSplitCombinePDFs(window, document) {
  // --- Modal open/close logic ---
  $('.tool-modal-cancel').on('click', function() {
    closeModal($(this).data('modal'));
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
  $('#compress-run').on('click', function() {
    let file = $('#compress-input')[0].files[0];
    let fname = $('#compress-filename').val();
    let flatten = $('#compress-flatten').is(':checked');
    if (!file || !fname) return;

    console.log('Compress run clicked:', {file: file.name, fname, flatten});

    showToolSpinner();
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('flatten', flatten ? 'true' : 'false');
    $.ajax({
      url: '/api/compress_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        hideToolSpinner();
        if (data.success && data.filename) {
          // Immediately close modal and start download
          closeModal('compress-modal');
          window.location = '/download/' + encodeURIComponent(data.filename);
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
          window.pdfjsLib.getDocument({data: ev.target.result}).promise.then(function(pdf=state.pdfDoc) {
            splitTotalPages = pdf.numPages;
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
          });
        } else {
          // Fallback when PDF.js not available
          splitTotalPages = 999; // Assume multi-page
          if (method === 'pages') {
            $('#split-max-pages').val(10);
          }
          $('#split-warning').hide();
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
  $('#split-filename, #split-max-pages, #split-max-size').on('input', validateSplitInputs);
  
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
    
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_zip', fname);
    
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
  $('#combine-run').on('click', function() {
    let files = $('#combine-input')[0].files;
    let fname = $('#combine-filename').val();
    let flatten = $('#combine-flatten').is(':checked');
    if (!(files.length > 0 && fname)) return;

    console.log('Combine run clicked:', {fileCount: files.length, fname, flatten});

    showToolSpinner();
    let formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('pdf_list', files[i]);
    }
    formData.append('output_filename', fname);
    formData.append('flatten', flatten ? 'true' : 'false');
    $.ajax({
      url: '/api/combine_pdfs',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        hideToolSpinner();
        if (data.success && data.filename) {
          // Immediately close modal and start download
          closeModal('combine-modal');
          window.location = '/download/' + encodeURIComponent(data.filename);
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
  $('#flatten-run').on('click', function() {
    let file = $('#flatten-input')[0].files[0];
    let fname = $('#flatten-filename').val();
    let removeLinks = $('#flatten-remove-links').is(':checked');
    let keepAnnotations = $('#flatten-keep-annotations').is(':checked');
    let keepTransparency = $('#flatten-keep-transparency').is(':checked');
    if (!file || !fname) return;

    console.log('Flatten run clicked:', {file: file.name, fname, removeLinks, keepAnnotations, keepTransparency});

    showToolSpinner();
    let formData = new FormData();
    formData.append('input_pdf', file);
    formData.append('output_filename', fname);
    formData.append('remove_links', removeLinks ? 'true' : 'false');
    formData.append('remove_annotations', keepAnnotations ? 'false' : 'true'); // Inverted logic
    formData.append('flatten_transparency', keepTransparency ? 'false' : 'true'); // Inverted logic
    $.ajax({
      url: '/api/flatten_pdf',
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function(data) {
        hideToolSpinner();
        if (data.success && data.filename) {
          // Immediately close modal and start download
          closeModal('flatten-modal');
          window.location = '/download/' + encodeURIComponent(data.filename);
        } else if (!data.success && data.error) {
          $('#flatten-message').text('Error: ' + data.error);
        } else {
          $('#flatten-message').text('An unknown error occurred.');
        }
      },
      error: function(xhr) {
        hideToolSpinner();
        $('#flatten-message').text('Error: ' + xhr.responseText);
      }
    });
  });

  // Expose openModal globally for navbar links
  window.openModal = openModal;
}

