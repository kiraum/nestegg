const API_BASE_URL = '/api/v1';
/**
 * Format a date string for the API (YYYY-MM-DD)
 */
function formatDateForAPI(dateStr) {
    // If the date is already in ISO format (YYYY-MM-DD), return it
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
        return dateStr;
    }
    // Otherwise, parse the date and format it
    const date = new Date(dateStr);
    return date.toISOString().split('T')[0];
}
/**
 * Fetch all investment types available from the API
 */
export async function fetchInvestmentTypes() {
    try {
        const response = await fetch(`${API_BASE_URL}/investment-types`);
        if (!response.ok) {
            throw new Error(`Error fetching investment types: ${response.statusText}`);
        }
        return await response.json();
    }
    catch (error) {
        console.error('Failed to fetch investment types:', error);
        throw error;
    }
}
/**
 * Calculate a single investment return
 */
export async function calculateInvestment(investment_type, params) {
    try {
        // Create query parameters
        const queryParams = new URLSearchParams();
        // Add required parameters
        queryParams.append('investment_type', investment_type);
        queryParams.append('amount', params.amount.toString());
        // Check and format date parameters
        if (params.start_date) {
            queryParams.append('start_date', formatDateForAPI(params.start_date));
        }
        else {
            throw new Error('Start date is required for investment calculation');
        }
        if (params.end_date) {
            queryParams.append('end_date', formatDateForAPI(params.end_date));
        }
        else {
            throw new Error('End date is required for investment calculation');
        }
        // Add optional parameters if they are provided
        if (params.cdb_rate !== undefined && investment_type === 'cdb') {
            queryParams.append('cdb_rate', params.cdb_rate.toString());
        }
        if (params.lci_rate !== undefined && investment_type === 'lci') {
            queryParams.append('lci_rate', params.lci_rate.toString());
        }
        if (params.lca_rate !== undefined && investment_type === 'lca') {
            queryParams.append('lca_rate', params.lca_rate.toString());
        }
        if (params.ipca_spread !== undefined &&
            (investment_type === 'ipca' || investment_type === 'lci_ipca' || investment_type === 'lca_ipca')) {
            queryParams.append('ipca_spread', params.ipca_spread.toString());
        }
        if (params.selic_spread !== undefined && investment_type === 'selic') {
            queryParams.append('selic_spread', params.selic_spread.toString());
        }
        if (params.cdi_percentage !== undefined &&
            (investment_type === 'cdi' || investment_type === 'lci_cdi' || investment_type === 'lca_cdi')) {
            queryParams.append('cdi_percentage', params.cdi_percentage.toString());
        }
        const response = await fetch(`${API_BASE_URL}/calculate?${queryParams.toString()}`, {
            method: 'POST',
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Error calculating investment: ${response.statusText}`);
        }
        return await response.json();
    }
    catch (error) {
        console.error('Failed to calculate investment:', error);
        throw error;
    }
}
/**
 * Compare multiple investments
 */
export async function compareInvestments(params) {
    try {
        const queryParams = new URLSearchParams();
        queryParams.append('amount', params.amount.toString());
        // Use period from date values if provided, otherwise use period directly
        if (params.start_date && params.end_date) {
            // Format dates as ISO strings (YYYY-MM-DD)
            queryParams.append('start_date', formatDateForAPI(params.start_date));
            queryParams.append('end_date', formatDateForAPI(params.end_date));
        }
        else if (params.period) {
            queryParams.append('period', params.period.toString());
        }
        else {
            throw new Error('Either period or start/end dates must be provided');
        }
        // Append optional parameters if provided
        if (params.cdb_rate !== undefined) {
            queryParams.append('cdb_rate', params.cdb_rate.toString());
        }
        if (params.lci_rate !== undefined) {
            queryParams.append('lci_rate', params.lci_rate.toString());
        }
        if (params.lca_rate !== undefined) {
            queryParams.append('lca_rate', params.lca_rate.toString());
        }
        if (params.ipca_spread !== undefined) {
            queryParams.append('ipca_spread', params.ipca_spread.toString());
        }
        if (params.selic_spread !== undefined) {
            queryParams.append('selic_spread', params.selic_spread.toString());
        }
        if (params.cdi_percentage !== undefined) {
            queryParams.append('cdi_percentage', params.cdi_percentage.toString());
        }
        if (params.lci_cdi_percentage !== undefined) {
            queryParams.append('lci_cdi_percentage', params.lci_cdi_percentage.toString());
        }
        if (params.lca_cdi_percentage !== undefined) {
            queryParams.append('lca_cdi_percentage', params.lca_cdi_percentage.toString());
        }
        if (params.lci_ipca_spread !== undefined) {
            queryParams.append('lci_ipca_spread', params.lci_ipca_spread.toString());
        }
        if (params.lca_ipca_spread !== undefined) {
            queryParams.append('lca_ipca_spread', params.lca_ipca_spread.toString());
        }
        if (params.cdb_ipca_spread !== undefined) {
            queryParams.append('cdb_ipca_spread', params.cdb_ipca_spread.toString());
        }
        // Include flags
        if (params.include_poupanca !== undefined) {
            queryParams.append('include_poupanca', params.include_poupanca.toString());
        }
        if (params.include_btc !== undefined) {
            queryParams.append('include_btc', params.include_btc.toString());
        }
        const url = `/api/v1/compare?${queryParams.toString()}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error comparing investments');
        }
        const data = await response.json();
        return data;
    }
    catch (error) {
        console.error('Error comparing investments:', error);
        throw error;
    }
}
//# sourceMappingURL=services.js.map
