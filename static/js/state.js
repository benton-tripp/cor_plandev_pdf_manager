// state.js

// Unified state object
export const state = {
    pdfDoc: null,
    defaultOutputFolder: '',
    splitTotalPages: 0,
    currentSplitJobId: null,
    currentFlattenJobId: null,
    currentExtractJobId: null,
    currentExtractRequest: null,
    currentOptimizeJobId: null,
    currentOptimizeRequest: null,
    currentCompressJobId: null,
    currentCompressRequest: null,
    currentCombineJobId: null,
    currentCombineRequest: null
};

// General setter for state properties
export function setState(key, value) {
    if (key in state) {
        state[key] = value;
    } else {
        throw new Error(`State key '${key}' does not exist.`);
    }
}

// Initialize default output folder
export function initializeDefaultFolder() {
    $.get('/api/get_default_output_folder')
        .done(function(data) {
            setState('defaultOutputFolder', data.folder);
            // Set default values in all output folder inputs
            $('#compress-output-folder').val(state.defaultOutputFolder);
            $('#split-output-folder').val(state.defaultOutputFolder);
            $('#combine-output-folder').val(state.defaultOutputFolder);
            $('#flatten-output-folder').val(state.defaultOutputFolder);
            $('#optimize-output-folder').val(state.defaultOutputFolder);
            $('#extract-output-folder').val(state.defaultOutputFolder);
        })
        .fail(function() {
            console.warn('Could not load default output folder');
        });
}

// Close modal and reset message
export function closeModal(id) {
    $('#' + id).fadeOut(200);
    $('#' + id + ' .tool-modal-message').text('');
    // Clear inputs but preserve radio button states and reset to defaults
    if (id === 'split-modal') {
        $('#split-input').val('');
        $('#split-filename').val('').prop('disabled', true);
        $('#split-output-folder').val(state.defaultOutputFolder);
        $('#split-max-pages').val('').prop('disabled', true);
        $('#split-max-size').val('').prop('disabled', true);
        // Reset radio buttons to default (pages)
        $('#split-method-pages').prop('checked', true);
        $('#split-pages-row').show();
        $('#split-size-row').hide();
        $('#split-warning').hide();
        setState('splitTotalPages', 0);
    } else if (id === 'compress-modal') {
        // Clear inputs and reset flatten checkbox for compress modal
        $('#compress-input').val('');
        $('#compress-filename').val('').prop('disabled', true);
        $('#compress-output-folder').val(state.defaultOutputFolder);
        $('#compress-optimize').prop('checked', false);
    } else if (id === 'combine-modal') {
        // Clear inputs and reset flatten checkbox for combine modal
        $('#combine-input').val('');
        $('#combine-filename').val('').prop('disabled', true);
        $('#combine-output-folder').val(state.defaultOutputFolder);
        $('#combine-optimize').prop('checked', false);
    } else if (id === 'flatten-modal') {
        // Clear inputs for flatten modal
        $('#flatten-input').val('');
        $('#flatten-filename').val('').prop('disabled', true);
        $('#flatten-output-folder').val(state.defaultOutputFolder);
    } else if (id === 'optimize-modal') {
        // Clear inputs for optimize modal
        $('#optimize-input').val('');
        $('#optimize-filename').val('').prop('disabled', true);
        $('#optimize-output-folder').val(state.defaultOutputFolder);
        $('#optimize-aggressive').prop('checked', false);
    } else if (id === 'extract-modal') {
        // Clear inputs for extract modal
        $('#extract-input').val('');
        $('#extract-filename').val('').prop('disabled', true);
        $('#extract-output-folder').val(state.defaultOutputFolder);
        $('#extract-pages').val('');
    } else {
        // For other modals, clear all inputs as before
        $('#' + id + ' input').val('');
    }
    $('#' + id + ' .tool-modal-run').prop('disabled', true);
}
