// utils.js - Shared utility functions

// Show spinner overlay
export function showToolSpinner() {
  if ($('#tool-spinner-overlay').length) return;
  $('body').append('<div id="tool-spinner-overlay"><div class="tool-spinner"></div></div>');
}

// Hide spinner overlay
export function hideToolSpinner() {
  $('#tool-spinner-overlay').remove();
}

// Open the modal with the given id
export function openModal(id) {
  $('#' + id).fadeIn(200);
}

// Validate filename - allow most common filename characters
export function validateFilename(filename) {
  return filename && filename.trim().length > 0 && !/[<>:"/\\|?*]/.test(filename);
}

// Validate folder path
export function validateFolder(folderPath) {
  return folderPath && folderPath.trim().length > 0;
}

// Folder browsing functionality for desktop app
export function selectFolder(inputId, validationFunction) {
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
        }
      },
      error: function(xhr, status, error) {
        console.log('Folder selection error:', error);
      }
    });
  }
}