// Investment types enumeration
export enum InvestmentType {
    CDB = "cdb",
    LCI = "lci",
    LCA = "lca",
    SELIC = "selic",
    POUPANCA = "poupanca",
    IPCA = "ipca",
    CDB_CDI = "cdi",
    BTC = "btc",
    LCI_CDI = "lci_cdi",
    LCA_CDI = "lca_cdi",
    LCI_IPCA = "lci_ipca",
    LCA_IPCA = "lca_ipca",
    CDB_IPCA = "cdb_ipca"
}

// Investment type description interface
export interface InvestmentTypeInfo {
    id: string;
    name: string;
    description: string;
}

// Tax information interface
export interface TaxInfo {
    tax_rate_percentage: number;
    tax_amount: number;
    is_tax_free: boolean;
    tax_period_days: number;
    tax_period_description: string;
}

// FGC coverage information interface
export interface FGCCoverage {
    is_covered: boolean;
    covered_amount: number;
    uncovered_amount: number;
    coverage_percentage: number;
    limit_per_institution?: number;
    total_coverage_limit?: number;
    description: string;
}

// Investment calculation request
export interface InvestmentRequest {
    investment_type: InvestmentType;
    amount: number;
    start_date: string;
    end_date: string;
    cdb_rate?: number;
    lci_rate?: number;
    lca_rate?: number;
    ipca_spread?: number;
    selic_spread?: number;
    cdi_percentage?: number;
}

// Investment calculation response
export interface InvestmentResponse {
    investment_type: string;
    initial_amount: number;
    final_amount: number;
    gross_profit: number;
    net_profit: number;
    tax_amount: number;
    effective_rate: number;
    start_date: string;
    end_date: string;
    rate: number;
    tax_info: TaxInfo;
    fgc_coverage: FGCCoverage;
}

// Comparison response with additional recommendation
export interface ComparisonResult extends InvestmentResponse {
    type: string;
    recommendation: string;
    tax_free: boolean;
}

// Form data interface
export interface FormData {
    amount: number;
    start_date?: string;
    end_date?: string;
    period?: number;
    cdb_rate?: number;
    lci_rate?: number;
    lca_rate?: number;
    ipca_spread?: number;
    selic_spread?: number;
    cdi_percentage?: number;
    lci_cdi_percentage?: number;
    lca_cdi_percentage?: number;
    lci_ipca_spread?: number;
    lca_ipca_spread?: number;
    cdb_ipca_spread?: number;
    include_poupanca?: boolean;
    include_btc?: boolean;
}
