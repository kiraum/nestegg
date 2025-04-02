"""
Investment calculator module.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from .external_api import BCBApiClient, CryptoApiClient
from .models import InvestmentRequest, InvestmentType
from .tax_calculator import TaxCalculator

logger = logging.getLogger(__name__)


class InvestmentCalculator:
    """Calculator for investment returns."""

    def __init__(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        crypto_client: CryptoApiClient | None = None,
    ):
        """
        Initialize the calculator.

        Args:
            start_date: Optional start date for testing
            end_date: Optional end date for testing
            crypto_client: Optional shared crypto client instance for consistent data
        """
        logger.debug("Initializing investment calculator")
        self.api_client = BCBApiClient(start_date=start_date, end_date=end_date)

        # Use provided crypto client or create a new one
        self.crypto_client = crypto_client or CryptoApiClient()
        if crypto_client:
            logger.debug("Using shared crypto client for consistent price data")
        else:
            logger.debug("Using new crypto client instance")

        self.tax_calculator = TaxCalculator()
        logger.debug("Using date range: %s to %s", start_date, end_date)

    async def close(self):
        """Close any resources used by the calculator."""
        logger.debug("Closing calculator resources")
        if hasattr(self, "api_client") and self.api_client is not None:
            await self.api_client.close()
            logger.debug("Closed API client")

        # Only close the crypto client if we created it (not if it was provided externally)
        if (
            hasattr(self, "crypto_client")
            and self.crypto_client is not None
            and not hasattr(self.crypto_client, "_is_shared")
        ):
            await self.crypto_client.close()
            logger.debug("Closed Crypto API client")

    async def compare_investments(
        self,
        initial_amount: float,
        period_years: float,
        cdb_rate: float | None = None,
        lci_rate: float | None = None,
        lca_rate: float | None = None,
        ipca_spread: float = 0.0,
        selic_spread: float = 0.0,
        cdi_percentage: float = 100.0,
        lci_cdi_percentage: float | None = None,
        lca_cdi_percentage: float | None = None,
        lci_ipca_spread: float | None = None,
        lca_ipca_spread: float | None = None,
        start_date_param: date | None = None,
        end_date_param: date | None = None,
    ) -> list[dict]:
        """
        Compare different investment types and provide recommendations.

        Args:
            initial_amount: Initial investment amount
            period_years: Investment period in years
            cdb_rate: Optional CDB rate to compare (if not provided, will use current market rate)
            lci_rate: Optional LCI rate to compare
            lca_rate: Optional LCA rate to compare
            ipca_spread: Optional spread to add to IPCA rate (in percentage points, e.g., 5.0 for IPCA+5%)
            selic_spread: Optional spread to add to SELIC rate (in percentage points, e.g., 3.0 for SELIC+3%)
            cdi_percentage: Optional percentage of CDI (e.g., 109.0 for 109% of CDI)
            lci_cdi_percentage: Optional percentage of CDI for LCI_CDI investment type
            lca_cdi_percentage: Optional percentage of CDI for LCA_CDI investment type
            lci_ipca_spread: Optional spread to add to IPCA for LCI_IPCA investment type
            lca_ipca_spread: Optional spread to add to IPCA for LCA_IPCA investment type
            start_date_param: Optional explicit start date (overrides calculation from period_years)
            end_date_param: Optional explicit end date (overrides calculation from period_years)

        Returns:
            List of dictionaries containing comparison results, sorted by effective rate
        """
        logger.debug("Starting investment comparison with parameters:")
        logger.debug("  initial_amount: R$ %.2f", initial_amount)
        logger.debug("  period_years: %.1f", period_years)
        logger.debug("  cdb_rate: %s", cdb_rate)
        logger.debug("  lci_rate: %s", lci_rate)
        logger.debug("  lca_rate: %s", lca_rate)
        logger.debug("  ipca_spread: %.2f%%", ipca_spread)
        logger.debug("  selic_spread: %.2f%%", selic_spread)
        logger.debug("  cdi_percentage: %.2f%%", cdi_percentage)
        logger.debug("  lci_cdi_percentage: %s", lci_cdi_percentage)
        logger.debug("  lca_cdi_percentage: %s", lca_cdi_percentage)
        logger.debug("  lci_ipca_spread: %s", lci_ipca_spread)
        logger.debug("  lca_ipca_spread: %s", lca_ipca_spread)
        logger.debug("  start_date_param: %s", start_date_param)
        logger.debug("  end_date_param: %s", end_date_param)

        # Determine the dates to use
        if start_date_param and end_date_param:
            # Use the provided dates directly
            start_date = start_date_param
            target_date = end_date_param
            logger.debug("Using provided date range: %s to %s", start_date, target_date)

            # Recalculate period_years based on the provided dates for consistency
            days = (target_date - start_date).days
            period_years = days / 365
            logger.debug("Recalculated period_years: %.2f (from %d days)", period_years, days)
        else:
            # Calculate target date based on period_years
            days = int(period_years * 365)

            # Use the actual date instead of hardcoded date
            start_date = date.today()

            target_date = start_date + timedelta(days=days)
            logger.debug("Using calculated date range: %s to %s", start_date, target_date)

        # Store dates in api_client for label generation
        self.api_client.start_date = start_date
        self.api_client.end_date = target_date
        today = date.today()

        # Determine if we're dealing with past, future or mixed data
        date_range_type = "historical"
        if target_date > today:
            if start_date <= today:
                date_range_type = "mixed historical/projected"
            else:
                date_range_type = "projected"
        logger.info(
            "Using %s data for date range: %s to %s",
            date_range_type,
            start_date,
            target_date,
        )

        # Create comparison results
        comparisons = []

        try:
            # Get current market rates for reference investments
            selic_rate = await self.api_client.get_selic_rate(target_date)
            logger.debug("Current SELIC rate: %.2f%%", selic_rate * 100)

            # Compare Poupança (always included)
            try:
                logger.debug("Calculating Poupança investment")
                poupanca_request = InvestmentRequest(
                    investment_type=InvestmentType.POUPANCA,
                    initial_amount=initial_amount,
                    start_date=start_date,
                    end_date=target_date,
                )
                poupanca_result = await self.calculate_investment(poupanca_request)
                poupanca_rate = await self.api_client.get_investment_rate(InvestmentType.POUPANCA, target_date)
                comparisons.append(
                    {
                        "type": "Poupança",
                        "rate": poupanca_rate * 100,
                        "effective_rate": poupanca_result["effective_rate"],
                        "gross_profit": poupanca_result["gross_profit"],
                        "net_profit": poupanca_result["net_profit"],
                        "tax_amount": poupanca_result["tax_amount"],
                        "final_amount": poupanca_result["final_amount"],
                        "tax_free": poupanca_result["tax_info"]["is_tax_free"],
                        "tax_info": poupanca_result["tax_info"],
                    }
                )
                logger.debug("Added Poupança to comparisons")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error calculating Poupança investment: %s", str(e))

            # Compare SELIC (always included)
            try:
                logger.debug("Calculating SELIC investment with spread: %.2f%%", selic_spread)
                selic_request = InvestmentRequest(
                    investment_type=InvestmentType.SELIC,
                    initial_amount=initial_amount,
                    start_date=start_date,
                    end_date=target_date,
                    selic_spread=selic_spread,
                )
                selic_result = await self.calculate_investment(selic_request)

                # Format the display name based on the spread
                selic_display = "SELIC" if selic_spread == 0 else f"Tesouro SELIC+{selic_spread:.2f}%"

                comparisons.append(
                    {
                        "type": selic_display,
                        "rate": selic_rate * 100 + selic_spread,  # Add spread to display rate
                        "effective_rate": selic_result["effective_rate"],
                        "gross_profit": selic_result["gross_profit"],
                        "net_profit": selic_result["net_profit"],
                        "tax_amount": selic_result["tax_amount"],
                        "final_amount": selic_result["final_amount"],
                        "tax_free": selic_result["tax_info"]["is_tax_free"],
                        "tax_info": selic_result["tax_info"],
                    }
                )
                logger.debug("Added SELIC to comparisons")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error calculating SELIC investment: %s", str(e), exc_info=True)

            # Compare IPCA (always included)
            try:
                logger.debug("Calculating IPCA investment with spread: %.2f%%", ipca_spread)
                ipca_request = InvestmentRequest(
                    investment_type=InvestmentType.IPCA,
                    initial_amount=initial_amount,
                    start_date=start_date,
                    end_date=target_date,
                    ipca_spread=ipca_spread,
                )
                ipca_result = await self.calculate_investment(ipca_request)
                ipca_rate = await self.api_client.get_investment_rate(InvestmentType.IPCA, target_date)

                # Format the display name based on the spread
                ipca_display = "IPCA" if ipca_spread == 0 else f"Tesouro IPCA+{ipca_spread:.2f}%"

                comparisons.append(
                    {
                        "type": ipca_display,
                        "rate": ipca_rate * 100 + ipca_spread,  # Add spread to display rate
                        "effective_rate": ipca_result["effective_rate"],
                        "gross_profit": ipca_result["gross_profit"],
                        "net_profit": ipca_result["net_profit"],
                        "tax_amount": ipca_result["tax_amount"],
                        "final_amount": ipca_result["final_amount"],
                        "tax_free": ipca_result["tax_info"]["is_tax_free"],
                        "tax_info": ipca_result["tax_info"],
                    }
                )
                logger.debug("Added IPCA to comparisons")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error calculating IPCA investment: %s", str(e), exc_info=True)

            # Compare CDI (always included)
            try:
                logger.debug("Calculating CDI investment with percentage: %.2f%%", cdi_percentage)
                cdi_request = InvestmentRequest(
                    investment_type=InvestmentType.CDI,
                    initial_amount=initial_amount,
                    start_date=start_date,
                    end_date=target_date,
                    cdi_percentage=cdi_percentage,
                )
                cdi_result = await self.calculate_investment(cdi_request)
                cdi_rate = await self.api_client.get_investment_rate(InvestmentType.CDI, target_date)

                # Format the display name based on the percentage
                cdi_display = "CDI" if cdi_percentage == 100.0 else f"CDB {cdi_percentage:.2f}% CDI"

                comparisons.append(
                    {
                        "type": cdi_display,
                        "rate": cdi_rate * 100 * (cdi_percentage / 100.0),  # Adjust rate by percentage
                        "effective_rate": cdi_result["effective_rate"],
                        "gross_profit": cdi_result["gross_profit"],
                        "net_profit": cdi_result["net_profit"],
                        "tax_amount": cdi_result["tax_amount"],
                        "final_amount": cdi_result["final_amount"],
                        "tax_free": cdi_result["tax_info"]["is_tax_free"],
                        "tax_info": cdi_result["tax_info"],
                    }
                )
                logger.debug("Added CDI to comparisons")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error calculating CDI investment: %s", str(e), exc_info=True)

            # Compare CDB (if rate provided)
            if cdb_rate is not None:
                try:
                    logger.debug("Calculating CDB investment with rate: %s%%", cdb_rate)
                    cdb_request = InvestmentRequest(
                        investment_type=InvestmentType.CDB,
                        initial_amount=initial_amount,
                        start_date=start_date,
                        end_date=target_date,
                        cdb_rate=cdb_rate,
                    )
                    cdb_result = await self.calculate_investment(cdb_request)
                    comparisons.append(
                        {
                            "type": "CDB Prefixado " + f"{cdb_rate:.2f}%",
                            "rate": cdb_rate,
                            "effective_rate": cdb_result["effective_rate"],
                            "gross_profit": cdb_result["gross_profit"],
                            "net_profit": cdb_result["net_profit"],
                            "tax_amount": cdb_result["tax_amount"],
                            "final_amount": cdb_result["final_amount"],
                            "tax_free": cdb_result["tax_info"]["is_tax_free"],
                            "tax_info": cdb_result["tax_info"],
                        }
                    )
                    logger.debug("Added CDB to comparisons")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error calculating CDB investment: %s", str(e))

            # Compare LCI (if rate provided)
            if lci_rate is not None:
                try:
                    logger.debug("Calculating LCI investment with rate: %s%%", lci_rate)
                    lci_request = InvestmentRequest(
                        investment_type=InvestmentType.LCI,
                        initial_amount=initial_amount,
                        start_date=start_date,
                        end_date=target_date,
                        lci_rate=lci_rate,
                    )
                    lci_result = await self.calculate_investment(lci_request)
                    comparisons.append(
                        {
                            "type": "LCI Prefixada " + f"{lci_rate:.2f}%",
                            "rate": lci_rate,
                            "effective_rate": lci_result["effective_rate"],
                            "gross_profit": lci_result["gross_profit"],
                            "net_profit": lci_result["net_profit"],
                            "tax_amount": lci_result["tax_amount"],
                            "final_amount": lci_result["final_amount"],
                            "tax_free": lci_result["tax_info"]["is_tax_free"],
                            "tax_info": lci_result["tax_info"],
                        }
                    )
                    logger.debug("Added LCI to comparisons")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error calculating LCI investment: %s", str(e))

            # Compare LCA (if rate provided)
            if lca_rate is not None:
                try:
                    logger.debug("Calculating LCA investment with rate: %s%%", lca_rate)
                    lca_request = InvestmentRequest(
                        investment_type=InvestmentType.LCA,
                        initial_amount=initial_amount,
                        start_date=start_date,
                        end_date=target_date,
                        lca_rate=lca_rate,
                    )
                    lca_result = await self.calculate_investment(lca_request)
                    comparisons.append(
                        {
                            "type": "LCA Prefixada " + f"{lca_rate:.2f}%",
                            "rate": lca_rate,
                            "effective_rate": lca_result["effective_rate"],
                            "gross_profit": lca_result["gross_profit"],
                            "net_profit": lca_result["net_profit"],
                            "tax_amount": lca_result["tax_amount"],
                            "final_amount": lca_result["final_amount"],
                            "tax_free": lca_result["tax_info"]["is_tax_free"],
                            "tax_info": lca_result["tax_info"],
                        }
                    )
                    logger.debug("Added LCA to comparisons")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error calculating LCA investment: %s", str(e))

            # Always include Bitcoin
            try:
                logger.debug("Calculating Bitcoin investment with actual price data")
                btc_request = InvestmentRequest(
                    investment_type=InvestmentType.BTC,
                    initial_amount=initial_amount,
                    start_date=start_date,
                    end_date=target_date,
                )

                # Remove direct price retrieval and rely solely on calculate_investment
                # This ensures consistency with the calculate endpoint
                logger.debug("Using calculate_investment method for Bitcoin calculation")

                btc_result = await self.calculate_investment(btc_request)

                logger.debug("Bitcoin calculation completed through calculate_investment method")

                comparisons.append(
                    {
                        "type": "Bitcoin",
                        "rate": btc_result["rate"],
                        "effective_rate": btc_result["effective_rate"],
                        "gross_profit": btc_result["gross_profit"],
                        "net_profit": btc_result["net_profit"],
                        "tax_amount": btc_result["tax_amount"],
                        "final_amount": btc_result["final_amount"],
                        "tax_free": btc_result["tax_info"]["is_tax_free"],
                        "tax_info": btc_result["tax_info"],
                    }
                )
                logger.debug("Added Bitcoin to comparisons")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error calculating Bitcoin investment: %s", str(e))

            # Add LCI_CDI comparison if percentage is provided
            if lci_cdi_percentage is not None:
                try:
                    logger.debug("Calculating LCI_CDI investment with %.2f%% of CDI", lci_cdi_percentage)
                    lci_cdi_request = InvestmentRequest(
                        investment_type=InvestmentType.LCI_CDI,
                        initial_amount=initial_amount,
                        start_date=start_date,
                        end_date=target_date,
                        cdi_percentage=lci_cdi_percentage,
                    )
                    lci_cdi_result = await self.calculate_investment(lci_cdi_request)
                    cdi_rate = await self.api_client.get_investment_rate(InvestmentType.CDI, target_date)

                    # Format display name
                    display_name = f"LCI {lci_cdi_percentage:.2f}% CDI"

                    comparisons.append(
                        {
                            "type": display_name,
                            "rate": cdi_rate * 100 * (lci_cdi_percentage / 100.0),  # Adjust rate by percentage
                            "effective_rate": lci_cdi_result["effective_rate"],
                            "gross_profit": lci_cdi_result["gross_profit"],
                            "net_profit": lci_cdi_result["net_profit"],
                            "tax_amount": lci_cdi_result["tax_amount"],
                            "final_amount": lci_cdi_result["final_amount"],
                            "tax_free": lci_cdi_result["tax_info"]["is_tax_free"],
                            "tax_info": lci_cdi_result["tax_info"],
                        }
                    )
                    logger.debug("Added LCI_CDI to comparisons")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error calculating LCI_CDI investment: %s", str(e), exc_info=True)

            # Add LCA_CDI comparison if percentage is provided
            if lca_cdi_percentage is not None:
                try:
                    logger.debug("Calculating LCA_CDI investment with %.2f%% of CDI", lca_cdi_percentage)
                    lca_cdi_request = InvestmentRequest(
                        investment_type=InvestmentType.LCA_CDI,
                        initial_amount=initial_amount,
                        start_date=start_date,
                        end_date=target_date,
                        cdi_percentage=lca_cdi_percentage,
                    )
                    lca_cdi_result = await self.calculate_investment(lca_cdi_request)
                    cdi_rate = await self.api_client.get_investment_rate(InvestmentType.CDI, target_date)

                    # Format display name
                    display_name = f"LCA {lca_cdi_percentage:.2f}% CDI"

                    comparisons.append(
                        {
                            "type": display_name,
                            "rate": cdi_rate * 100 * (lca_cdi_percentage / 100.0),  # Adjust rate by percentage
                            "effective_rate": lca_cdi_result["effective_rate"],
                            "gross_profit": lca_cdi_result["gross_profit"],
                            "net_profit": lca_cdi_result["net_profit"],
                            "tax_amount": lca_cdi_result["tax_amount"],
                            "final_amount": lca_cdi_result["final_amount"],
                            "tax_free": lca_cdi_result["tax_info"]["is_tax_free"],
                            "tax_info": lca_cdi_result["tax_info"],
                        }
                    )
                    logger.debug("Added LCA_CDI to comparisons")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error calculating LCA_CDI investment: %s", str(e), exc_info=True)

            # Add LCI_IPCA comparison if spread is provided
            if lci_ipca_spread is not None:
                try:
                    logger.debug("Calculating LCI_IPCA investment with spread: +%.2f%%", lci_ipca_spread)
                    lci_ipca_request = InvestmentRequest(
                        investment_type=InvestmentType.LCI_IPCA,
                        initial_amount=initial_amount,
                        start_date=start_date,
                        end_date=target_date,
                        ipca_spread=lci_ipca_spread,
                    )
                    lci_ipca_result = await self.calculate_investment(lci_ipca_request)
                    ipca_rate = await self.api_client.get_investment_rate(InvestmentType.IPCA, target_date)

                    # Format display name
                    display_name = f"LCI IPCA+{lci_ipca_spread:.2f}%"

                    comparisons.append(
                        {
                            "type": display_name,
                            "rate": ipca_rate * 100 + lci_ipca_spread,  # Add spread to display rate
                            "effective_rate": lci_ipca_result["effective_rate"],
                            "gross_profit": lci_ipca_result["gross_profit"],
                            "net_profit": lci_ipca_result["net_profit"],
                            "tax_amount": lci_ipca_result["tax_amount"],
                            "final_amount": lci_ipca_result["final_amount"],
                            "tax_free": lci_ipca_result["tax_info"]["is_tax_free"],
                            "tax_info": lci_ipca_result["tax_info"],
                        }
                    )
                    logger.debug("Added LCI_IPCA to comparisons")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error calculating LCI_IPCA investment: %s", str(e), exc_info=True)

            # Add LCA_IPCA comparison if spread is provided
            if lca_ipca_spread is not None:
                try:
                    logger.debug("Calculating LCA_IPCA investment with spread: +%.2f%%", lca_ipca_spread)
                    lca_ipca_request = InvestmentRequest(
                        investment_type=InvestmentType.LCA_IPCA,
                        initial_amount=initial_amount,
                        start_date=start_date,
                        end_date=target_date,
                        ipca_spread=lca_ipca_spread,
                    )
                    lca_ipca_result = await self.calculate_investment(lca_ipca_request)
                    ipca_rate = await self.api_client.get_investment_rate(InvestmentType.IPCA, target_date)

                    # Format display name
                    display_name = f"LCA IPCA+{lca_ipca_spread:.2f}%"

                    comparisons.append(
                        {
                            "type": display_name,
                            "rate": ipca_rate * 100 + lca_ipca_spread,  # Add spread to display rate
                            "effective_rate": lca_ipca_result["effective_rate"],
                            "gross_profit": lca_ipca_result["gross_profit"],
                            "net_profit": lca_ipca_result["net_profit"],
                            "tax_amount": lca_ipca_result["tax_amount"],
                            "final_amount": lca_ipca_result["final_amount"],
                            "tax_free": lca_ipca_result["tax_info"]["is_tax_free"],
                            "tax_info": lca_ipca_result["tax_info"],
                        }
                    )
                    logger.debug("Added LCA_IPCA to comparisons")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error calculating LCA_IPCA investment: %s", str(e), exc_info=True)

            # Sort by effective rate (highest first)
            if comparisons:
                comparisons.sort(key=lambda x: x["effective_rate"], reverse=True)

                # Add recommendations
                for comp in comparisons:
                    comp["recommendation"] = self._generate_recommendation(comp, comparisons)

            logger.debug("Generated %d investment comparisons", len(comparisons))
            return comparisons

        except Exception as e:
            logger.error("Error comparing investments: %s", str(e))
            raise ValueError(f"Failed to compare investments: {str(e)}") from e

    def _generate_recommendation(self, investment: dict, all_investments: list[dict]) -> str:
        """
        Generate a recommendation for an investment type.

        Args:
            investment: The investment to generate recommendation for
            all_investments: List of all investments being compared

        Returns:
            Recommendation string
        """
        # Check if future date prediction
        today = date.today()
        prediction_label = ""

        # Use the same approach for consistency - check if we have explicit dates
        if hasattr(self, "api_client") and hasattr(self.api_client, "end_date") and self.api_client.end_date:
            # If we're using an explicit end date in the client, check if it's future
            if self.api_client.end_date > today:
                if hasattr(self.api_client, "start_date") and self.api_client.start_date:
                    if self.api_client.start_date <= today < self.api_client.end_date:
                        # Mixed case - start date is in past, end date is in future
                        prediction_label = " (mixed historical/projected)"
                    else:
                        # Fully future case
                        prediction_label = " (projected)"

        # If this is the top-rated investment
        if investment["type"] == all_investments[0]["type"]:
            # Check if there are other investments with the same rate
            same_rate_investments = [
                inv
                for inv in all_investments
                if inv["type"] != investment["type"]
                and abs(inv["effective_rate"] - investment["effective_rate"]) < 0.001
            ]

            if same_rate_investments:
                other_types = ", ".join([inv["type"] for inv in same_rate_investments])
                if investment["tax_free"] and not all(inv["tax_free"] for inv in same_rate_investments):
                    return f"Best option (tied with {other_types}) with tax-free advantage{prediction_label}"
                return f"Tied for best option with {other_types}{prediction_label}"
            return f"Best option among compared investments{prediction_label}"

        # If this is not the top-rated investment
        best = all_investments[0]
        diff = best["effective_rate"] - investment["effective_rate"]

        # Find all top investments with the same rate (within 0.001%)
        top_investments = [
            inv for inv in all_investments if abs(inv["effective_rate"] - best["effective_rate"]) < 0.001
        ]

        # Get names of top investments
        top_types = ", ".join([inv["type"] for inv in top_investments])

        # If the difference is negligible (less than 0.001%), consider them equal
        if abs(diff) < 0.001:
            if investment["tax_free"] and not best["tax_free"]:
                return f"Equal effective rate to {top_types} with tax-free advantage{prediction_label}"
            if investment["tax_free"]:
                return f"Equal effective rate to {top_types}, both tax-free{prediction_label}"
            return f"Equal effective rate to {top_types}{prediction_label}"

        # Otherwise, show the difference
        if investment["tax_free"] and not best["tax_free"]:
            return f"Tax-free alternative, {diff:.2f}% lower than {top_types}{prediction_label}"
        if investment["tax_free"]:
            return f"Tax-free option, {diff:.2f}% lower than {top_types}{prediction_label}"
        return f"{diff:.2f}% lower than {top_types}{prediction_label}"

    async def calculate_investment(self, request: InvestmentRequest) -> dict:
        """
        Calculate the return on an investment.

        Args:
            request: Investment request containing all necessary parameters

        Returns:
            Dictionary containing investment calculation results
        """
        logger.debug(
            "Calculating investment: investment_type=%s amount=%.2f start_date=%s "
            "end_date=%s cdb_rate=%s lci_rate=%s lca_rate=%s period_years=%.1f",
            request.investment_type,
            request.initial_amount,
            request.start_date,
            request.end_date,
            request.cdb_rate,
            request.lci_rate,
            request.lca_rate,
            request.period_years,
        )

        try:
            # Log the period in days and years
            logger.debug(
                "Investment period: %.2f years (%d days)",
                request.period_years,
                int(request.period_years * 365),
            )

            # Validate rates based on investment type
            if request.investment_type == InvestmentType.CDB:
                logger.debug("CDB investment detected. CDB rate: %s", request.cdb_rate)
                if request.cdb_rate is None:
                    raise ValueError("CDB rate is required for CDB investments")

                annual_rate = request.cdb_rate / 100  # Convert from percentage to decimal

                # CDB uses daily compounding similar to SELIC (252 business days)
                daily_rate = annual_rate / 252
                business_days = int(request.period_years * 252)
                logger.debug(
                    "CDB daily rate: %.6f%%, business days: %d",
                    daily_rate * 100,
                    business_days,
                )

                # Compound interest formula: P * (1 + r)^t - P
                gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                logger.debug(
                    "CDB calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                    request.initial_amount,
                    daily_rate,
                    business_days,
                    request.initial_amount,
                    gross_profit,
                )

                rate = annual_rate  # For response

            elif request.investment_type == InvestmentType.LCI:
                logger.debug("LCI investment detected. LCI rate: %s", request.lci_rate)
                if request.lci_rate is None:
                    raise ValueError("LCI rate is required for LCI investments")

                annual_rate = request.lci_rate / 100  # Convert from percentage to decimal

                # LCI typically uses daily compounding (252 business days)
                daily_rate = annual_rate / 252
                business_days = int(request.period_years * 252)
                logger.debug(
                    "LCI daily rate: %.6f%%, business days: %d",
                    daily_rate * 100,
                    business_days,
                )

                # Compound interest formula: P * (1 + r)^t - P
                gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                logger.debug(
                    "LCI calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                    request.initial_amount,
                    daily_rate,
                    business_days,
                    request.initial_amount,
                    gross_profit,
                )

                rate = annual_rate  # For response

            elif request.investment_type == InvestmentType.LCA:
                logger.debug("LCA investment detected. LCA rate: %s", request.lca_rate)
                if request.lca_rate is None:
                    raise ValueError("LCA rate is required for LCA investments")

                annual_rate = request.lca_rate / 100  # Convert from percentage to decimal

                # LCA typically uses daily compounding (252 business days)
                daily_rate = annual_rate / 252
                business_days = int(request.period_years * 252)
                logger.debug(
                    "LCA daily rate: %.6f%%, business days: %d",
                    daily_rate * 100,
                    business_days,
                )

                # Compound interest formula: P * (1 + r)^t - P
                gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                logger.debug(
                    "LCA calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                    request.initial_amount,
                    daily_rate,
                    business_days,
                    request.initial_amount,
                    gross_profit,
                )

                rate = annual_rate  # For response

            elif request.investment_type == InvestmentType.LCI_CDI:
                logger.debug("LCI_CDI investment detected with %.2f%% of CDI", request.cdi_percentage or 100.0)
                if request.cdi_percentage is None:
                    raise ValueError("CDI percentage is required for LCI_CDI investments")

                if request.end_date is None:
                    raise ValueError("End date must be provided for LCI_CDI investments")

                # Get the CDI rate
                cdi_rate = await self.api_client.get_cdi_rate(request.end_date)
                logger.debug("Raw CDI rate from API: %.4f%%", cdi_rate * 100)

                # For CDI, we'll multiply the CDI rate by the percentage
                annual_rate = cdi_rate * (request.cdi_percentage / 100.0)
                rate = annual_rate

                logger.debug(
                    "Using %.2f%% of CDI rate for LCI_CDI: %.4f%% (CDI %.4f%% × %.2f%%)",
                    request.cdi_percentage,
                    annual_rate * 100,
                    cdi_rate * 100,
                    request.cdi_percentage,
                )

                # CDI uses daily compounding (252 business days per year)
                daily_rate = rate / 252
                business_days = int(request.period_years * 252)
                logger.debug(
                    "LCI_CDI daily rate: %.6f%%, business days: %d",
                    daily_rate * 100,
                    business_days,
                )

                # Compound interest formula: P * (1 + r)^t - P
                gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                logger.debug(
                    "LCI_CDI calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                    request.initial_amount,
                    daily_rate,
                    business_days,
                    request.initial_amount,
                    gross_profit,
                )

            elif request.investment_type == InvestmentType.LCA_CDI:
                logger.debug("LCA_CDI investment detected with %.2f%% of CDI", request.cdi_percentage or 100.0)
                if request.cdi_percentage is None:
                    raise ValueError("CDI percentage is required for LCA_CDI investments")

                if request.end_date is None:
                    raise ValueError("End date must be provided for LCA_CDI investments")

                # Get the CDI rate
                cdi_rate = await self.api_client.get_cdi_rate(request.end_date)
                logger.debug("Raw CDI rate from API: %.4f%%", cdi_rate * 100)

                # For CDI, we'll multiply the CDI rate by the percentage
                annual_rate = cdi_rate * (request.cdi_percentage / 100.0)
                rate = annual_rate

                logger.debug(
                    "Using %.2f%% of CDI rate for LCA_CDI: %.4f%% (CDI %.4f%% × %.2f%%)",
                    request.cdi_percentage,
                    annual_rate * 100,
                    cdi_rate * 100,
                    request.cdi_percentage,
                )

                # CDI uses daily compounding (252 business days per year)
                daily_rate = rate / 252
                business_days = int(request.period_years * 252)
                logger.debug(
                    "LCA_CDI daily rate: %.6f%%, business days: %d",
                    daily_rate * 100,
                    business_days,
                )

                # Compound interest formula: P * (1 + r)^t - P
                gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                logger.debug(
                    "LCA_CDI calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                    request.initial_amount,
                    daily_rate,
                    business_days,
                    request.initial_amount,
                    gross_profit,
                )

            elif request.investment_type == InvestmentType.LCI_IPCA:
                logger.debug("LCI_IPCA investment detected with spread: +%.2f%%", request.ipca_spread or 0.0)
                if request.ipca_spread is None:
                    raise ValueError("IPCA spread is required for LCI_IPCA investments")

                if request.end_date is None:
                    raise ValueError("End date must be provided for LCI_IPCA investments")

                # Get the IPCA rate
                ipca_rate = await self.api_client.get_ipca_rate(request.end_date)
                logger.debug("Raw IPCA rate from API: %.4f%%", ipca_rate * 100)

                ipca_spread = request.ipca_spread
                logger.debug("IPCA spread for LCI_IPCA: +%.2f%%", ipca_spread)

                # For IPCA, we'll use the actual IPCA rate plus the specified spread
                annual_rate = ipca_rate + (ipca_spread / 100)  # Convert spread percentage to decimal
                rate = annual_rate

                logger.debug(
                    "Using IPCA%s rate for LCI_IPCA: %.4f%% (IPCA %.4f%% + %.2f%%)",
                    f"+{ipca_spread}%" if ipca_spread > 0 else "",
                    annual_rate * 100,
                    ipca_rate * 100,
                    ipca_spread,
                )

                # IPCA uses daily compounding (252 business days per year)
                daily_rate = rate / 252
                business_days = int(request.period_years * 252)
                logger.debug(
                    "LCI_IPCA daily rate: %.6f%%, business days: %d",
                    daily_rate * 100,
                    business_days,
                )

                # Compound interest formula: P * (1 + r)^t - P
                gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                logger.debug(
                    "LCI_IPCA calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                    request.initial_amount,
                    daily_rate,
                    business_days,
                    request.initial_amount,
                    gross_profit,
                )

            elif request.investment_type == InvestmentType.LCA_IPCA:
                logger.debug("LCA_IPCA investment detected with spread: +%.2f%%", request.ipca_spread or 0.0)
                if request.ipca_spread is None:
                    raise ValueError("IPCA spread is required for LCA_IPCA investments")

                if request.end_date is None:
                    raise ValueError("End date must be provided for LCA_IPCA investments")

                # Get the IPCA rate
                ipca_rate = await self.api_client.get_ipca_rate(request.end_date)
                logger.debug("Raw IPCA rate from API: %.4f%%", ipca_rate * 100)

                ipca_spread = request.ipca_spread
                logger.debug("IPCA spread for LCA_IPCA: +%.2f%%", ipca_spread)

                # For IPCA, we'll use the actual IPCA rate plus the specified spread
                annual_rate = ipca_rate + (ipca_spread / 100)  # Convert spread percentage to decimal
                rate = annual_rate

                logger.debug(
                    "Using IPCA%s rate for LCA_IPCA: %.4f%% (IPCA %.4f%% + %.2f%%)",
                    f"+{ipca_spread}%" if ipca_spread > 0 else "",
                    annual_rate * 100,
                    ipca_rate * 100,
                    ipca_spread,
                )

                # IPCA uses daily compounding (252 business days per year)
                daily_rate = rate / 252
                business_days = int(request.period_years * 252)
                logger.debug(
                    "LCA_IPCA daily rate: %.6f%%, business days: %d",
                    daily_rate * 100,
                    business_days,
                )

                # Compound interest formula: P * (1 + r)^t - P
                gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                logger.debug(
                    "LCA_IPCA calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                    request.initial_amount,
                    daily_rate,
                    business_days,
                    request.initial_amount,
                    gross_profit,
                )

            else:
                # For non-CDB investments, get current SELIC rate for reference
                if request.end_date is None:
                    raise ValueError("End date must be provided for non-CDB investments")
                selic_rate = await self.api_client.get_selic_rate(request.end_date)
                logger.debug("Current SELIC rate: %.2f%%", selic_rate * 100)

                # Calculate investment rate based on type
                if request.investment_type == InvestmentType.POUPANCA:
                    # Get the base poupança rate
                    if request.end_date is None:
                        raise ValueError("End date must be provided for Poupança investments")
                    poupanca_base_rate = await self.api_client.get_poupanca_rate(request.end_date)
                    logger.debug("Raw poupança rate from API: %.4f%%", poupanca_base_rate * 100)

                    # Convert the annual rate to monthly rate
                    # (1 + annual_rate)^(1/12) - 1
                    monthly_rate = (1 + poupanca_base_rate) ** (1 / 12) - 1

                    logger.debug(
                        "Using Poupança monthly rate: %.4f%% (from annual rate %.4f%%)",
                        monthly_rate * 100,
                        poupanca_base_rate * 100,
                    )

                    # Calculate annualized rate for response
                    annual_rate = poupanca_base_rate
                    rate = annual_rate  # Store for the response

                    logger.debug(
                        "Using poupança monthly rate: %.4f%% (%.4f%% annual)",
                        monthly_rate * 100,
                        annual_rate * 100,
                    )

                    # Poupança uses monthly compounding
                    months = int(request.period_years * 12)
                    gross_profit = request.initial_amount * ((1 + monthly_rate) ** months) - request.initial_amount
                    logger.debug(
                        "Poupança calculation: %.2f * ((1 + %.6f) ^ %d) - %.2f = %.2f",
                        request.initial_amount,
                        monthly_rate,
                        months,
                        request.initial_amount,
                        gross_profit,
                    )

                # SELIC investments
                elif request.investment_type == InvestmentType.SELIC:
                    logger.debug("Raw SELIC rate from API: %.4f%%", selic_rate * 100)

                    # Use the actual SELIC rate from the API
                    annual_rate = selic_rate

                    # Add the spread if provided
                    selic_spread = request.selic_spread or 0.0
                    if selic_spread > 0:
                        logger.debug("Adding SELIC spread: +%.2f%%", selic_spread)
                        annual_rate += selic_spread / 100  # Convert spread percentage to decimal

                    rate = annual_rate

                    logger.debug(
                        "Using SELIC%s rate: %.4f%%",
                        f"+{selic_spread}%" if selic_spread > 0 else "",
                        annual_rate * 100,
                    )

                    # Selic uses daily compounding (252 business days per year)
                    daily_rate = rate / 252
                    business_days = int(request.period_years * 252)
                    logger.debug(
                        "Selic daily rate: %.6f%%, business days: %d",
                        daily_rate * 100,
                        business_days,
                    )

                    # Compound interest formula: P * (1 + r)^t - P
                    gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                    logger.debug(
                        "SELIC calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                        request.initial_amount,
                        daily_rate,
                        business_days,
                        request.initial_amount,
                        gross_profit,
                    )

                # IPCA investments
                elif request.investment_type == InvestmentType.IPCA:
                    # Get the IPCA rate
                    ipca_rate = await self.api_client.get_ipca_rate(request.end_date)
                    logger.debug("Raw IPCA rate from API: %.4f%%", ipca_rate * 100)

                    # Get the spread from the request or use default
                    ipca_spread = request.ipca_spread or 0.0
                    logger.debug("IPCA spread: +%.2f%%", ipca_spread)

                    # For IPCA, we'll use the actual IPCA rate plus the specified spread
                    annual_rate = ipca_rate + (ipca_spread / 100)  # Convert spread percentage to decimal
                    rate = annual_rate

                    logger.debug(
                        "Using IPCA%s rate: %.4f%% (IPCA %.4f%% + %.2f%%)",
                        f"+{ipca_spread}%" if ipca_spread > 0 else "",
                        annual_rate * 100,
                        ipca_rate * 100,
                        ipca_spread,
                    )

                    # IPCA uses daily compounding (252 business days per year)
                    daily_rate = rate / 252
                    business_days = int(request.period_years * 252)
                    logger.debug(
                        "IPCA daily rate: %.6f%%, business days: %d",
                        daily_rate * 100,
                        business_days,
                    )

                    # Compound interest formula: P * (1 + r)^t - P
                    gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                    logger.debug(
                        "IPCA calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                        request.initial_amount,
                        daily_rate,
                        business_days,
                        request.initial_amount,
                        gross_profit,
                    )

                # CDI investments
                elif request.investment_type == InvestmentType.CDI:
                    # Get the CDI rate
                    cdi_rate = await self.api_client.get_cdi_rate(request.end_date)
                    logger.debug("Raw CDI rate from API: %.4f%%", cdi_rate * 100)

                    # Get CDI percentage (default is 100%)
                    cdi_percentage = request.cdi_percentage or 100.0

                    # For CDI, we'll multiply the CDI rate by the percentage
                    annual_rate = cdi_rate * (cdi_percentage / 100.0)
                    rate = annual_rate

                    logger.debug(
                        "Using %.2f%% of CDI rate: %.4f%% (CDI %.4f%% × %.2f%%)",
                        cdi_percentage,
                        annual_rate * 100,
                        cdi_rate * 100,
                        cdi_percentage,
                    )

                    # CDI uses daily compounding (252 business days per year)
                    daily_rate = rate / 252
                    business_days = int(request.period_years * 252)
                    logger.debug(
                        "CDI daily rate: %.6f%%, business days: %d",
                        daily_rate * 100,
                        business_days,
                    )

                    # Compound interest formula: P * (1 + r)^t - P
                    gross_profit = request.initial_amount * ((1 + daily_rate) ** business_days) - request.initial_amount
                    logger.debug(
                        "CDI calculation: %.2f * ((1 + %.8f) ^ %d) - %.2f = %.2f",
                        request.initial_amount,
                        daily_rate,
                        business_days,
                        request.initial_amount,
                        gross_profit,
                    )

                # Bitcoin investments
                elif request.investment_type == InvestmentType.BTC:
                    # Get Bitcoin prices at start and end dates
                    if request.start_date is None or request.end_date is None:
                        raise ValueError("Start date and end date must be provided for Bitcoin investments")

                    btc_start_price = await self.crypto_client.get_bitcoin_price(request.start_date)
                    btc_end_price = await self.crypto_client.get_bitcoin_price(request.end_date)

                    logger.debug(
                        "Bitcoin price at start date (%s): BRL %.2f",
                        request.start_date,
                        btc_start_price,
                    )
                    logger.debug(
                        "Bitcoin price at end date (%s): BRL %.2f",
                        request.end_date,
                        btc_end_price,
                    )

                    # Calculate the price change percentage
                    price_change_pct = ((btc_end_price - btc_start_price) / btc_start_price) * 100

                    # Calculate the annualized return (using compound annual growth rate formula)
                    if price_change_pct >= 0:
                        annual_rate = ((1 + (price_change_pct / 100)) ** (1 / request.period_years)) - 1
                    else:
                        # Handle negative returns
                        annual_rate = ((1 + (price_change_pct / 100)) ** (1 / request.period_years)) - 1

                    rate = annual_rate

                    logger.debug(
                        "Bitcoin price change: %.2f%% over %.2f years",
                        price_change_pct,
                        request.period_years,
                    )
                    logger.debug("Annualized BTC rate: %.2f%%", annual_rate * 100)

                    # Calculate gross profit based on actual price change
                    # How many BTC could be purchased with initial amount
                    btc_amount = request.initial_amount / btc_start_price
                    # Value of that BTC at end date
                    final_value = btc_amount * btc_end_price
                    # Gross profit
                    gross_profit = final_value - request.initial_amount

                    logger.debug(
                        "BTC calculation: Initial BRL %.2f buys %.8f BTC at BRL %.2f/BTC, "
                        "worth BRL %.2f at end price of BRL %.2f/BTC, profit: BRL %.2f",
                        request.initial_amount,
                        btc_amount,
                        btc_start_price,
                        final_value,
                        btc_end_price,
                        gross_profit,
                    )

                else:
                    raise ValueError(f"Unsupported investment type: {request.investment_type}")

            logger.debug("Gross profit: R$ %.2f", gross_profit)

            # Calculate tax amount
            if request.start_date is None or request.end_date is None:
                raise ValueError("Start date and end date must be provided for tax calculation")

            tax_amount = await self._calculate_tax(
                request.investment_type,
                request.start_date,
                request.end_date,
                gross_profit,
                request.initial_amount,
            )
            logger.debug("Tax amount: R$ %.2f", tax_amount)

            # Calculate net profit
            net_profit = gross_profit - tax_amount
            logger.debug("Net profit: R$ %.2f", net_profit)

            # Calculate final amount
            final_amount = request.initial_amount + net_profit
            logger.debug("Final amount: R$ %.2f", final_amount)

            # Calculate effective rate (net profit / initial amount)
            effective_rate = (net_profit / request.initial_amount) * 100
            logger.debug("Effective rate: %.2f%%", effective_rate)

            # Get the tax rate percentage
            tax_rate = self.tax_calculator.calculate_tax_rate(
                investment_type=request.investment_type,
                days=int(request.period_years * 365),
                initial_amount=request.initial_amount,
                gross_profit=gross_profit,
            )

            # Calculate tax information
            is_tax_free = tax_rate == 0

            # Special case for Bitcoin - ensure is_tax_free is consistent with tax amount
            if request.investment_type == InvestmentType.BTC:
                is_tax_free = tax_amount == 0

            tax_rate_percentage = tax_rate * 100  # Convert to percentage

            response = {
                "investment_type": request.investment_type,
                "initial_amount": request.initial_amount,
                "final_amount": final_amount,
                "gross_profit": gross_profit,
                "net_profit": net_profit,
                "tax_amount": tax_amount,
                "effective_rate": effective_rate,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "rate": rate * 100,  # Convert to percentage for display
                "tax_info": {
                    "tax_rate_percentage": tax_rate_percentage,
                    "tax_amount": tax_amount,
                    "is_tax_free": is_tax_free,
                    "tax_period_days": int(request.period_years * 365),
                    "tax_period_description": self._get_tax_period_description(
                        int(request.period_years * 365),
                        request.investment_type,
                        request.initial_amount,
                        gross_profit,
                    ),
                },
            }

            return response

        except Exception as e:
            logger.error("Error calculating investment: %s", str(e))
            raise ValueError(f"Failed to calculate investment: {str(e)}") from e

    def _get_tax_period_description(
        self,
        days: int,
        investment_type: InvestmentType,
        initial_amount: Optional[float] = None,
        gross_profit: Optional[float] = None,
    ) -> str:
        """Get a description of the tax period based on days and investment type."""
        # Check if this is a future date prediction
        today = date.today()

        # We need to check the actual end date from the request
        # Since we don't have direct access to it here, we'll use a different approach
        prediction_label = ""
        if hasattr(self, "api_client") and hasattr(self.api_client, "end_date") and self.api_client.end_date:
            # If we're using an explicit end date in the client, check if it's future
            if self.api_client.end_date > today:
                if hasattr(self.api_client, "start_date") and self.api_client.start_date:
                    if self.api_client.start_date <= today < self.api_client.end_date:
                        # Mixed case - start date is in past, end date is in future
                        prediction_label = " (mixed historical/projected)"
                    else:
                        # Fully future case
                        prediction_label = " (projected)"

        # For tax-free investments, don't show taxable periods
        if investment_type in (
            InvestmentType.POUPANCA,
            InvestmentType.LCI,
            InvestmentType.LCA,
        ):
            return f"Tax-free investment{prediction_label}"

        # For Bitcoin, show the special tax rules
        if investment_type == InvestmentType.BTC:
            if initial_amount is None or gross_profit is None:
                return f"15% tax on gains (sales exceeding R$ 35,000/month){prediction_label}"

            # If there's a loss, no tax applies regardless of sale amount
            if gross_profit <= 0:
                return f"No tax (capital loss of R$ {-gross_profit:.2f}){prediction_label}"

            # Calculate final sale amount
            sale_amount = initial_amount + gross_profit

            # For Bitcoin tax rules in Brazil:
            # - Monthly sales BELOW R$ 35,000: tax-exempt on any gains
            # - Monthly sales ABOVE R$ 35,000: progressive tax rates based on profit
            if sale_amount <= 35000:
                return f"Tax-exempt (monthly sales below R$ 35,000 threshold){prediction_label}"

            # Show appropriate tax rate based on profit amount
            if gross_profit <= 5_000_000:  # Up to R$ 5 million
                return f"15% tax on gains (monthly sales exceed R$ 35,000 threshold){prediction_label}"
            if gross_profit <= 10_000_000:  # R$ 5M to R$ 10M
                return f"17.5% tax on gains (profit between R$ 5-10 million){prediction_label}"
            if gross_profit <= 30_000_000:  # R$ 10M to R$ 30M
                return f"20% tax on gains (profit between R$ 10-30 million){prediction_label}"
            # Above R$ 30M
            return f"22.5% tax on gains (profit exceeds R$ 30 million){prediction_label}"

        # For taxable investments, show the appropriate tax period
        if days <= 180:
            return f"Up to 180 days (22.5% tax){prediction_label}"
        if days <= 360:
            return f"181 to 360 days (20% tax){prediction_label}"
        if days <= 720:
            return f"361 to 720 days (17.5% tax){prediction_label}"
        return f"More than 720 days (15% tax){prediction_label}"

    async def _calculate_tax(
        self,
        investment_type: InvestmentType,
        start_date: date,
        end_date: date,
        gross_profit: float,
        initial_amount: Optional[float] = None,
    ) -> float:
        """
        Calculate the tax amount for the investment.

        Args:
            investment_type: Type of investment
            start_date: Start date for the investment period
            end_date: End date for the investment period
            gross_profit: Gross profit amount
            initial_amount: Initial investment amount (needed for BTC calculations)

        Returns:
            Tax amount
        """
        # Calculate the investment duration in days
        days = (end_date - start_date).days
        logger.debug("Investment duration: %d days", days)

        # For LCI and LCA, there's no income tax
        if investment_type in (InvestmentType.LCI, InvestmentType.LCA):
            logger.debug("LCI/LCA investments are tax-free")
            return 0.0
        if investment_type == InvestmentType.POUPANCA:
            # Check if the investment is tax-free (Poupança is tax-free in all cases)
            logger.debug("Poupança investment is tax-free")
            return 0.0

        # Special case for Bitcoin - apply tax directly here
        if investment_type == InvestmentType.BTC:
            if initial_amount is None:
                logger.warning("Missing initial_amount for Bitcoin tax calculation")
                return 0.0

            # No tax on losses
            if gross_profit <= 0:
                logger.debug("No tax on Bitcoin loss")
                return 0.0

            # Calculate sale amount
            sale_amount = initial_amount + gross_profit

            # Brazil's tax rule: Tax applies if monthly sales exceed R$ 35,000
            if sale_amount > 35000:
                # Progressive tax rates based on profit amount
                if gross_profit <= 5_000_000:  # Up to R$ 5 million
                    tax_rate = 0.15
                elif gross_profit <= 10_000_000:  # R$ 5M to R$ 10M
                    tax_rate = 0.175
                elif gross_profit <= 30_000_000:  # R$ 10M to R$ 30M
                    tax_rate = 0.20
                else:  # Above R$ 30M
                    tax_rate = 0.225

                tax_amount = gross_profit * tax_rate
                logger.debug(
                    "Bitcoin tax: R$ %.2f (%.1f%% of R$ %.2f profit)",
                    tax_amount,
                    tax_rate * 100,
                    gross_profit,
                )
                return tax_amount

            logger.debug("No tax on Bitcoin (sales below R$ 35,000 threshold)")
            return 0.0

        # Get the tax rate for other investment types
        rate = self.tax_calculator.calculate_tax_rate(investment_type, days)
        logger.debug("Tax rate: %.2f%%", rate * 100)

        # For other investments, calculate the tax normally
        tax_amount = gross_profit * rate
        logger.debug("Tax amount: R$ %.2f", tax_amount)
        return tax_amount
