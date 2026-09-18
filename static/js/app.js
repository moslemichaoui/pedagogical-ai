// Basic JavaScript functionality for the application

document.addEventListener('DOMContentLoaded', function() {
    console.log('Pedagogical AI application loaded');
    
    // Add any interactive functionality here
    // For now, this is just a placeholder
    
    // Example: Add click event to nav links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Remove active class from all links
            navLinks.forEach(l => l.classList.remove('active'));
            // Add active class to clicked link
            this.classList.add('active');
        });
    });
});