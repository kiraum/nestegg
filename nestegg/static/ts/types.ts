// Investment types enumeration
export enum InvestmentType {
    CDB = "cdb",
    LCI = "lci",
    LCA = "lca",
    SELIC = "selic",
    POUPANCA = "poupanca",
    IPCA = "ipca",
    CDI = "cdi",
    BTC = "btc",
    LCI_CDI = "lci_cdi",
    LCA_CDI = "lca_cdi",
    LCI_IPCA = "lci_ipca",
    LCA_IPCA = "lca_ipca"
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
    start_date: string;
    end_date: string;
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
    include_poupanca?: boolean;
    include_selic?: boolean;
    include_cdi?: boolean;
    include_btc?: boolean;
}
