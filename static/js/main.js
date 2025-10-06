import { state, initializeDefaultFolder, closeModal } from './state.js';
import { openModal, selectFolder } from './utils.js';
import { initializeCompress } from './pdfCompress.js';
import { initializeSplit } from './pdfSplit.js';
import { initializeCombine } from './pdfCombine.js';
import { initializeFlatten } from './pdfFlatten.js';
import { initializeOptimize } from './pdfOptimize.js';
import { initializeExtract } from './pdfExtract.js';

// Main initialization
$(document).ready(function () {
    // Load default output folder on page load
    initializeDefaultFolder();
    
    // Mobile navbar toggle
    $('#navbar-toggle').on('click', function() {
        $('#navbar-menu').toggleClass('show');
    });
    
    // Close mobile menu when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.navbar').length) {
            $('#navbar-menu').removeClass('show');
        }
    });
    
    // Modal close functionality
    $('.tool-modal-cancel').on('click', function() {
        closeModal($(this).data('modal'));
    });
    
    // Initialize all PDF tools
    initializeCompress();
    initializeSplit();
    initializeCombine();
    initializeFlatten();
    initializeOptimize();
    initializeExtract();
    
    // Set up folder browsing functionality for all tools
    $('#compress-browse-folder').on('click', function() {
        selectFolder('#compress-output-folder', () => {});
    });
    
    $('#split-browse-folder').on('click', function() {
        selectFolder('#split-output-folder', () => {});
    });
    
    $('#combine-browse-folder').on('click', function() {
        selectFolder('#combine-output-folder', () => {});
    });
    
    $('#flatten-browse-folder').on('click', function() {
        selectFolder('#flatten-output-folder', () => {});
    });
    
    $('#optimize-browse-folder').on('click', function() {
        selectFolder('#optimize-output-folder', () => {});
    });
    
    $('#extract-browse-folder').on('click', function() {
        selectFolder('#extract-output-folder', () => {});
    });
    
    // Expose openModal globally for navbar links
    window.openModal = openModal;
    
    // Show body once CSS is loaded
    $('body').addClass('css-loaded');
});