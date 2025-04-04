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
        initial_amount: Optional[float] = None,
    ) -> float:
        """
        Calculate tax amount for investment returns.

        Args:
            investment_type: Type of investment
            gross_profit: Gross profit before taxes
            investment_period_days: Number of days the investment is held
            cdb_rate: CDB rate (required only for CDB investments)
            initial_amount: Initial investment amount (required for BTC calculations)

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
            InvestmentType.LCI_CDI,
            InvestmentType.LCA_CDI,
            InvestmentType.LCI_IPCA,
            InvestmentType.LCA_IPCA,
        ):
            logger.debug("No tax for %s investment", investment_type)
            return 0.0

        # Bitcoin - special tax rules in Brazil
        # Exempt if total monthly sales <= R$ 35,000
        # Otherwise, 15% tax on gains
        if investment_type == InvestmentType.BTC:
            if initial_amount is None:
                raise ValueError("Initial amount is required for Bitcoin tax calculations")

            # No tax on capital losses
            if gross_profit <= 0:
                logger.debug("Bitcoin has a capital loss - no tax applies")
                return 0.0

            # The total sale amount is the final value (initial + profit)
            sale_amount = initial_amount + gross_profit

            if sale_amount <= 35000:
                logger.debug(
                    "Bitcoin sale amount (R$ %.2f) below R$ 35,000 monthly threshold - tax exempt",
                    sale_amount,
                )
                return 0.0

            # Get tax rate based on profit amount
            tax_rate = TaxCalculator._get_btc_tax_rate(gross_profit)
            tax_amount = gross_profit * tax_rate
            logger.debug(
                "Bitcoin sale amount (R$ %.2f) exceeds R$ 35,000 monthly threshold - %.1f%% tax: R$ %.2f",
                sale_amount,
                tax_rate * 100,
                tax_amount,
            )
            return tax_amount

        # CDB and CDI taxes
        if investment_type in (InvestmentType.CDB, InvestmentType.CDI):
            if investment_type == InvestmentType.CDB and not cdb_rate:
                raise ValueError("CDB rate is required for CDB investments")

            # IOF for up to 30 days
            if investment_period_days <= 30:
                # IOF decreases from 96% to 0% over 30 days
                # Formula: IOF rate = (30 - days) / 30 * 96%
                days_remaining = max(0, 30 - investment_period_days)
                iof_rate = (days_remaining / 30) * 0.96
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

    def calculate_tax_rate(
        self,
        investment_type: InvestmentType,
        days: int,
        initial_amount: Optional[float] = None,
        gross_profit: Optional[float] = None,
    ) -> float:
        """
        Calculate the tax rate based on investment type and holding period.

        Args:
            investment_type: Type of investment
            days: Number of days the investment is held
            initial_amount: Initial investment amount (needed for BTC calculations)
            gross_profit: Gross profit (needed for BTC calculations to determine sale amount)

        Returns:
            Tax rate as a decimal (e.g., 0.15 for 15%)
        """
        # Tax-free investments
        if investment_type in (
            InvestmentType.POUPANCA,
            InvestmentType.LCI,
            InvestmentType.LCA,
            InvestmentType.LCI_CDI,
            InvestmentType.LCA_CDI,
            InvestmentType.LCI_IPCA,
            InvestmentType.LCA_IPCA,
        ):
            return 0.0

        # Bitcoin - special tax rules in Brazil
        # Exempt if total monthly sales <= R$ 35,000
        # Otherwise, progressive tax rates based on profit amount
        if investment_type == InvestmentType.BTC:
            # No tax on capital losses
            if gross_profit is not None and gross_profit <= 0:
                return 0.0

            if initial_amount is None:
                # Default to lowest taxable rate if no amount info
                return 0.15

            # Calculate sale amount if we have both initial_amount and gross_profit
            if gross_profit is not None:
                sale_amount = initial_amount + gross_profit
                if sale_amount <= 35000:
                    return 0.0

                # For sales > R$ 35,000, get tax rate based on profit
                return self._get_btc_tax_rate(gross_profit)

            # Default if we can't determine profit amount
            return 0.15

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

    @staticmethod
    def _get_btc_tax_rate(gross_profit: float) -> float:
        """
        Get the appropriate Bitcoin tax rate based on profit amount.

        Args:
            gross_profit: The gross profit amount from the Bitcoin investment

        Returns:
            The applicable tax rate as a decimal
        """
        if gross_profit <= 5_000_000:  # Up to R$ 5 million
            return 0.15
        if gross_profit <= 10_000_000:  # R$ 5M to R$ 10M
            return 0.175
        if gross_profit <= 30_000_000:  # R$ 10M to R$ 30M
            return 0.20
        # Above R$ 30M
        return 0.225
