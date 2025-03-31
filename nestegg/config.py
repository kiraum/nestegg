"""
Configuration module for the NestEgg application.
"""

import logging
from typing import Any

from .models import InvestmentType


# Configure logging
def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.DEBUG,
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
