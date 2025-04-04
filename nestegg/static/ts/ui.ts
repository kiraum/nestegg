import { InvestmentTypeInfo, InvestmentResponse, ComparisonResult, FGCCoverage } from './types.js';

/**
 * Get user-friendly name for investment type
 */
function getFriendlyName(typeId: string): string {
    const nameMap: Record<string, string> = {
        'cdb': 'CDB (Prefixado)',
        'lci': 'LCI (Prefixado)',
        'lca': 'LCA (Prefixado)',
        'selic': 'Tesouro SELIC',
        'poupanca': 'Poupança',
        'ipca': 'Tesouro IPCA+',
        'cdi': 'CDB (% do CDI)',
        'btc': 'Bitcoin (BTC)',
        'lci_cdi': 'LCI (% do CDI)',
        'lca_cdi': 'LCA (% do CDI)',
        'lci_ipca': 'LCI (IPCA+)',
        'lca_ipca': 'LCA (IPCA+)'
    };

    return nameMap[typeId] || typeId;
}

/**
 * Get investment category for grouping
 */
function getInvestmentCategory(typeId: string): string {
    if (typeId.startsWith('lci')) {
        return 'LCI';
    } else if (typeId.startsWith('lca')) {
        return 'LCA';
    } else if (typeId === 'cdb' || typeId === 'cdi') {
        return 'CDB';
    } else if (typeId === 'selic' || typeId === 'ipca') {
        return 'Tesouro';
    } else if (typeId === 'poupanca') {
        return 'Poupança';
    } else if (typeId === 'btc') {
        return 'Cripto';
    }
    return 'Outros';
}

/**
 * Get rate description for investment type
 */
function getRateDescription(typeId: string): string {
    const rateDescMap: Record<string, string> = {
        'cdb': 'Annual fixed rate',
        'lci': 'Annual fixed rate',
        'lca': 'Annual fixed rate',
        'selic': 'SELIC + spread',
        'poupanca': 'Variable rate (BCB)',
        'ipca': 'IPCA + spread',
        'cdi': 'Percentage of CDI',
        'btc': 'Market price',
        'lci_cdi': 'Percentage of CDI',
        'lca_cdi': 'Percentage of CDI',
        'lci_ipca': 'IPCA + spread',
        'lca_ipca': 'IPCA + spread'
    };

    return rateDescMap[typeId] || '';
}

/**
 * Render investment types as clickable list items, grouped by category
 */
export function renderInvestmentTypes(
    types: InvestmentTypeInfo[],
    container: HTMLElement,
    onToggle: (typeId: string) => void,
    selectedTypes: Set<string> = new Set(),
    savedValues: Record<string, number> = {}
): void {
    container.innerHTML = '';

    // Group investment types by category
    const categories: Record<string, InvestmentTypeInfo[]> = {};

    types.forEach(type => {
        const category = getInvestmentCategory(type.id);
        if (!categories[category]) {
            categories[category] = [];
        }
        categories[category].push(type);
    });

    // Create a section for each category
    const categoryOrder = ['Tesouro', 'CDB', 'LCI', 'LCA', 'CDI', 'Poupança', 'Cripto', 'Outros'];

    categoryOrder.forEach(category => {
        if (!categories[category] || categories[category].length === 0) return;

        const categoryEl = document.createElement('div');
        categoryEl.className = 'investment-category mb-3';

        const categoryTitle = document.createElement('h6');
        categoryTitle.className = 'category-title mb-2';
        categoryTitle.textContent = category;
        categoryEl.appendChild(categoryTitle);

        // Create items for this category
        categories[category].forEach(type => {
            const itemContainer = document.createElement('div');
            itemContainer.className = 'investment-item-container mb-3';

            const item = document.createElement('div');
            item.className = 'investment-type-item';
            if (selectedTypes.has(type.id)) {
                item.classList.add('active');
            }
            item.dataset.id = type.id;

            const needsParams = !['poupanca', 'btc'].includes(type.id);
            const paramIcon = needsParams ? '<span class="param-indicator">⚙️</span>' : '';
            const rateDescription = getRateDescription(type.id);

            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="fw-bold">${getFriendlyName(type.id)}</div>
                    ${paramIcon}
                </div>
                <div class="rate-info text-primary small">${rateDescription}</div>
                <div class="small text-muted">${type.description}</div>
            `;

            itemContainer.appendChild(item);

            // Add parameter input if needed
            if (needsParams) {
                const paramSection = document.createElement('div');
                paramSection.className = 'parameter-section mt-2 p-2 border-top';
                paramSection.style.display = selectedTypes.has(type.id) ? 'block' : 'none';

                let inputHTML = '';

                switch (type.id) {
                    case 'cdb':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-rate" class="form-label small">CDB Rate (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-rate" name="cdb_rate" value="${savedValues['cdb_rate'] !== undefined ? savedValues['cdb_rate'] : '12.5'}" min="0.1" step="0.1" required>
                            </div>
                        `;
                        break;

                    case 'lci':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-rate" class="form-label small">LCI Rate (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-rate" name="lci_rate" value="${savedValues['lci_rate'] !== undefined ? savedValues['lci_rate'] : '11.0'}" min="0.1" step="0.1" required>
                            </div>
                        `;
                        break;

                    case 'lca':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-rate" class="form-label small">LCA Rate (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-rate" name="lca_rate" value="${savedValues['lca_rate'] !== undefined ? savedValues['lca_rate'] : '10.5'}" min="0.1" step="0.1" required>
                            </div>
                        `;
                        break;

                    case 'selic':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-spread" class="form-label small">SELIC Spread (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-spread" name="selic_spread" value="${savedValues['selic_spread'] !== undefined ? savedValues['selic_spread'] : '0.0'}" min="0" step="0.1">
                            </div>
                        `;
                        break;

                    case 'ipca':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-spread" class="form-label small">IPCA Spread (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-spread" name="ipca_spread" value="${savedValues['ipca_spread'] !== undefined ? savedValues['ipca_spread'] : '5.0'}" min="0" step="0.1">
                            </div>
                        `;
                        break;

                    case 'cdi':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-percentage" class="form-label small">CDI Percentage (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-percentage" name="cdi_percentage" value="${savedValues['cdi_percentage'] !== undefined ? savedValues['cdi_percentage'] : '100.0'}" min="0.1" step="0.1">
                            </div>
                        `;
                        break;

                    case 'lci_cdi':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-percentage" class="form-label small">LCI CDI Percentage (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-percentage" name="lci_cdi_percentage" value="${savedValues['lci_cdi_percentage'] !== undefined ? savedValues['lci_cdi_percentage'] : '95.0'}" min="0.1" step="0.1" required>
                            </div>
                        `;
                        break;

                    case 'lca_cdi':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-percentage" class="form-label small">LCA CDI Percentage (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-percentage" name="lca_cdi_percentage" value="${savedValues['lca_cdi_percentage'] !== undefined ? savedValues['lca_cdi_percentage'] : '90.0'}" min="0.1" step="0.1" required>
                            </div>
                        `;
                        break;

                    case 'lci_ipca':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-spread" class="form-label small">LCI IPCA Spread (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-spread" name="lci_ipca_spread" value="${savedValues['lci_ipca_spread'] !== undefined ? savedValues['lci_ipca_spread'] : '4.5'}" min="0" step="0.1" required>
                            </div>
                        `;
                        break;

                    case 'lca_ipca':
                        inputHTML = `
                            <div class="mb-0">
                                <label for="${type.id}-spread" class="form-label small">LCA IPCA Spread (%)</label>
                                <input type="number" class="form-control form-control-sm" id="${type.id}-spread" name="lca_ipca_spread" value="${savedValues['lca_ipca_spread'] !== undefined ? savedValues['lca_ipca_spread'] : '4.0'}" min="0" step="0.1" required>
                            </div>
                        `;
                        break;
                }

                // Add remove button at the end of the parameter section
                inputHTML += `
                    <div class="d-flex justify-content-end mt-2">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-btn">Remove</button>
                    </div>
                `;

                paramSection.innerHTML = inputHTML;

                // Add event listener for remove button
                setTimeout(() => {
                    const removeBtn = paramSection.querySelector('.remove-btn');
                    if (removeBtn) {
                        removeBtn.addEventListener('click', (e) => {
                            e.stopPropagation(); // Prevent event bubbling
                            const event = new CustomEvent('investment-removed', {
                                detail: { typeId: type.id },
                                bubbles: true // Allow event to bubble up
                            });
                            item.dispatchEvent(event);
                        });
                    }
                }, 0);

                itemContainer.appendChild(paramSection);
            }

            // Item click toggles parameter section and selection
            item.addEventListener('click', () => {
                // Toggle selection
                onToggle(type.id);

                // If parameters are needed, toggle parameter section visibility
                if (needsParams) {
                    const paramSection = item.nextElementSibling as HTMLElement;
                    if (paramSection && paramSection.classList.contains('parameter-section')) {
                        paramSection.style.display = selectedTypes.has(type.id) ? 'block' : 'none';
                    }
                }
            });

            categoryEl.appendChild(itemContainer);
        });

        container.appendChild(categoryEl);
    });
}

/**
 * Render selected investments with their parameter inputs
 */
export function renderSelectedInvestments(
    selectedTypes: Set<string>,
    allTypes: InvestmentTypeInfo[],
    container: HTMLElement,
    savedValues: Record<string, number> = {}
): void {
    if (selectedTypes.size === 0) {
        container.innerHTML = '<p class="text-muted">Select investment types from the list above</p>';
        return;
    }

    container.innerHTML = '';

    // Create a form section for each selected investment type
    selectedTypes.forEach(typeId => {
        const typeInfo = allTypes.find(t => t.id === typeId);
        if (!typeInfo) return;

        const section = document.createElement('div');
        section.className = 'selected-investment mb-3 p-2 border rounded';
        section.dataset.investmentType = typeId;

        const header = document.createElement('h6');
        header.className = 'mb-2';
        header.textContent = getFriendlyName(typeId);

        section.appendChild(header);

        // Add parameter inputs based on investment type
        const inputsContainer = document.createElement('div');
        inputsContainer.className = 'mb-2';

        // Generate inputs based on investment type
        switch (typeId) {
            case 'cdb':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-rate" class="form-label small">CDB Rate (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-rate" name="cdb_rate" value="${savedValues['cdb_rate'] !== undefined ? savedValues['cdb_rate'] : '12.5'}" min="0.1" step="0.1" required>
                    </div>
                `;
                break;

            case 'lci':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-rate" class="form-label small">LCI Rate (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-rate" name="lci_rate" value="${savedValues['lci_rate'] !== undefined ? savedValues['lci_rate'] : '11.0'}" min="0.1" step="0.1" required>
                    </div>
                `;
                break;

            case 'lca':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-rate" class="form-label small">LCA Rate (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-rate" name="lca_rate" value="${savedValues['lca_rate'] !== undefined ? savedValues['lca_rate'] : '10.5'}" min="0.1" step="0.1" required>
                    </div>
                `;
                break;

            case 'selic':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-spread" class="form-label small">SELIC Spread (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-spread" name="selic_spread" value="${savedValues['selic_spread'] !== undefined ? savedValues['selic_spread'] : '0.0'}" min="0" step="0.1">
                    </div>
                `;
                break;

            case 'ipca':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-spread" class="form-label small">IPCA Spread (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-spread" name="ipca_spread" value="${savedValues['ipca_spread'] !== undefined ? savedValues['ipca_spread'] : '5.0'}" min="0" step="0.1">
                    </div>
                `;
                break;

            case 'cdi':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-percentage" class="form-label small">CDI Percentage (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-percentage" name="cdi_percentage" value="${savedValues['cdi_percentage'] !== undefined ? savedValues['cdi_percentage'] : '100.0'}" min="0.1" step="0.1">
                    </div>
                `;
                break;

            case 'lci_cdi':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-percentage" class="form-label small">LCI CDI Percentage (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-percentage" name="lci_cdi_percentage" value="${savedValues['lci_cdi_percentage'] !== undefined ? savedValues['lci_cdi_percentage'] : '95.0'}" min="0.1" step="0.1" required>
                    </div>
                `;
                break;

            case 'lca_cdi':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-percentage" class="form-label small">LCA CDI Percentage (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-percentage" name="lca_cdi_percentage" value="${savedValues['lca_cdi_percentage'] !== undefined ? savedValues['lca_cdi_percentage'] : '90.0'}" min="0.1" step="0.1" required>
                    </div>
                `;
                break;

            case 'lci_ipca':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-spread" class="form-label small">LCI IPCA Spread (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-spread" name="lci_ipca_spread" value="${savedValues['lci_ipca_spread'] !== undefined ? savedValues['lci_ipca_spread'] : '4.5'}" min="0" step="0.1" required>
                    </div>
                `;
                break;

            case 'lca_ipca':
                inputsContainer.innerHTML = `
                    <div class="mb-2">
                        <label for="${typeId}-spread" class="form-label small">LCA IPCA Spread (%)</label>
                        <input type="number" class="form-control form-control-sm" id="${typeId}-spread" name="lca_ipca_spread" value="${savedValues['lca_ipca_spread'] !== undefined ? savedValues['lca_ipca_spread'] : '4.0'}" min="0" step="0.1" required>
                    </div>
                `;
                break;
        }

        section.appendChild(inputsContainer);

        // Add remove button
        const removeBtn = document.createElement('button');
        removeBtn.className = 'btn btn-sm btn-outline-danger';
        removeBtn.textContent = 'Remove';
        removeBtn.addEventListener('click', () => {
            const event = new CustomEvent('investment-removed', { detail: { typeId } });
            container.dispatchEvent(event);
        });

        section.appendChild(removeBtn);
        container.appendChild(section);
    });
}

/**
 * Format currency values as BRL
 */
function formatCurrency(value: number): string {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

/**
 * Format percentage values
 */
function formatPercentage(value: number): string {
    return new Intl.NumberFormat('pt-BR', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

/**
 * Render a single investment result
 */
export function renderInvestmentResult(result: InvestmentResponse, container: HTMLElement): void {
    container.innerHTML = '';

    const investmentName = result.investment_type.toUpperCase().replace('_', ' ');
    const taxFreeLabel = result.tax_info.is_tax_free
        ? '<span class="tax-free-badge">Tax Free</span>'
        : '';

    const resultCard = document.createElement('div');
    resultCard.className = 'result-card';
    resultCard.innerHTML = `
        <h4>${investmentName} ${taxFreeLabel}</h4>
        <div class="row">
            <div class="col-md-6">
                <p><span class="label">Initial Amount:</span> <span class="value">${formatCurrency(result.initial_amount)}</span></p>
                <p><span class="label">Final Amount:</span> <span class="value result-highlight">${formatCurrency(result.final_amount)}</span></p>
                <p><span class="label">Gross Profit:</span> <span class="value">${formatCurrency(result.gross_profit)}</span></p>
                <p><span class="label">Net Profit:</span> <span class="value">${formatCurrency(result.net_profit)}</span></p>
            </div>
            <div class="col-md-6">
                <p><span class="label">Tax Amount:</span> <span class="value">${formatCurrency(result.tax_amount)}</span></p>
                <p><span class="label">Effective Rate:</span> <span class="value result-highlight">${formatPercentage(result.effective_rate)}</span></p>
                <p><span class="label">Rate:</span> <span class="value">${formatPercentage(result.rate)}</span></p>
                <p><span class="label">Tax Rate:</span> <span class="value">${formatPercentage(result.tax_info.tax_rate_percentage)}</span></p>
            </div>
        </div>
        <div class="mt-3">
            <p><strong>Tax Period:</strong> ${result.tax_info.tax_period_description}</p>
            <p><strong>Period:</strong> ${new Date(result.start_date).toLocaleDateString()} to ${new Date(result.end_date).toLocaleDateString()}</p>
        </div>
        ${renderFGCCoverageInfo(result.fgc_coverage)}
    `;

    container.appendChild(resultCard);
}

/**
 * Render FGC coverage information
 */
function renderFGCCoverageInfo(fgcCoverage: FGCCoverage): string {
    if (!fgcCoverage) return '';

    let coverageClass = fgcCoverage.is_covered ? 'text-success' : 'text-danger';
    let coverageBadge = fgcCoverage.is_covered
        ? `<span class="badge bg-success">Covered</span>`
        : `<span class="badge bg-danger">Not Covered</span>`;

    let coverageDetails = '';
    if (fgcCoverage.is_covered) {
        const coveragePercentage = formatPercentage(fgcCoverage.coverage_percentage);
        coverageDetails = `
            <div class="row mt-2">
                <div class="col-md-6">
                    <p><span class="label">Covered Amount:</span> <span class="value">${formatCurrency(fgcCoverage.covered_amount)}</span></p>
                </div>
                <div class="col-md-6">
                    <p><span class="label">Coverage:</span> <span class="value">${coveragePercentage}</span></p>
                </div>
            </div>
        `;

        if (fgcCoverage.uncovered_amount > 0) {
            coverageDetails += `
                <div class="alert alert-warning mt-2">
                    <small>Warning: ${formatCurrency(fgcCoverage.uncovered_amount)} exceeds the FGC guarantee limit and is not covered.</small>
                </div>
            `;
        }
    }

    return `
        <div class="fgc-coverage-info mt-3 p-3 border rounded">
            <h5 class="mb-2">FGC Guarantee Coverage ${coverageBadge}</h5>
            <p>${fgcCoverage.description}</p>
            ${coverageDetails}
        </div>
    `;
}

/**
 * Render comparison results
 */
export function renderComparisonResults(results: ComparisonResult[], container: HTMLElement): void {
    container.innerHTML = '';

    if (results.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">No investment comparison results available.</div>';
        return;
    }

    // Create a bar chart with all results
    const chartContainer = document.createElement('div');
    chartContainer.className = 'chart-container';
    chartContainer.innerHTML = '<canvas id="comparison-chart"></canvas>';
    container.appendChild(chartContainer);

    // Create result cards for each investment
    results.forEach((result, index) => {
        const resultCard = document.createElement('div');
        resultCard.className = index === 0 ? 'result-card best-option' : 'result-card';

        const taxFreeLabel = result.tax_free
            ? '<span class="tax-free-badge">Tax Free</span>'
            : '';

        // FGC Coverage badge
        let fgcBadge = '';
        if (result.fgc_coverage) {
            fgcBadge = result.fgc_coverage.is_covered
                ? '<span class="badge bg-success ms-1">FGC Covered</span>'
                : '';
        }

        resultCard.innerHTML = `
            <h5>${result.type} ${taxFreeLabel} ${fgcBadge}</h5>
            <p class="recommendation">${result.recommendation}</p>
            <div class="row result-values">
                <div class="col-md-6">
                    <p><span class="label">Net Profit:</span> <span class="value result-highlight">${formatCurrency(result.net_profit)}</span></p>
                    <p><span class="label">Effective Rate:</span> <span class="value result-highlight">${formatPercentage(result.effective_rate)}</span></p>
                </div>
                <div class="col-md-6">
                    <p><span class="label">Final Amount:</span> <span class="value">${formatCurrency(result.final_amount)}</span></p>
                    <p><span class="label">Tax Amount:</span> <span class="value">${formatCurrency(result.tax_amount)}</span></p>
                </div>
            </div>
            ${result.fgc_coverage && result.fgc_coverage.uncovered_amount > 0 ?
                `<div class="alert alert-warning mt-2 p-2">
                    <small>Warning: ${formatCurrency(result.fgc_coverage.uncovered_amount)} exceeds FGC limit</small>
                </div>` : ''
            }
        `;

        container.appendChild(resultCard);
    });

    // Initialize chart after rendering all cards
    renderComparisonChart(results);
}

/**
 * Render a chart with the comparison results
 */
function renderComparisonChart(results: ComparisonResult[]): void {
    const canvas = document.getElementById('comparison-chart') as HTMLCanvasElement;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // @ts-ignore - Chart.js is loaded from CDN
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: results.map(r => r.type),
            datasets: [
                {
                    label: 'Net Profit (R$)',
                    data: results.map(r => r.net_profit),
                    backgroundColor: results.map((_, i) => i === 0 ? '#4c51bf' : '#a3bffa'),
                    borderColor: results.map((_, i) => i === 0 ? '#434190' : '#7f9cf5'),
                    borderWidth: 1
                },
                {
                    label: 'Tax Amount (R$)',
                    data: results.map(r => r.tax_amount),
                    backgroundColor: '#cbd5e0',
                    borderColor: '#a0aec0',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Investment Comparison'
                },
                tooltip: {
                    callbacks: {
                        label: function(context: any) {
                            const value = context.raw as number;
                            return `${context.dataset.label}: ${formatCurrency(value)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value: any) {
                            return formatCurrency(value as number);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Show loading indicator
 */
export function showLoading(container: HTMLElement): void {
    container.innerHTML = `
        <div class="spinner-container">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
}

/**
 * Show error message
 */
export function showError(container: HTMLElement, message: string): void {
    container.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <h5>Error</h5>
            <p>${message}</p>
        </div>
    `;
}
