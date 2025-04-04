import { InvestmentResponse, ComparisonResult, FormData, InvestmentTypeInfo } from './types.js';
import { fetchInvestmentTypes, calculateInvestment, compareInvestments } from './services.js';
import {
    renderInvestmentTypes,
    renderComparisonResults,
    showLoading,
    showError
} from './ui.js';

// DOM elements
const investmentTypesContainer = document.getElementById('investment-types-container') as HTMLElement;
const resultsContainer = document.getElementById('results-container') as HTMLElement;
const compareBtn = document.getElementById('compare-btn') as HTMLButtonElement;
const resetBtn = document.getElementById('reset-btn') as HTMLButtonElement;
const form = document.getElementById('investment-form') as HTMLFormElement;

// State
let availableInvestmentTypes: InvestmentTypeInfo[] = [];
let selectedInvestments: Set<string> = new Set();
// Store user input values for each parameter
let parameterValues: Record<string, number> = {};

// Initialize the application
async function initApp(): Promise<void> {
    try {
        // Load investment types
        availableInvestmentTypes = await fetchInvestmentTypes();
        renderInvestmentTypes(availableInvestmentTypes, investmentTypesContainer, handleInvestmentTypeToggle, selectedInvestments, parameterValues);

        // Set up event listeners
        setupEventListeners();

        // Set default dates
        setDefaultDates();

    } catch (error) {
        console.error('Failed to initialize app:', error);
        showError(investmentTypesContainer, 'Failed to load investment types. Please refresh the page.');
    }
}

// Set up event listeners
function setupEventListeners(): void {
    // Compare button
    compareBtn.addEventListener('click', handleCompare);

    // Reset button
    resetBtn.addEventListener('click', () => {
        // Simply reload the page to reset everything
        window.location.reload();
    });

    // Add event listener for investment removal via event delegation
    investmentTypesContainer.addEventListener('investment-removed', (event: Event) => {
        const customEvent = event as CustomEvent;
        const typeId = customEvent.detail.typeId;
        selectedInvestments.delete(typeId);
        renderInvestmentTypes(availableInvestmentTypes, investmentTypesContainer, handleInvestmentTypeToggle, selectedInvestments, parameterValues);
    });

    // Track parameter input changes
    investmentTypesContainer.addEventListener('change', (event: Event) => {
        const target = event.target as HTMLInputElement;
        if (target.tagName === 'INPUT' && target.name) {
            // Save the input value to our state
            parameterValues[target.name] = parseFloat(target.value);
        }
    });

    // "Today" buttons for date inputs
    const startDateTodayBtn = document.getElementById('start-date-today') as HTMLButtonElement;
    const endDateTodayBtn = document.getElementById('end-date-today') as HTMLButtonElement;
    const startDateInput = document.getElementById('start-date') as HTMLInputElement;
    const endDateInput = document.getElementById('end-date') as HTMLInputElement;

    startDateTodayBtn.addEventListener('click', () => {
        startDateInput.value = formatDateForInput(new Date());
    });

    endDateTodayBtn.addEventListener('click', () => {
        endDateInput.value = formatDateForInput(new Date());
    });
}

// Set default dates
function setDefaultDates(): void {
    const startDateInput = document.getElementById('start-date') as HTMLInputElement;
    const endDateInput = document.getElementById('end-date') as HTMLInputElement;

    const today = new Date();
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(today.getFullYear() - 1);

    startDateInput.value = formatDateForInput(oneYearAgo);
    endDateInput.value = formatDateForInput(today);
}

// Format date for input field (YYYY-MM-DD)
function formatDateForInput(date: Date): string {
    return date.toISOString().split('T')[0];
}

// Handle investment type toggle (selection/deselection)
function handleInvestmentTypeToggle(typeId: string): void {
    if (selectedInvestments.has(typeId)) {
        selectedInvestments.delete(typeId);
    } else {
        selectedInvestments.add(typeId);
    }

    // Update UI
    renderInvestmentTypes(availableInvestmentTypes, investmentTypesContainer, handleInvestmentTypeToggle, selectedInvestments, parameterValues);
}

// Get form data including all selected investment parameters
function getFormData(): FormData {
    const formData = new FormData(form);
    const data: FormData = {
        amount: parseFloat(formData.get('amount') as string),
        start_date: formData.get('start_date') as string,
        end_date: formData.get('end_date') as string
    };

    // Add parameters for each selected investment
    for (const selectedType of selectedInvestments) {
        // Handle special cases for investment types that need inclusion flags
        if (selectedType === 'btc') {
            (data as any)['include_btc'] = true;
        } else if (selectedType === 'poupanca') {
            (data as any)['include_poupanca'] = true;
        } else if (selectedType === 'selic') {
            // Only include the flag if no selic_spread is being provided
            const selicinputVal = document.querySelector('input[name="selic_spread"]') as HTMLInputElement;
            if (!selicinputVal || !selicinputVal.value) {
                (data as any)['include_selic'] = true;
            }
        } else if (selectedType === 'cdb_ipca') {
            // Only include the flag if no cdb_ipca_spread is being provided
            const ipcaInputVal = document.querySelector('input[name="cdb_ipca_spread"]') as HTMLInputElement;
            if (!ipcaInputVal || !ipcaInputVal.value) {
                (data as any)['include_cdb_ipca'] = true;
            }
        }

        // Get inputs from parameter sections in the investment types container
        const typeItem = document.querySelector(`.investment-type-item[data-id="${selectedType}"]`);
        const paramSection = typeItem ? typeItem.nextElementSibling as HTMLElement : null;

        if (paramSection) {
            const inputs = paramSection.querySelectorAll('input');
            inputs.forEach((input: HTMLInputElement) => {
                if (input.name && input.value) {
                    (data as any)[input.name] = parseFloat(input.value);
                }
            });
        }
    }

    return data;
}

// Handle compare button click
async function handleCompare(): Promise<void> {
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
    } catch (error) {
        console.error('Comparison error:', error);

        let errorMessage = (error as Error).message || 'Failed to compare investments.';

        // Provide a more helpful message for IPCA-related errors
        if (errorMessage.includes('IPCA') || errorMessage.includes('ipca')) {
            errorMessage = 'Some investments based on IPCA inflation could not be calculated. This usually happens with future dates since inflation data is not available. The comparison will show other investment types that could be calculated.';
        }

        showError(resultsContainer, errorMessage);
    } finally {
        compareBtn.disabled = false;
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);
