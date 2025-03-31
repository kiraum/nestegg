# NestEgg - Brazilian Investment Index Comparison Tool

A FastAPI application that helps you compare different Brazilian investment indexes, considering taxes and investment periods.

## Features

- Compare returns between different investment types:
  - Poupança (tax-free savings account)
  - SELIC Treasury Bonds (with optional spread: SELIC+X%)
  - CDB (Certificado de Depósito Bancário)
  - LCI (Letra de Crédito Imobiliário, tax-free)
  - LCA (Letra de Crédito do Agronegócio, tax-free)
  - IPCA (Inflation-indexed investments with optional spread: IPCA+X%)
  - CDI (Certificado de Depósito Interbancário with optional percentage: X% of CDI)
- Automatic tax calculation based on investment type and period
- Real-time data from Brazilian Central Bank API
- Easy-to-use REST API

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

## Usage

1. Start the server:
   ```bash
   uvicorn nestegg.main:app --reload
   ```

2. Open your browser and navigate to `http://localhost:8000/docs` to access the interactive API documentation

3. Make a POST request to `/api/v1/calculate` with a JSON body like:
   ```json
   {
     "investment_type": "cdb",
     "amount": 10000.0,
     "start_date": "2024-03-01",
     "end_date": "2024-12-31",
     "cdb_rate": 12.5
   }
   ```

4. Or compare multiple investments at once with:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/compare?amount=10000&start_date=2025-03-31&end_date=2026-03-31&cdb_rate=14.5&lci_rate=12.0&lca_rate=11.5&ipca_spread=5.5&selic_spread=2.0&cdi_percentage=109.0"
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
- `investment_type`: Type of investment (`cdb`, `poupanca`, `selic`, `lci`, `lca`, `ipca`, `cdi`)
- `amount`: Initial investment amount
- `start_date`: Start date (format: `YYYY-MM-DD`)
- `end_date`: End date (format: `YYYY-MM-DD`)
- `cdb_rate`: CDB rate as percentage (required for CDB investments)
- `lci_rate`: LCI rate as percentage (required for LCI investments)
- `lca_rate`: LCA rate as percentage (required for LCA investments)
- `ipca_spread`: IPCA spread in percentage points (optional, default: 0)
- `selic_spread`: SELIC spread in percentage points (optional, default: 0)
- `cdi_percentage`: CDI percentage (optional, default: 100.0)

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

### POST /api/v1/compare

Compare returns between different investment types and provide recommendations.

Request parameters:
- `amount`: Initial investment amount
- `start_date`: Start date (format: `YYYY-MM-DD`)
- `end_date`: End date (format: `YYYY-MM-DD`)
- `cdb_rate`: CDB rate as percentage (optional)
- `lci_rate`: LCI rate as percentage (optional)
- `lca_rate`: LCA rate as percentage (optional)
- `ipca_spread`: IPCA spread in percentage points (optional, default: 0)
- `selic_spread`: SELIC spread in percentage points (optional, default: 0)
- `cdi_percentage`: CDI percentage (optional, default: 100.0)

Response:
```json
[
  {
    "type": "LCI",
    "rate": 12.0,
    "effective_rate": 12.0,
    "gross_profit": 1200.0,
    "net_profit": 1200.0,
    "tax_amount": 0.0,
    "final_amount": 11200.0,
    "tax_free": true,
    "tax_info": {
      "tax_rate_percentage": 0.0,
      "tax_amount": 0.0,
      "is_tax_free": true,
      "tax_period_days": 365,
      "tax_period_description": "181 to 360 days (20% tax)"
    },
    "recommendation": "Best option among compared investments"
  },
  {
    "type": "CDB",
    "rate": 14.5,
    "effective_rate": 11.6,
    "gross_profit": 1450.0,
    "net_profit": 1160.0,
    "tax_amount": 290.0,
    "final_amount": 11160.0,
    "tax_free": false,
    "tax_info": {
      "tax_rate_percentage": 20.0,
      "tax_amount": 290.0,
      "is_tax_free": false,
      "tax_period_days": 365,
      "tax_period_description": "181 to 360 days (20% tax)"
    },
    "recommendation": "0.40% lower than LCI"
  }
]
```

## Example curl Commands

Here are some example curl commands for using the API:

### Calculate a single CDB investment
```bash
curl -X POST "http://localhost:8000/api/v1/calculate?investment_type=cdb&amount=10000&start_date=2025-03-31&end_date=2026-03-31&cdb_rate=14.5"
```

### Compare multiple investments with custom parameters
```bash
curl -X POST "http://localhost:8000/api/v1/compare?amount=10000&start_date=2025-03-31&end_date=2026-03-31&cdb_rate=14.5&lci_rate=12.0&lca_rate=11.5&ipca_spread=5.5&selic_spread=2.0&cdi_percentage=109.0"
```

## Data Sources

The application uses the Brazilian Central Bank API (BCB) to fetch current rates for:
- SELIC rate
- CDI rate
- IPCA (inflation) rate

## License

MIT License
