# NestEgg - Brazilian Investment Index Comparison Tool

A FastAPI application that helps you compare different Brazilian investment indexes, considering taxes and investment periods.

## Features

- Compare returns between different investment types:
  - Poupança
  - SELIC Treasury Bonds
  - CDB (Certificado de Depósito Bancário)
  - LCI (Letra de Crédito Imobiliário)
  - LCA (Letra de Crédito do Agronegócio)
  - IPCA (Inflation-indexed investments)
  - CDI (Certificado de Depósito Interbancário)
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
     "cdb_rate": 12.5,
     "period_years": 0.82
   }
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

Calculate investment returns for different Brazilian investment types.

Request body:
```json
{
  "investment_type": "cdb|poupanca|selic|lci|lca",
  "amount": float,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "cdb_rate": float (optional, required only for CDB),
  "period_years": float (investment period in years)
}
```

Response:
```json
{
  "gross_profit": 1000.0,
  "tax_amount": 150.0,
  "net_profit": 850.0,
  "effective_rate": 8.5
}
```

## Data Sources

The application uses the Brazilian Central Bank API (BCB) to fetch current rates for:
- SELIC rate
- CDI rate
- IPCA (inflation) rate

## License

MIT License
