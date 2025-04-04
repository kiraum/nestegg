"use strict";
/**
 * Dark mode functionality for NestEgg
 */
// Check for saved preference in localStorage
function loadDarkModePreference() {
    const darkModeEnabled = localStorage.getItem('darkModeEnabled');
    if (darkModeEnabled === 'true') {
        document.body.classList.add('dark-mode');
    }
}
// Toggle dark mode
function toggleDarkMode() {
    const isDarkMode = document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkModeEnabled', isDarkMode.toString());
}
// Initialize dark mode
function initDarkMode() {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (!darkModeToggle)
        return;
    // Load saved preference
    loadDarkModePreference();
    // Add click event listener
    darkModeToggle.addEventListener('click', toggleDarkMode);
}
// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initDarkMode);
//# sourceMappingURL=darkmode.js.map
