// static/scripts.js

// This file is intended for global JavaScript functions or initializations
// that might be used across multiple pages of your Flask application.

document.addEventListener('DOMContentLoaded', function() {
    console.log("scripts.js loaded successfully!");

    // Example: You could add a simple scroll-to-top button functionality here
    // const scrollToTopBtn = document.getElementById("scrollToTopBtn");
    // if (scrollToTopBtn) {
    //     window.onscroll = function() {
    //         if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
    //             scrollToTopBtn.style.display = "block";
    //         } else {
    //             scrollToTopBtn.style.display = "none";
    //         }
    //     };
    //     scrollToTopBtn.onclick = function() {
    //         document.body.scrollTop = 0; // For Safari
    //         document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
    //     };
    // }

    // Example: Basic client-side validation for common forms (if not handled by Flask-WTF)
    // function validateEmail(email) {
    //     const re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    //     return re.test(String(email).toLowerCase());
    // }
});

// Any other global helper functions can be defined here
// function myFunctionGlobal() {
//     console.log("This is a global function.");
// }