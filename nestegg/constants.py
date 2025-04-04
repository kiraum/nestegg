"""
Shared constants for the NestEgg application.
"""

from .models import InvestmentType

# Tax-free investment types
TAX_FREE_INVESTMENTS = (
    InvestmentType.POUPANCA,
    InvestmentType.LCI,
    InvestmentType.LCA,
    InvestmentType.LCI_CDI,
    InvestmentType.LCA_CDI,
    InvestmentType.LCI_IPCA,
    InvestmentType.LCA_IPCA,
)

# FGC guaranteed investment types
FGC_GUARANTEED_INVESTMENTS = (
    InvestmentType.CDB,
    InvestmentType.CDB_CDI,  # CDB with CDI indexation
    InvestmentType.CDB_IPCA,  # CDB with IPCA indexation
    InvestmentType.LCI,
    InvestmentType.LCA,
    InvestmentType.LCI_CDI,
    InvestmentType.LCA_CDI,
    InvestmentType.LCI_IPCA,
    InvestmentType.LCA_IPCA,
    InvestmentType.POUPANCA,
)

# Government guaranteed investment types
GOVT_GUARANTEED_INVESTMENTS = (
    InvestmentType.SELIC,
    InvestmentType.IPCA,
)
