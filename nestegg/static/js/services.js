const API_BASE_URL = '/api/v1';
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
        queryParams.append('start_date', params.start_date);
        queryParams.append('end_date', params.end_date);
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
        // Create query parameters
        const queryParams = new URLSearchParams();
        // Add required parameters
        queryParams.append('amount', params.amount.toString());
        queryParams.append('start_date', params.start_date);
        queryParams.append('end_date', params.end_date);
        // Add optional parameters if they exist
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
        // Add inclusion parameters for default investment types
        if (params.include_poupanca !== undefined) {
            queryParams.append('include_poupanca', params.include_poupanca.toString());
        }
        if (params.include_selic !== undefined) {
            queryParams.append('include_selic', params.include_selic.toString());
        }
        if (params.include_cdi !== undefined) {
            queryParams.append('include_cdi', params.include_cdi.toString());
        }
        if (params.include_btc !== undefined) {
            queryParams.append('include_btc', params.include_btc.toString());
        }
        const response = await fetch(`${API_BASE_URL}/compare?${queryParams.toString()}`, {
            method: 'POST',
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Error comparing investments: ${response.statusText}`);
        }
        return await response.json();
    }
    catch (error) {
        console.error('Failed to compare investments:', error);
        throw error;
    }
}
//# sourceMappingURL=services.js.map
