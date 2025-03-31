"""
Tax calculator module for investment returns.
"""

import logging
from typing import Optional

from .models import InvestmentType

logger = logging.getLogger(__name__)


class TaxCalculator:
    """Calculator for investment taxes."""

    # Tax rates for different investment periods
    CDB_TAX_RATES = {
        180: 0.225,  # 22.5% for up to 180 days
        360: 0.20,  # 20% for up to 360 days
        720: 0.175,  # 17.5% for up to 720 days
        float("inf"): 0.15,  # 15% for more than 720 days
    }

    @staticmethod
    def calculate_tax(
        investment_type: InvestmentType,
        gross_profit: float,
        investment_period_days: int,
        cdb_rate: Optional[float] = None,
    ) -> float:
        """
        Calculate tax amount for investment returns.

        Args:
            investment_type: Type of investment
            gross_profit: Gross profit before taxes
            investment_period_days: Number of days the investment is held
            cdb_rate: CDB rate (required only for CDB investments)

        Returns:
            Tax amount to be deducted from gross profit

        Raises:
            ValueError: If parameters are invalid
        """
        logger.debug(
            "Calculating tax for %s investment with gross profit R$ %.2f over %d days",
            investment_type,
            gross_profit,
            investment_period_days,
        )

        # Tax-free investments
        if investment_type in (
            InvestmentType.POUPANCA,
            InvestmentType.LCI,
            InvestmentType.LCA,
        ):
            logger.debug("No tax for %s investment", investment_type)
            return 0.0

        # CDB and CDI taxes
        if investment_type in (InvestmentType.CDB, InvestmentType.CDI):
            if investment_type == InvestmentType.CDB and not cdb_rate:
                raise ValueError("CDB rate is required for CDB investments")

            # IOF for up to 30 days
            if investment_period_days <= 30:
                iof_rate = 0.96 - (investment_period_days * 0.032)  # Linear reduction
                tax_amount = gross_profit * iof_rate
                logger.debug("Applied IOF rate: %.2f%%", iof_rate * 100)
                return tax_amount

            # Find the appropriate tax rate based on investment period
            for days, rate in TaxCalculator.CDB_TAX_RATES.items():
                if investment_period_days <= days:
                    tax_amount = gross_profit * rate
                    logger.debug("Applied tax rate: %.2f%%", rate * 100)
                    return tax_amount

            # This should never happen due to float('inf') in the dictionary
            raise ValueError("Invalid investment period")

        # SELIC and IPCA taxes
        if investment_type in (InvestmentType.SELIC, InvestmentType.IPCA):
            # Find the appropriate tax rate based on investment period
            for days, rate in TaxCalculator.CDB_TAX_RATES.items():
                if investment_period_days <= days:
                    tax_amount = gross_profit * rate
                    logger.debug("Applied tax rate: %.2f%%", rate * 100)
                    return tax_amount

            # This should never happen due to float('inf') in the dictionary
            raise ValueError("Invalid investment period")

        raise ValueError(f"Unsupported investment type: {investment_type}")

    def calculate_tax_rate(self, investment_type: InvestmentType, days: int) -> float:
        """
        Calculate the tax rate based on investment type and holding period.

        Args:
            investment_type: Type of investment
            days: Number of days the investment is held

        Returns:
            Tax rate as a decimal (e.g., 0.15 for 15%)
        """
        # Tax-free investments
        if investment_type in (
            InvestmentType.POUPANCA,
            InvestmentType.LCI,
            InvestmentType.LCA,
        ):
            return 0.0

        # CDB, SELIC, IPCA, and CDI taxes
        if investment_type in (
            InvestmentType.CDB,
            InvestmentType.SELIC,
            InvestmentType.IPCA,
            InvestmentType.CDI,
        ):
            for period_days, rate in self.CDB_TAX_RATES.items():
                if days <= period_days:
                    return rate

            # This should never happen due to float('inf') in the dictionary
            raise ValueError("Invalid investment period")

        raise ValueError(f"Unsupported investment type: {investment_type}")
