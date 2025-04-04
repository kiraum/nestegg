"""
Data models for the NestEgg application.
"""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CaseInsensitiveEnum(str, Enum):
    """Case insensitive enum that converts values to lowercase before validation."""

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            lower_value = value.lower()
            for member in cls:
                if member.value.lower() == lower_value:
                    return member
        return None


class InvestmentType(CaseInsensitiveEnum):
    """Types of investment available for simulation."""

    CDB = "cdb"
    LCI = "lci"
    LCA = "lca"
    SELIC = "selic"
    POUPANCA = "poupanca"
    IPCA = "ipca"
    CDI = "cdi"
    BTC = "btc"
    LCI_CDI = "lci_cdi"
    LCA_CDI = "lca_cdi"
    LCI_IPCA = "lci_ipca"
    LCA_IPCA = "lca_ipca"


class InvestmentRequest(BaseModel):
    """Request model for investment calculation."""

    investment_type: InvestmentType
    initial_amount: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rate: Optional[float] = None
    cdb_rate: Optional[float] = None
    lci_rate: Optional[float] = None
    lca_rate: Optional[float] = None
    ipca_spread: Optional[float] = 0.0  # Spread percentage added to IPCA rate (e.g., 5.0 for IPCA+5%)
    selic_spread: Optional[float] = 0.0  # Spread percentage added to SELIC rate (e.g., 3.0 for SELIC+3%)
    cdi_percentage: Optional[float] = 100.0  # Percentage of CDI (e.g., 109.0 for 109% of CDI)
    compare: bool = False

    @field_validator("initial_amount")
    @classmethod
    def validate_initial_amount(cls, v):
        """Validate the initial amount is positive."""
        if v <= 0:
            raise ValueError("Initial amount must be positive")
        return v

    @field_validator(
        "rate",
        "cdb_rate",
        "lci_rate",
        "lca_rate",
        "ipca_spread",
        "selic_spread",
        "cdi_percentage",
    )
    @classmethod
    def validate_rate(cls, v, info):
        """Validate the rate is positive if provided."""
        if v is not None:
            field_name = info.field_name
            # For spread parameters, allow zero values
            if field_name in ("ipca_spread", "selic_spread") and v < 0:
                raise ValueError(f"{field_name} must be non-negative if provided")
            # For all other rate parameters, require positive values
            if field_name not in ("ipca_spread", "selic_spread") and v <= 0:
                raise ValueError(f"{field_name} must be positive if provided")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v, info):
        """Validate end_date is after start_date if both are provided."""
        if "start_date" in info.data and info.data["start_date"] and v:
            if info.data["start_date"] >= v:
                raise ValueError("End date must be after start date")
        return v

    @property
    def period_years(self) -> float:
        """Calculate investment period in years from start and end dates."""
        if self.start_date is None or self.end_date is None:
            raise ValueError("Both start_date and end_date must be provided to calculate period_years")
        days = (self.end_date - self.start_date).days
        return days / 365


class FGCCoverage(BaseModel):
    """Model for FGC (Fundo Garantidor de Créditos) coverage information."""

    is_covered: bool = Field(..., description="Whether the investment is covered by FGC")
    covered_amount: float = Field(..., description="Amount covered by the FGC guarantee")
    uncovered_amount: float = Field(..., description="Amount not covered by the FGC guarantee")
    coverage_percentage: float = Field(..., description="Percentage of the investment covered by FGC")
    limit_per_institution: Optional[float] = Field(None, description="FGC coverage limit per financial institution")
    total_coverage_limit: Optional[float] = Field(None, description="Total FGC coverage limit across institutions")
    description: str = Field(..., description="Human-readable description of the FGC coverage")


class TaxInfo(BaseModel):
    """Model for tax information."""

    tax_rate_percentage: float = Field(..., description="Tax rate as a percentage")
    tax_amount: float = Field(..., description="Amount of tax applied")
    is_tax_free: bool = Field(..., description="Whether this investment is tax-free")
    tax_period_days: int = Field(..., description="Period in days used for tax calculation")
    tax_period_description: str = Field(..., description="Human-readable description of the tax period")


class InvestmentResponse(BaseModel):
    """Response model for investment comparison."""

    investment_type: InvestmentType
    initial_amount: float
    final_amount: float
    gross_profit: float
    net_profit: float
    tax_amount: float
    effective_rate: float
    start_date: date
    end_date: date
    rate: float
    tax_info: TaxInfo
    fgc_coverage: FGCCoverage
