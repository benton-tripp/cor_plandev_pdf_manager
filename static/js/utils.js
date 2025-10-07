// utils.js - Shared utility functions

// Track which browsers are currently open
let activeBrowsers = new Set();

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

// Disable Run and Cancel buttons for a modal during browser operation
function disableModalButtons(modalPrefix) {
  console.log(`Disabling buttons for ${modalPrefix} - browser is open`);
  $(`#${modalPrefix}-run`).prop('disabled', true);
  $(`#${modalPrefix}-cancel`).prop('disabled', true);
}

// Re-enable Run and Cancel buttons for a modal after browser operation
function enableModalButtons(modalPrefix, validationFunction) {
  console.log(`Re-enabling buttons for ${modalPrefix} - browser closed`);
  $(`#${modalPrefix}-cancel`).prop('disabled', false);
  // Re-run validation to determine if Run button should be enabled
  if (validationFunction) {
    validationFunction();
  }
}

// Mark a browser as active and disable relevant buttons
function setBrowserActive(modalPrefix) {
  activeBrowsers.add(modalPrefix);
  disableModalButtons(modalPrefix);
}

// Mark a browser as inactive and re-enable relevant buttons
function setBrowserInactive(modalPrefix, validationFunction) {
  activeBrowsers.delete(modalPrefix);
  enableModalButtons(modalPrefix, validationFunction);
}

// Folder browsing functionality for desktop app
export function selectFolder(inputId, validationFunction, modalPrefix, event) {
  // Determine modal prefix from inputId if not provided
  if (!modalPrefix) {
    modalPrefix = inputId.replace('#', '').replace('-output-folder', '');
  }
  
  // Mark browser as active and disable buttons
  setBrowserActive(modalPrefix);
  
  // Get cursor position from the event if available
  let cursorX = null;
  let cursorY = null;
  
  if (event) {
    // Use screenX/screenY for absolute screen coordinates (better for multi-monitor)
    if (event.screenX !== undefined && event.screenY !== undefined) {
      cursorX = event.screenX;
      cursorY = event.screenY;
      console.log(`Captured screen position from event: (${cursorX}, ${cursorY})`);
    } else if (event.clientX !== undefined && event.clientY !== undefined) {
      // Fallback to client coordinates if screen coordinates unavailable
      cursorX = event.clientX;
      cursorY = event.clientY;
      console.log(`Captured client position from event: (${cursorX}, ${cursorY})`);
    }
  } else {
    console.log('No event provided, dialog will use fallback positioning');
  }
  
  // Check if we're running in a webview (desktop app)
  if (window.pywebview && window.pywebview.api) {
    // Use webview folder selection (desktop app)
    window.pywebview.api.select_folder(cursorX, cursorY).then(function(folderPath) {
      if (folderPath) {
        $(inputId).val(folderPath);
        if (validationFunction) {
          validationFunction();
        }
      }
      // Re-enable buttons when browser closes
      setBrowserInactive(modalPrefix, validationFunction);
    }).catch(function(error) {
      console.log('Folder selection error:', error);
      // Re-enable buttons even on error
      setBrowserInactive(modalPrefix, validationFunction);
    });
  } else {
    // Use Flask API for native folder selection (web app)
    $.ajax({
      url: '/api/select_folder',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({
        cursor_x: cursorX,
        cursor_y: cursorY
      }),
      success: function(data) {
        if (data.success && data.folder) {
          $(inputId).val(data.folder);
          if (validationFunction) {
            validationFunction();
          }
        } else {
          console.log('Folder selection failed:', data.error);
        }
        // Re-enable buttons when browser closes
        setBrowserInactive(modalPrefix, validationFunction);
      },
      error: function(xhr, status, error) {
        console.log('Folder selection error:', error);
        // Re-enable buttons even on error
        setBrowserInactive(modalPrefix, validationFunction);
      }
    });
  }
}

// Track file input browser state for file selection dialogs
export function setupFileInputBrowserTracking(inputId, modalPrefix, validationFunction) {
  // Listen for when file input is clicked (browser about to open)
  $(inputId).on('mousedown', function() {
    setBrowserActive(modalPrefix);
  });
  
  // Listen for when file selection completes or is cancelled
  $(inputId).on('change', function() {
    // Small delay to ensure the browser dialog has closed
    setTimeout(() => {
      setBrowserInactive(modalPrefix, validationFunction);
    }, 100);
  });
  
  // Handle the case where user cancels file selection (focus returns without change)
  $(inputId).on('focus', function() {
    // If browser was active but no change event occurred, re-enable buttons
    if (activeBrowsers.has(modalPrefix)) {
      setTimeout(() => {
        if (activeBrowsers.has(modalPrefix)) {
          setBrowserInactive(modalPrefix, validationFunction);
        }
      }, 200);
    }
  });
}