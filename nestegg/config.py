"""
Configuration module for the NestEgg application.
"""

import logging
from typing import Any

from .models import InvestmentType


# Configure logging
def setup_logging(debug: bool = False) -> None:
    """
    Configure logging for the application.

    Args:
        debug: Whether to enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


# Investment type descriptions
INVESTMENT_DESCRIPTIONS: dict[InvestmentType, str] = {
    InvestmentType.POUPANCA: ("Poupança - Tax-free savings account with yield based on SELIC rate"),
    InvestmentType.SELIC: ("SELIC Treasury Bonds - Government bonds yielding 100% of SELIC rate"),
    InvestmentType.CDB: ("CDB (Certificado de Depósito Bancário) - " "Bank deposit certificate with fixed rate"),
    InvestmentType.LCI: ("LCI (Letra de Crédito Imobiliário) - Real estate credit note, tax-free"),
    InvestmentType.LCA: ("LCA (Letra de Crédito do Agronegócio) - " "Agribusiness credit note, tax-free"),
    InvestmentType.IPCA: ("IPCA - Investment indexed to Brazilian inflation index"),
    InvestmentType.CDI: (
        "CDI (Certificado de Depósito Interbancário) - "
        "Interbank deposit rate used as a reference for many investments"
    ),
    InvestmentType.BTC: ("Bitcoin (BTC) - Cryptocurrency with user-specified annual growth rate"),
}

# API configuration
API_CONFIG: dict[str, Any] = {
    "title": "NestEgg API",
    "description": """
    NestEgg is a FastAPI application for comparing Brazilian investment indexes.

    The API provides:
    * Investment calculations for CDB, LCI, LCA, SELIC, and Poupança
    * Tax calculations for different investment types
    * Performance comparison between investment types
    """,
    "version": "0.1.0",
    "prefix": "/api/v1",
}

# CORS configuration
CORS_CONFIG: dict[str, Any] = {
    "allow_origins": ["*"],  # In production, replace with specific origins
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

# BCB API configuration
# Series codes for the Brazilian Central Bank API
BCB_SERIES_CODES = {
    "SELIC": "11",  # BCB series code for SELIC rate
    "CDI": "12",  # BCB series code for CDI rate
    "IPCA": "433",  # BCB series code for IPCA (inflation)
    "POUPANCA": "25",  # BCB series code for Poupança savings rate
}

# Rate calculation constants
BCB_RATE_CONSTANTS = {
    # Brazil standard for daily-to-annual rate conversion
    "BUSINESS_DAYS_IN_YEAR": 252,
    # Rate validation thresholds
    "SELIC_MIN_EXPECTED": 0.05,  # 5% minimum expected annual SELIC rate
    "SELIC_MAX_EXPECTED": 0.20,  # 20% maximum expected annual SELIC rate
    # Poupança calculation constants (based on BCB rules)
    "POUPANCA_SELIC_THRESHOLD": 0.085,  # 8.5% SELIC threshold for calculation method
    "POUPANCA_MONTHLY_RATE": 0.005,  # 0.5% monthly when SELIC > threshold
    "POUPANCA_SELIC_FACTOR": 0.7,  # 70% of SELIC when SELIC <= threshold
    # API request parameters
    "MAX_DAILY_RANGE": 3650,  # 10 years in days - maximum range for historical data
    "DEFAULT_RANGE_DAYS": 30,  # Default range for rate requests
}
