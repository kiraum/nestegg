import { fetchInvestmentTypes, compareInvestments } from './services.js';
import { renderInvestmentTypes, renderComparisonResults, showLoading, showError } from './ui.js';
// DOM elements
const investmentTypesContainer = document.getElementById('investment-types-container');
const resultsContainer = document.getElementById('results-container');
const compareBtn = document.getElementById('compare-btn');
const resetBtn = document.getElementById('reset-btn');
const form = document.getElementById('investment-form');
// State
let availableInvestmentTypes = [];
let selectedInvestments = new Set();
// Store user input values for each parameter
let parameterValues = {};
// Initialize the application
async function initApp() {
    try {
        // Load investment types
        availableInvestmentTypes = await fetchInvestmentTypes();
        renderInvestmentTypes(availableInvestmentTypes, investmentTypesContainer, handleInvestmentTypeToggle, selectedInvestments, parameterValues);
        // Set up event listeners
        setupEventListeners();
        // Set default dates
        setDefaultDates();
    }
    catch (error) {
        console.error('Failed to initialize app:', error);
        showError(investmentTypesContainer, 'Failed to load investment types. Please refresh the page.');
    }
}
// Set up event listeners
function setupEventListeners() {
    // Compare button
    compareBtn.addEventListener('click', handleCompare);
    // Reset button
    resetBtn.addEventListener('click', () => {
        // Simply reload the page to reset everything
        window.location.reload();
    });
    // Add event listener for investment removal via event delegation
    investmentTypesContainer.addEventListener('investment-removed', (event) => {
        const customEvent = event;
        const typeId = customEvent.detail.typeId;
        selectedInvestments.delete(typeId);
        renderInvestmentTypes(availableInvestmentTypes, investmentTypesContainer, handleInvestmentTypeToggle, selectedInvestments, parameterValues);
    });
    // Track parameter input changes
    investmentTypesContainer.addEventListener('change', (event) => {
        const target = event.target;
        if (target.tagName === 'INPUT' && target.name) {
            // Save the input value to our state
            parameterValues[target.name] = parseFloat(target.value);
        }
    });
    // "Today" buttons for date inputs
    const startDateTodayBtn = document.getElementById('start-date-today');
    const endDateTodayBtn = document.getElementById('end-date-today');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    startDateTodayBtn.addEventListener('click', () => {
        startDateInput.value = formatDateForInput(new Date());
    });
    endDateTodayBtn.addEventListener('click', () => {
        endDateInput.value = formatDateForInput(new Date());
    });
}
// Set default dates
function setDefaultDates() {
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const today = new Date();
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    startDateInput.value = formatDateForInput(oneYearAgo);
    endDateInput.value = formatDateForInput(today);
}
// Format date for input field (YYYY-MM-DD)
function formatDateForInput(date) {
    return date.toISOString().split('T')[0];
}
// Handle investment type toggle (selection/deselection)
function handleInvestmentTypeToggle(typeId) {
    if (selectedInvestments.has(typeId)) {
        selectedInvestments.delete(typeId);
    }
    else {
        selectedInvestments.add(typeId);
    }
    // Update UI
    renderInvestmentTypes(availableInvestmentTypes, investmentTypesContainer, handleInvestmentTypeToggle, selectedInvestments, parameterValues);
}
// Get form data including all selected investment parameters
function getFormData() {
    const formData = new FormData(form);
    const data = {
        amount: parseFloat(formData.get('amount')),
        start_date: formData.get('start_date'),
        end_date: formData.get('end_date')
    };
    // Add parameters for each selected investment
    for (const selectedType of selectedInvestments) {
        // Handle special cases for investment types that need inclusion flags
        if (selectedType === 'btc') {
            data['include_btc'] = true;
        }
        else if (selectedType === 'poupanca') {
            data['include_poupanca'] = true;
        }
        // Get inputs from parameter sections in the investment types container
        const typeItem = document.querySelector(`.investment-type-item[data-id="${selectedType}"]`);
        const paramSection = typeItem ? typeItem.nextElementSibling : null;
        if (paramSection) {
            const inputs = paramSection.querySelectorAll('input');
            inputs.forEach((input) => {
                if (input.name && input.value) {
                    data[input.name] = parseFloat(input.value);
                }
            });
        }
    }
    return data;
}
// Handle compare button click
async function handleCompare() {
    try {
        if (selectedInvestments.size === 0) {
            alert('Please select at least one investment type.');
            return;
        }
        // Get form data with all selected investment parameters
        const formData = getFormData();
        // Show loading state
        showLoading(resultsContainer);
        compareBtn.disabled = true;
        // Call API
        const results = await compareInvestments(formData);
        if (results.length === 0) {
            showError(resultsContainer, 'No investment results available. There might be an issue with data for future dates.');
            return;
        }
        // Render results
        renderComparisonResults(results, resultsContainer);
    }
    catch (error) {
        console.error('Comparison error:', error);
        let errorMessage = error.message || 'Failed to compare investments.';
        // Provide a more helpful message for IPCA-related errors
        if (errorMessage.includes('IPCA') || errorMessage.includes('ipca')) {
            errorMessage = 'Some investments based on IPCA inflation could not be calculated. This usually happens with future dates since inflation data is not available. The comparison will show other investment types that could be calculated.';
        }
        showError(resultsContainer, errorMessage);
    }
    finally {
        compareBtn.disabled = false;
    }
}
// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);
//# sourceMappingURL=app.js.map
