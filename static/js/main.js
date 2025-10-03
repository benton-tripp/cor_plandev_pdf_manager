import {initializePDFTools} from './pdfManager.js';

// Main initialization
$(document).ready(function () {
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
    
    // Initialize all PDF tools (compress, split, combine, optimize, extract)
    initializePDFTools(window, document);
    
    // Show body once CSS is loaded
    $('body').addClass('css-loaded');
});