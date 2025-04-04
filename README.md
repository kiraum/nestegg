# NestEgg - Brazilian Investment Index Comparison Tool

A FastAPI application that helps you compare different Brazilian investment indexes, considering taxes and investment periods.

## Features

- Compare returns between different investment types:
  - Poupança (tax-free savings account)
  - SELIC Treasury Bonds (with optional spread: SELIC+X%)
  - CDB (Certificado de Depósito Bancário)
    - Fixed-rate CDB (Prefixado)
    - CDI-based CDB (X% of CDI)
    - IPCA-based CDB (IPCA+X%)
  - LCI (Letra de Crédito Imobiliário, tax-free)
    - Fixed-rate LCI (Prefixado)
    - CDI-based LCI (X% of CDI)
    - IPCA-based LCI (IPCA+X%)
  - LCA (Letra de Crédito do Agronegócio, tax-free)
    - Fixed-rate LCA (Prefixado)
    - CDI-based LCA (X% of CDI)
    - IPCA-based LCA (IPCA+X%)
  - IPCA (Inflation-indexed investments with optional spread: IPCA+X%)
  - CDI (Certificado de Depósito Interbancário with optional percentage: X% of CDI)
  - Bitcoin (BTC) with real market prices from CryptoCompare API
- Automatic tax calculation based on investment type and period
- Historical data from Brazilian Central Bank API
- Future projections based on historical volatility and trends
- Dynamic IPCA data retrieval with multi-level fallback strategies
- Bitcoin price data from CryptoCompare API
- User-friendly interface with Today buttons for date selection
- Convenient form reset with New Query button
- Robust error handling and logging
- Easy-to-use REST API

<p align="center">
  <img src="https://raw.githubusercontent.com/kiraum/nestegg/main/nestegg/static/img/nestegg.png" alt="NesteEgg Logo" width="300"/>
</p>

## Installation

1. Make sure you have Python 3.9+ installed
2. Install `uv` (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Clone this repository
4. Install dependencies:
   ```bash
   uv pip install -e .
   ```

## Building the UI

The NestEgg UI is built with TypeScript and requires Node.js to compile the TypeScript code to JavaScript.

1. Make sure you have Node.js installed (version 16+)

2. Build the TypeScript files:
   ```bash
   cd nestegg/static
   ./build.sh
   ```

## Usage

1. Start the server:
   ```bash
   uvicorn nestegg.main:app --reload --port 8001
   ```

2. Access the UI by navigating to `http://localhost:8001` in your browser

3. Or access the API documentation at `http://localhost:8001/docs` to use the interactive API

4. Make a POST request to `/api/v1/calculate` with a JSON body like:
   ```json
   {
     "investment_type": "cdb",
     "amount": 10000.0,
     "start_date": "2024-03-01",
     "end_date": "2024-12-31",
     "cdb_rate": 12.5
   }
   ```

5. Or compare multiple investments at once with:
   ```bash
   curl -X GET "http://localhost:8001/api/v1/compare?amount=10000&period=1&cdb_rate=14.5&lci_rate=12.0&lca_rate=11.5&ipca_spread=5.5&selic_spread=2.0&cdi_percentage=109.0"
   ```

## API Documentation

The API provides the following endpoints:

### GET /api/v1/investment-types

List all supported investment types with their descriptions.

Response:
```json
[
  {
    "id": "poupanca",
    "name": "Poupanca",
    "description": "Poupança - Tax-free savings account with yield based on SELIC rate"
  },
  {
    "id": "selic",
    "name": "Selic",
    "description": "SELIC Treasury Bonds - Government bonds yielding 100% of SELIC rate"
  }
]
```

### POST /api/v1/calculate

Calculate investment returns for a single Brazilian investment type.

Request parameters:
- `investment_type`: Type of investment (`cdb`, `poupanca`, `selic`, `lci`, `lca`, `ipca`, `cdi`, `btc`, `lci_cdi`, `lca_cdi`, `lci_ipca`, `lca_ipca`, `cdb_ipca`)
- `amount`: Initial investment amount
- `start_date`: Start date (format: `YYYY-MM-DD`)
- `end_date`: End date (format: `YYYY-MM-DD`)
- `cdb_rate`: CDB rate as percentage (required for CDB investments)
- `lci_rate`: LCI rate as percentage (required for fixed-rate LCI investments)
- `lca_rate`: LCA rate as percentage (required for fixed-rate LCA investments)
- `ipca_spread`: IPCA spread in percentage points (optional, default: 0, required for IPCA, LCI_IPCA, LCA_IPCA, CDB_IPCA)
- `selic_spread`: SELIC spread in percentage points (optional, default: 0)
- `cdi_percentage`: CDI percentage (optional, default: 100.0, required for CDI, LCI_CDI, LCA_CDI)

Response:
```json
{
  "investment_type": "cdb",
  "initial_amount": 10000.0,
  "final_amount": 11000.0,
  "gross_profit": 1200.0,
  "net_profit": 1000.0,
  "tax_amount": 200.0,
  "effective_rate": 10.0,
  "start_date": "2024-03-01",
  "end_date": "2024-12-31",
  "rate": 12.5,
  "tax_info": {
    "tax_rate_percentage": 17.5,
    "tax_amount": 200.0,
    "is_tax_free": false,
    "tax_period_days": 305,
    "tax_period_description": "181 to 360 days (20% tax)"
  }
}
```

### GET /api/v1/compare

Compare returns between different investment types and provide recommendations.

Request parameters:
- `amount`: Initial investment amount
- `period`: Investment period in years (optional if start_date and end_date are provided)
- `start_date`: Start date (format: `YYYY-MM-DD`, optional if period is provided)
- `end_date`: End date (format: `YYYY-MM-DD`, optional if period is provided)
- `cdb_rate`: CDB rate as percentage (optional)
- `lci_rate`: LCI rate as percentage (optional)
- `lca_rate`: LCA rate as percentage (optional)
- `ipca_spread`: IPCA spread in percentage points (optional)
- `selic_spread`: SELIC spread in percentage points (optional)
- `cdi_percentage`: CDI percentage (optional)
- `lci_cdi_percentage`: LCI CDI percentage (optional)
- `lca_cdi_percentage`: LCA CDI percentage (optional)
- `lci_ipca_spread`: LCI IPCA spread (optional)
- `lca_ipca_spread`: LCA IPCA spread (optional)
- `cdb_ipca_spread`: CDB IPCA spread (optional)
- `include_poupanca`: Whether to include Poupança in comparison (optional, default: false)
- `include_selic`: Whether to include base SELIC in comparison (optional, default: false, only needed if not providing selic_spread)
- `include_btc`: Whether to include Bitcoin in comparison (optional, default: false)
- `include_cdb_ipca`: Whether to include CDB_IPCA with default spread (optional, default: false, only needed if not providing cdb_ipca_spread)

The comparison will only include investment types that are explicitly requested through parameters.

Response:
```json
[
  {
    "type": "LCI 95.00% CDI",
    "rate": 11.40,
    "effective_rate": 5.62,
    "gross_profit": 561.85,
    "net_profit": 561.85,
    "tax_amount": 0.0,
    "final_amount": 10561.85,
    "tax_free": true,
    "recommendation": "Best option among compared investments"
  },
  {
    "type": "LCA 90.00% CDI",
    "rate": 10.80,
    "effective_rate": 5.31,
    "gross_profit": 531.45,
    "net_profit": 531.45,
    "tax_amount": 0.0,
    "final_amount": 10531.45,
    "tax_free": true,
    "recommendation": "0.31% lower than LCI 95.00% CDI"
  },
  {
    "type": "CDB Prefixado 14.50%",
    "rate": 14.50,
    "effective_rate": 5.30,
    "gross_profit": 725.00,
    "net_profit": 530.47,
    "tax_amount": 194.53,
    "final_amount": 10530.47,
    "tax_free": false,
    "recommendation": "0.32% lower than LCI 95.00% CDI"
  },
  {
    "type": "CDB 109.00% CDI",
    "rate": 13.08,
    "effective_rate": 4.84,
    "gross_profit": 654.00,
    "net_profit": 484.59,
    "tax_amount": 169.41,
    "final_amount": 10484.59,
    "tax_free": false,
    "recommendation": "0.78% lower than LCI 95.00% CDI"
  },
  {
    "type": "Tesouro SELIC+2.00%",
    "rate": 14.00,
    "effective_rate": 4.82,
    "gross_profit": 700.00,
    "net_profit": 482.30,
    "tax_amount": 217.70,
    "final_amount": 10482.30,
    "tax_free": false,
    "recommendation": "0.80% lower than LCI 95.00% CDI"
  }
]
```

- A sorted list of investment comparisons, with the best performing investments first
- Includes tax calculations and effective rates for each investment type
- Provides a recommendation highlighting the best option
- Clearly marks calculations for historical data vs. projected future returns

## Example curl Commands

Here are some example curl commands for using the API:

### Calculate a single CDB investment
```bash
curl -X POST "http://localhost:8001/api/v1/calculate?investment_type=cdb&amount=10000&start_date=2024-01-01&end_date=2024-12-31&cdb_rate=14.5"
```

### Compare multiple investments with custom parameters (using period)
```bash
curl -X GET "http://localhost:8001/api/v1/compare?amount=10000&period=1&cdb_rate=14.5&lci_rate=12.0&lca_rate=11.5&ipca_spread=5.5&selic_spread=2.0&cdi_percentage=109.0"
```

### Compare multiple investments with custom parameters (using dates)
```bash
curl -X GET "http://localhost:8001/api/v1/compare?amount=10000&start_date=2024-01-01&end_date=2024-12-31&cdb_rate=14.5&lci_rate=12.0&lca_rate=11.5&ipca_spread=5.5&selic_spread=2.0&cdi_percentage=109.0"
```

### Compare investments with different LCI/LCA variants
```bash
curl -X GET "http://localhost:8001/api/v1/compare?amount=10000&period=1&cdb_rate=14.5&lci_rate=12.0&lca_rate=11.5&ipca_spread=5.5&selic_spread=2.0&cdi_percentage=109.0&lci_cdi_percentage=95.0&lca_cdi_percentage=90.0&lci_ipca_spread=4.5&lca_ipca_spread=4.0"
```

### Compare investments with CDB IPCA and other specific types
```bash
curl -X GET "http://localhost:8001/api/v1/compare?amount=10000&period=1&lci_rate=13.5&lci_cdi_percentage=94.0&cdb_ipca_spread=5.5&include_poupanca=true&include_btc=true"
```

### Compare investments with future dates (projections)
```bash
curl -X GET "http://localhost:8001/api/v1/compare?amount=10000&start_date=2025-01-01&end_date=2025-12-31&cdb_rate=14.5&lci_rate=12.0&lca_rate=11.5&ipca_spread=5.5&selic_spread=2.0&cdi_percentage=109.0"
```

## Data Sources

The application uses the following data sources:

1. Brazilian Central Bank API (BCB)
   - SELIC rate (BCB series code 11)
   - CDI rate (BCB series code 12)
   - IPCA (inflation) rate (BCB series code 433)
   - Poupança rate (BCB series code 25)

2. CryptoCompare API
   - Current and historical Bitcoin prices in BRL
   - Future Bitcoin price projections based on historical volatility

For future dates, the application uses sophisticated projections based on historical data patterns and volatility. These projections are clearly marked in the results. For IPCA, the system employs a multi-level dynamic fallback strategy using recent historical data.

## UI Features

The web interface provides several user-friendly features:

- **Today Buttons**: Next to date inputs, allowing you to quickly set a date to today
- **New Query Button**: Resets all selections and results to start fresh
- **Responsive Design**: Works well on desktop and mobile devices
- **Dynamic Investment Selection**: Only selected investment types are included in comparisons
- **Interactive Results**: Clear visualization of investment performance

## Changelog

See [CHANGELOG.md](https://github.com/kiraum/nestegg/blob/main/CHANGELOG.md) for a detailed history of changes.

## License

See [LICENSE](https://raw.githubusercontent.com/kiraum/nestegg/refs/heads/main/LICENSE) file for details.
