"""
External API client for fetching financial data.
"""

import json
import logging
import math
from datetime import date, datetime, timedelta
from typing import Optional

import backoff
import httpx

from .config import BCB_RATE_CONSTANTS, BCB_SERIES_CODES
from .models import InvestmentType

logger = logging.getLogger(__name__)


# Define a function to determine if an exception should trigger a retry
def should_retry(exception):
    """Determine if the exception is retryable."""
    if isinstance(exception, httpx.HTTPStatusError):
        # Retry on 429 (Too Many Requests), 500, 502, 503, 504 server errors
        return exception.response.status_code in (429, 500, 502, 503, 504)

    # Retry on connection errors, timeouts, etc.
    return isinstance(exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError))


class CryptoApiClient:
    """Client for fetching cryptocurrency data from CryptoCompare API."""

    # CryptoCompare API for historical daily BTC prices (with BRL conversion)
    CRYPTOCOMPARE_HISTORICAL_URL = "https://min-api.cryptocompare.com/data/pricehistorical?fsym=BTC&tsyms=BRL&ts={}"
    # CryptoCompare API for current BTC price
    CRYPTOCOMPARE_CURRENT_URL = "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=BRL"

    def __init__(self):
        """Initialize the Crypto API client."""
        logger.debug("Initializing CryptoApiClient using CryptoCompare API")
        self.http_client = None
        # Cache for Bitcoin prices to ensure consistency between requests
        self.price_cache = {}
        # Flag to indicate if this client instance is shared across multiple calculators
        self.is_shared = False
        logger.debug("Initialized price cache for consistent data between requests")

    async def get_http_client(self):
        """Get or create an HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client

    async def close(self):
        """Close the HTTP client if it exists."""
        if self.http_client is not None:
            # Only close if not shared with other components
            if not self.is_shared:
                await self.http_client.aclose()
                self.http_client = None
                logger.debug("Closed CryptoApiClient HTTP client")
            else:
                logger.debug("Not closing shared CryptoApiClient HTTP client")

    async def _make_request(self, url: str) -> dict:
        """
        Make an HTTP request to CryptoCompare API.

        Args:
            url: The URL to request

        Returns:
            The JSON response data

        Raises:
            ValueError: If no data is available
            Exception: Other exceptions from the HTTP request
        """
        client = await self.get_http_client()
        logger.debug("Making CryptoCompare API request to: %s", url)

        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        if not data:
            error_msg = f"No data available from URL: {url}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        return data

    async def get_bitcoin_price(self, date_obj: date) -> float:
        """
        Get the Bitcoin price in BRL for a specific date from CryptoCompare API.
        Uses a cache to ensure consistent data between requests.

        Args:
            date_obj: The date to get the price for

        Returns:
            Bitcoin price in BRL as a float
        """
        # Check if price is already in cache
        cache_key = date_obj.isoformat()
        if cache_key in self.price_cache:
            logger.debug(
                "Using cached Bitcoin price for %s: BRL %.2f",
                date_obj,
                self.price_cache[cache_key],
            )
            return self.price_cache[cache_key]

        # Get today's actual date
        today = date.today()

        # CASE 1: Historical date - use actual API data
        if date_obj <= today:
            price = await self._get_historical_btc_price(date_obj)
            # Cache the price for future requests
            self.price_cache[cache_key] = price
            logger.debug("Cached Bitcoin price for %s", date_obj)
            return price

        # CASE 2: Future date - use more sophisticated projections
        logger.info("Requested Bitcoin price for future date: %s", date_obj)
        days_in_future = (date_obj - today).days

        try:
            # Get current price
            current_price = await self._get_historical_btc_price(today)

            # APPROACH 1: Volatility-aware projection based on historical pattern
            # Get price from equivalent days in past for pattern matching
            # This looks at what Bitcoin did for the same number of days in the past
            past_date = today - timedelta(days=days_in_future)
            past_price = await self._get_historical_btc_price(past_date)

            # Calculate the growth rate from past period
            past_growth_rate = (current_price / past_price) - 1

            # Apply that growth rate to current price for the future
            # But reduce the effect (assume regression to the mean)
            projected_price_pattern = current_price * (1 + (past_growth_rate * 0.5))

            # APPROACH 2: Dampened growth model
            # More conservative estimate based on diminishing returns
            annual_growth_rate = 0.20  # 20% annual growth rate (conservative long-term estimate)
            daily_growth_rate = annual_growth_rate / 365
            dampening_factor = 1 / math.sqrt(1 + (days_in_future / 365))  # Diminishing returns
            effective_daily_rate = daily_growth_rate * dampening_factor
            projected_price_model = current_price * (1 + effective_daily_rate) ** days_in_future

            # APPROACH 3: Random walk with drift based on past volatility
            # This simulates a more random future price within reasonable bounds
            # (Implementation not shown for simplicity)

            # Use a weighted average of different approaches
            # Short-term: more weight on recent pattern
            # Long-term: more weight on conservative model
            if days_in_future <= 90:  # 3 months
                weight_pattern = 0.7
                weight_model = 0.3
            else:
                # Gradually shift weights for longer projections
                weight_pattern = max(0.1, 0.7 - ((days_in_future - 90) / 1000))
                weight_model = 1 - weight_pattern

            projected_price = (projected_price_pattern * weight_pattern) + (projected_price_model * weight_model)

            logger.info(
                "Projected Bitcoin price for %s: BRL %.2f (%.1f days in future)",
                date_obj,
                projected_price,
                days_in_future,
            )
            logger.debug(
                "Pattern-based: BRL %.2f, Model-based: BRL %.2f, Weights: %.2f/%.2f",
                projected_price_pattern,
                projected_price_model,
                weight_pattern,
                weight_model,
            )

            # Cache the projected price
            self.price_cache[cache_key] = projected_price
            return projected_price

        except Exception as e:
            logger.error("Error projecting Bitcoin price: %s", str(e))
            raise ValueError(f"Failed to project Bitcoin price for {date_obj}: {str(e)}") from e

    async def _get_historical_btc_price(self, date_obj: date) -> float:
        """Get historical Bitcoin price from the API."""
        try:
            # Convert date to UNIX timestamp (seconds since epoch)
            dt = datetime.combine(date_obj, datetime.min.time())
            timestamp = int(dt.timestamp())

            if date_obj == date.today():
                # For today, use current price API
                logger.debug("Fetching current Bitcoin price from CryptoCompare for today")
                url = self.CRYPTOCOMPARE_CURRENT_URL
                data = await self._make_request(url)
                price = data["BRL"]
                logger.debug("Current Bitcoin price: BRL %.2f", price)
            else:
                # For historical dates, use historical API
                logger.debug(
                    "Fetching historical Bitcoin price from CryptoCompare for timestamp: %s",
                    timestamp,
                )
                url = self.CRYPTOCOMPARE_HISTORICAL_URL.format(timestamp)
                data = await self._make_request(url)
                # Extract BRL price from response
                price = data["BTC"]["BRL"]
                logger.debug(
                    "Historical Bitcoin price for %s: BRL %.2f",
                    date_obj,
                    price,
                )

            return price
        except Exception as e:
            logger.error("Error fetching Bitcoin price from CryptoCompare: %s", str(e))
            raise ValueError(f"Failed to retrieve Bitcoin price for {date_obj}: {str(e)}") from e


class BCBApiClient:
    """Client for fetching data from Brazilian Central Bank API."""

    BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados/?dataInicial={}&dataFinal={}"

    # Use constants from config
    MAX_DAILY_RANGE = BCB_RATE_CONSTANTS["MAX_DAILY_RANGE"]
    DEFAULT_RANGE_DAYS = BCB_RATE_CONSTANTS["DEFAULT_RANGE_DAYS"]

    # API Series codes from config
    SERIES_SELIC = BCB_SERIES_CODES["SELIC"]
    SERIES_CDI = BCB_SERIES_CODES["CDI"]
    SERIES_IPCA = BCB_SERIES_CODES["IPCA"]
    SERIES_POUPANCA = BCB_SERIES_CODES["POUPANCA"]

    # Rate constants and thresholds from config
    SELIC_MIN_EXPECTED = BCB_RATE_CONSTANTS["SELIC_MIN_EXPECTED"]
    SELIC_MAX_EXPECTED = BCB_RATE_CONSTANTS["SELIC_MAX_EXPECTED"]

    # Poupança calculation constants from config
    POUPANCA_SELIC_THRESHOLD = BCB_RATE_CONSTANTS["POUPANCA_SELIC_THRESHOLD"]
    POUPANCA_MONTHLY_RATE = BCB_RATE_CONSTANTS["POUPANCA_MONTHLY_RATE"]
    POUPANCA_SELIC_FACTOR = BCB_RATE_CONSTANTS["POUPANCA_SELIC_FACTOR"]

    # Business days in year from config
    BUSINESS_DAYS_IN_YEAR = BCB_RATE_CONSTANTS["BUSINESS_DAYS_IN_YEAR"]

    def __init__(self, start_date: date | None = None, end_date: date | None = None):
        """
        Initialize the BCB API client.

        Args:
            start_date: Optional start date for testing (default: 30 days before end_date)
            end_date: Optional end date for testing (default: today)
        """
        logger.debug("Initializing BCB API client")

        # Store the requested date range
        self.start_date = start_date
        self.end_date = end_date

        # These dates are only used for initialization, not for API requests
        logger.debug(
            "BCB client initialized with date range: %s to %s",
            self.start_date or "None",
            self.end_date or "None",
        )

        self.http_client = None

    async def get_http_client(self):
        """Get or create an HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client

    async def close(self):
        """Close the HTTP client if it exists."""
        if self.http_client is not None:
            await self.http_client.aclose()
            self.http_client = None
            logger.debug("Closed HTTP client")

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        max_time=30,
        giveup=lambda e: not should_retry(e),
        on_backoff=lambda details: logger.warning(
            "Backing off request to '%s' for %.1f seconds after %d tries. Exception: %s",
            details["args"][0] if details["args"] else "unknown URL",
            details["wait"],
            details["tries"],
            details["exception"],
        ),
    )
    async def _make_request(self, url: str) -> dict:
        """
        Make an HTTP request with retry logic.

        Args:
            url: The URL to request

        Returns:
            The JSON response data

        Raises:
            ValueError: If no data is available
            Exception: Other exceptions from the HTTP request
        """
        client = await self.get_http_client()
        logger.debug("Making request to: %s", url)

        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        if not data:
            error_msg = f"No data available from URL: {url}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        return data

    async def get_investment_rate(self, investment_type: InvestmentType, target_date: date) -> float:
        """
        Get the investment rate for a given type and date.

        Args:
            investment_type: Type of investment
            target_date: Date to get the rate for

        Returns:
            Investment rate as a decimal
        """
        logger.debug(
            "Getting rate for investment type %s on date %s",
            investment_type,
            target_date,
        )

        if investment_type == InvestmentType.SELIC:
            return await self.get_selic_rate(target_date)
        if investment_type == InvestmentType.POUPANCA:
            return await self.get_poupanca_rate(target_date)
        if investment_type == InvestmentType.IPCA:
            return await self.get_ipca_rate(target_date)
        if investment_type == InvestmentType.CDI:
            return await self.get_cdi_rate(target_date)
        if investment_type == InvestmentType.BTC:
            # For BTC, we don't get the rate through this API
            # We'll return a placeholder value since the actual calculation uses CryptoApiClient
            logger.debug("Bitcoin rate requested - will be handled by CryptoApiClient")
            return 0.0  # Placeholder, actual rate is calculated from price data
        raise ValueError(f"Unsupported investment type: {investment_type}")

    async def get_selic_rate(self, target_date: date) -> float:
        """
        Get the SELIC rate for a given date.

        Args:
            target_date: Date to get the rate for

        Returns:
            SELIC rate as a decimal (annual rate)
        """
        logger.debug("Fetching SELIC rate for date: %s", target_date)

        # Get today's actual date
        today = date.today()

        # CASE 1: Historical date - use actual API data
        if target_date <= today:
            try:
                return await self._get_historical_selic_rate(target_date)
            except ValueError as e:
                # For historical dates, if we can't get data, this is a real error
                logger.error("Cannot get historical SELIC data: %s", e)
                raise

        # CASE 2: Future date - use a pattern from the past with the same length
        logger.info("Requested SELIC rate for future date: %s", target_date)
        days_in_future = (target_date - today).days

        # Calculate the equivalent past date range with same length
        past_end_date = today
        past_start_date = today - timedelta(days=days_in_future)

        # Log that we're using historical patterns for prediction
        logger.info(
            "Using historical pattern from %s to %s to predict future SELIC rate for %s",
            past_start_date,
            past_end_date,
            target_date,
        )

        try:
            # We need the most recent SELIC rate to project into the future
            # Past pattern is useful but for SELIC we need the most current value
            latest_rate = await self._get_historical_selic_rate(today)

            # For now, assume SELIC will hold steady (this is a simple projection)
            # In reality, a more sophisticated model would use COPOM meeting schedule
            # and market forecasts to predict changes

            logger.info(
                "Using latest SELIC rate (%.4f%%) as prediction for %s",
                latest_rate * 100,
                target_date,
            )
            return latest_rate

        except Exception as e:
            logger.error("Failed to get SELIC rate for future date: %s", e)
            # Propagate the error instead of using a fallback value
            raise ValueError(f"Failed to predict SELIC rate: {str(e)}") from e

    async def _get_historical_selic_rate(
        self, target_date: date, historical_start_date: Optional[date] = None
    ) -> float:
        """
        Get historical SELIC rate from the API.

        Args:
            target_date: The date to get the rate for
            historical_start_date: Optional start date to use for the API request
                                  (useful when getting patterns for future predictions)
        """
        reference_date = self._get_reference_date(target_date, InvestmentType.SELIC)
        logger.debug("Using reference date: %s", reference_date)

        # Use the provided date range or calculate from reference date
        if self.start_date and self.end_date:
            start_date = self.start_date
            end_date = self.end_date
            logger.debug("Using provided date range: %s to %s", start_date, end_date)
        elif historical_start_date:
            # Use the historical date range provided (for future date predictions)
            start_date = historical_start_date
            end_date = target_date
            logger.debug("Using historical date range: %s to %s", start_date, end_date)
        else:
            start_date = reference_date - timedelta(days=self.DEFAULT_RANGE_DAYS)
            end_date = reference_date
            logger.debug("Using calculated date range: %s to %s", start_date, end_date)

        # Make sure we're not using future dates in the API request
        today = date.today()
        if start_date > today:
            logger.warning(
                "Adjusting future start date %s to today %s for API request",
                start_date,
                today,
            )
            start_date = today - timedelta(days=30)  # Use last 30 days of data
        if end_date > today:
            logger.warning(
                "Adjusting future end date %s to today %s for API request",
                end_date,
                today,
            )
            end_date = today

        formatted_start = start_date.strftime("%d/%m/%Y")
        formatted_end = end_date.strftime("%d/%m/%Y")
        logger.debug("Using date range: %s to %s", formatted_start, formatted_end)

        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{self.SERIES_SELIC}/dados"
            f"?formato=json&dataInicial={formatted_start}&dataFinal={formatted_end}"
        )
        logger.debug("Requesting SELIC rate from URL: %s", url)

        try:
            data = await self._make_request(url)
            if not data:
                raise ValueError("Empty response from BCB API")

            # Extra logging to debug potential format issues
            if isinstance(data, str):
                logger.warning("API returned string instead of JSON: %s", data[:100])
                try:
                    data = json.loads(data)
                except Exception as e:
                    logger.error("Failed to parse API response as JSON: %s", str(e))
                    raise ValueError(f"Invalid response format: {data[:100]}...") from e

            # Check if we got a different format than expected
            if not isinstance(data, list):
                logger.warning("Unexpected API response format: %s", str(data)[:100])
                # Handle empty array response
                if data == []:
                    raise ValueError("API returned empty array")

                # BCB API might return an error message in a different format
                if isinstance(data, dict) and "erro" in data:
                    logger.warning("BCB API returned error: %s", data["erro"])
                    raise ValueError(f"BCB API error: {data['erro']}")

                raise ValueError(f"Unexpected data format: {type(data)}")

            # Handle the case where data is empty
            if not data:
                raise ValueError("API returned empty data")

            # Find the rate closest to our target date
            target_str = reference_date.strftime("%d/%m/%Y")

            # Try to find exact match, otherwise use the latest date
            try:
                rate_data = next((item for item in data if item["data"] == target_str), None)
            except (KeyError, TypeError) as e:
                logger.warning(
                    "Error accessing data structure: %s. Data sample: %s",
                    e,
                    str(data[:2]),
                )
                # Try alternate format if possible
                if data and isinstance(data, list) and isinstance(data[0], dict):
                    # Try to identify the date and value fields
                    sample = data[0]
                    date_key = next((k for k in sample.keys() if "data" in k.lower()), None)
                    value_key = next((k for k in sample.keys() if "valor" in k.lower()), None)

                    if date_key and value_key:
                        logger.info(
                            "Using alternate keys: date='%s', value='%s'",
                            date_key,
                            value_key,
                        )
                        rate_data = next(
                            (item for item in data if item[date_key] == target_str),
                            None,
                        )
                    else:
                        raise ValueError(f"Cannot identify date/value fields in: {sample}") from e
                else:
                    raise ValueError(f"Invalid data structure: {data[:2]}") from e

            if not rate_data and data:
                # If no exact match found, use the latest date
                logger.debug("No exact date match found, using latest available data")
                # Sort by date (most recent last) and get the last item
                try:
                    # Try standard format first
                    sorted_data = sorted(
                        data,
                        key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y").date(),
                    )
                except (KeyError, ValueError) as e:
                    logger.warning("Error sorting data: %s. Trying alternate format.", e)
                    # Try to identify the date field
                    if data and isinstance(data[0], dict):
                        sample = data[0]
                        date_key = next((k for k in sample.keys() if "data" in k.lower()), None)
                        if date_key:
                            sorted_data = sorted(
                                data,
                                key=lambda x: datetime.strptime(x[date_key], "%d/%m/%Y").date(),
                            )
                        else:
                            logger.error("Cannot find date field in: %s", sample)
                            # Last resort: just use the last item
                            sorted_data = data
                    else:
                        # Just use as is if we can't sort
                        sorted_data = data

                rate_data = sorted_data[-1] if sorted_data else None

            if not rate_data:
                raise ValueError("No suitable data found in response")

            try:
                # Try standard format
                rate_str = rate_data["valor"].replace(",", ".")
            except (KeyError, TypeError) as e:
                logger.warning("Error extracting rate value: %s. Trying alternate format.", e)
                # Try alternate format
                if isinstance(rate_data, dict):
                    # Try to identify the value field
                    value_key = next((k for k in rate_data.keys() if "valor" in k.lower()), None)
                    if value_key:
                        rate_str = rate_data[value_key]
                        # Handle different number formats (comma or dot as decimal separator)
                        if isinstance(rate_str, str):
                            rate_str = rate_str.replace(",", ".")
                        else:
                            rate_str = str(rate_str)
                    else:
                        logger.error("Cannot find value field in: %s", rate_data)
                        raise ValueError("Cannot extract rate value") from e
                else:
                    logger.error("Rate data is not a dictionary: %s", rate_data)
                    raise ValueError("Invalid rate data format") from e

            # BCB API returns SELIC as daily percentage
            # Converting from percentage to decimal
            daily_rate = float(rate_str) / 100

            # Convert daily rate to annual rate: (1 + r_d)^252 - 1
            # Brazil uses 252 business days for CDI and SELIC calculations
            annual_rate = ((1 + daily_rate) ** self.BUSINESS_DAYS_IN_YEAR) - 1

            # Sanity check the rate
            if annual_rate <= 0:
                raise ValueError(f"Retrieved SELIC rate ({annual_rate:.4f}) is non-positive")

            # SELIC is typically in the range of 5% to 20% annually
            if annual_rate < self.SELIC_MIN_EXPECTED or annual_rate > self.SELIC_MAX_EXPECTED:
                logger.warning(
                    "Retrieved SELIC rate (%.4f%%) may be outside typical range (%.1f-%.1f%%)",
                    annual_rate * 100,
                    self.SELIC_MIN_EXPECTED * 100,
                    self.SELIC_MAX_EXPECTED * 100,
                )

            logger.debug(
                "Retrieved SELIC rate: %.6f%% daily (%.4f%% annual) for date %s",
                daily_rate * 100,
                annual_rate * 100,
                rate_data.get("data", "unknown date"),
            )
            return annual_rate
        except Exception as e:
            logger.error("Error fetching SELIC rate: %s", str(e))
            raise ValueError(f"Failed to retrieve SELIC rate: {str(e)}") from e

    async def get_poupanca_rate(self, date_obj: date) -> float:
        """
        Get Poupança rate for the given date.

        Args:
            date_obj: Date to get the rate for

        Returns:
            Poupança rate as a decimal (annual rate)
        """
        logger.debug("Fetching Poupança rate for date: %s", date_obj)

        # Get today's actual date
        today = date.today()

        # CASE 1: Historical date - use actual API data
        if date_obj <= today:
            try:
                return await self._get_historical_poupanca_rate(date_obj)
            except ValueError as e:
                # For historical dates, if we can't get data, this is a real error
                logger.error("Cannot get historical Poupança data: %s", e)
                raise

        # CASE 2: Future date - calculate based on SELIC rate
        logger.info("Requested Poupança rate for future date: %s", date_obj)

        try:
            # Get SELIC rate for calculation
            selic_rate = await self.get_selic_rate(date_obj)

            # Poupança follows SELIC with rules set by Banco Central do Brasil:
            # - If SELIC is > 8.5% annually: Poupança = 0.5% monthly + TR (Taxa Referencial)
            # - If SELIC is <= 8.5% annually: Poupança = 70% of SELIC + TR
            #
            # Since TR is very close to zero in recent years, we can simplify:
            if selic_rate > self.POUPANCA_SELIC_THRESHOLD:  # 8.5%
                # 0.5% monthly = approx. 6.17% annually compounded
                monthly_rate = self.POUPANCA_MONTHLY_RATE  # 0.5% monthly
                annual_rate = ((1 + monthly_rate) ** 12) - 1
                logger.info(
                    "Calculated future Poupança rate as %.2f%% monthly (%.4f%% annual) for date %s (SELIC > %.1f%%)",
                    self.POUPANCA_MONTHLY_RATE * 100,
                    annual_rate * 100,
                    date_obj,
                    self.POUPANCA_SELIC_THRESHOLD * 100,
                )
            else:
                # 70% of SELIC
                annual_rate = selic_rate * self.POUPANCA_SELIC_FACTOR
                logger.info(
                    "Calculated future Poupança rate as %.0f%% of SELIC (%.4f%%) = %.4f%% for date %s",
                    self.POUPANCA_SELIC_FACTOR * 100,
                    selic_rate * 100,
                    annual_rate * 100,
                    date_obj,
                )

            # Sanity check
            if annual_rate <= 0:
                raise ValueError(f"Calculated Poupança rate ({annual_rate:.4f}) is non-positive")

            return annual_rate

        except Exception as e:
            logger.error("Failed to calculate Poupança rate for future date: %s", e)
            raise ValueError(f"Failed to calculate Poupança rate: {str(e)}") from e

    async def _get_historical_poupanca_rate(
        self, date_obj: date, historical_start_date: Optional[date] = None
    ) -> float:
        """
        Get historical Poupança rate from the API.

        Args:
            date_obj: The date to get the rate for
            historical_start_date: Optional start date to use for the API request
                                  (useful when getting patterns for future predictions)
        """
        reference_date = self._get_reference_date(date_obj, InvestmentType.POUPANCA)
        logger.debug("Using reference date: %s", reference_date)

        # Use the provided date range or calculate from reference date
        if self.start_date and self.end_date:
            start_date = self.start_date
            end_date = self.end_date
            logger.debug("Using provided date range: %s to %s", start_date, end_date)
        elif historical_start_date:
            # Use the historical date range provided (for future date predictions)
            start_date = historical_start_date
            end_date = date_obj
            logger.debug("Using historical date range: %s to %s", start_date, end_date)
        else:
            # For Poupança, we need a broader range since it's often reported with a delay
            start_date = reference_date - timedelta(days=15)
            end_date = reference_date + timedelta(days=15)
            logger.debug("Using calculated date range: %s to %s", start_date, end_date)

        # Make sure we're not using future dates in the API request
        today = date.today()
        if start_date > today:
            logger.warning(
                "Adjusting future start date %s to today %s for API request",
                start_date,
                today,
            )
            start_date = today - timedelta(days=30)  # Use last 30 days of data
        if end_date > today:
            logger.warning(
                "Adjusting future end date %s to today %s for API request",
                end_date,
                today,
            )
            end_date = today

        formatted_start = start_date.strftime("%d/%m/%Y")
        formatted_end = end_date.strftime("%d/%m/%Y")
        logger.debug("Using date range: %s to %s", formatted_start, formatted_end)

        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{self.SERIES_POUPANCA}/dados"
            f"?formato=json&dataInicial={formatted_start}&dataFinal={formatted_end}"
        )
        logger.debug("Requesting Poupança rate from URL: %s", url)

        try:
            data = await self._make_request(url)
            if not data:
                raise ValueError("Empty response from BCB API")

            # Find the rate closest to our target date
            target_str = reference_date.strftime("%d/%m/%Y")

            # Try to find exact match, otherwise use the latest date
            rate_data = next((item for item in data if item["data"] == target_str), None)

            if not rate_data and data:
                # If no exact match found, use the closest date
                logger.debug("No exact date match found, using closest available data")
                # Sort by date (most recent last)
                sorted_data = sorted(data, key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y").date())

                # Find the closest date to our reference date
                reference_dt = datetime.combine(reference_date, datetime.min.time())
                closest_idx = min(
                    range(len(sorted_data)),
                    key=lambda i: abs(reference_dt - datetime.strptime(sorted_data[i]["data"], "%d/%m/%Y")),
                )
                rate_data = sorted_data[closest_idx]

            if not rate_data:
                raise ValueError("No suitable Poupança data found in response")

            # Get the rate value
            rate_str = rate_data["valor"].replace(",", ".")

            # BCB API returns Poupança rate as monthly percentage
            monthly_rate = float(rate_str) / 100

            # Convert monthly rate to annual rate: (1 + r_m)^12 - 1
            annual_rate = ((1 + monthly_rate) ** 12) - 1

            # Sanity check
            if annual_rate <= 0:
                raise ValueError(f"Retrieved Poupança rate ({annual_rate:.4f}) is non-positive")

            logger.debug(
                "Retrieved Poupança rate: %.4f%% monthly (%.4f%% annual) for date %s",
                monthly_rate * 100,
                annual_rate * 100,
                rate_data["data"],
            )
            return annual_rate
        except Exception as e:
            logger.error("Error fetching Poupança rate: %s", str(e))
            raise ValueError(f"Failed to retrieve Poupança rate: {str(e)}") from e

    def _get_reference_date(
        self,
        target_date: date,
        investment_type: InvestmentType | None = None,
    ) -> date:
        """
        Get the reference date for rate lookups, adjusting for weekends and holidays.

        Args:
            target_date: Date to get the reference for
            investment_type: Type of investment (optional)

        Returns:
            Adjusted reference date
        """
        # Use the system's actual date instead of hardcoded value
        today = date.today()

        # If target date is in the future, use today
        target_date = min(target_date, today)

        # For CDB investments, if target date is a weekend or holiday, find the last working day
        if (
            investment_type in (InvestmentType.CDB, InvestmentType.CDI, InvestmentType.IPCA)
            and target_date.weekday() >= 5
        ):  # Saturday (5) or Sunday (6)
            while target_date.weekday() >= 5:  # Saturday (5) or Sunday (6)
                target_date = target_date - timedelta(days=1)
                logger.debug(
                    "Investment on weekend/holiday, using previous day: %s",
                    target_date,
                )

        return target_date

    async def get_ipca_rate(self, date_obj: date) -> float:
        """
        Get IPCA (inflation) rate for the given date.

        Args:
            date_obj: Date to get the rate for

        Returns:
            IPCA rate as a decimal (annual rate)
        """
        logger.debug("Fetching IPCA rate for date: %s", date_obj)

        # Get today's actual date
        today = date.today()

        # CASE 1: Historical date - use actual API data
        if date_obj <= today:
            try:
                return await self._get_historical_ipca_rate(date_obj)
            except ValueError as e:
                # For historical dates, if we can't get data, this is a real error
                logger.error("Cannot get historical IPCA data: %s", e)
                raise

        # CASE 2: Future date - use a pattern from the past with the same length
        logger.info("Requested IPCA rate for future date: %s", date_obj)
        days_in_future = (date_obj - today).days

        # Calculate the equivalent past date range with same length
        past_end_date = today
        past_start_date = today - timedelta(days=days_in_future)

        # Log that we're using historical patterns for prediction
        logger.info(
            "Using historical pattern from %s to %s to predict future date %s",
            past_start_date,
            past_end_date,
            date_obj,
        )

        # Since IPCA is monthly, we need the monthly rate from the same month last year
        try:
            # Try to get the rate from the same month last year
            same_month_last_year = date(date_obj.year - 1, date_obj.month, 1)
            historical_rate = await self._get_historical_ipca_rate(same_month_last_year)
            logger.info(
                "Using IPCA from %s (%.4f%%) as prediction for %s",
                same_month_last_year,
                historical_rate * 100,
                date_obj,
            )
            return historical_rate
        except ValueError as hist_error:
            logger.warning(
                "Could not get IPCA from same month last year, trying 12-month average: %s",
                str(hist_error),
            )

            # Get average IPCA for the last 12 months
            rates = []
            errors = []
            for i in range(1, 13):
                past_date = today - timedelta(days=30 * i)
                try:
                    rate = await self._get_historical_ipca_rate(past_date)
                    rates.append(rate)
                except (ValueError, KeyError, TypeError) as month_error:
                    # Skip months we can't get data for
                    errors.append(str(month_error))

            if rates:
                avg_rate = sum(rates) / len(rates)
                logger.info(
                    "Using average IPCA from last %d months (%.4f%%) as prediction for %s",
                    len(rates),
                    avg_rate * 100,
                    date_obj,
                )
                return avg_rate

            # If we couldn't get any data, this is a real error
            raise ValueError(f"Failed to get IPCA data for prediction. Errors: {'; '.join(errors)}") from hist_error

    async def _get_historical_ipca_rate(self, date_obj: date, historical_start_date: Optional[date] = None) -> float:
        """
        Get historical IPCA rate from the API.

        Args:
            date_obj: The date to get the rate for
            historical_start_date: Optional start date to use for the API request
                                  (useful when getting patterns for future predictions)
        """
        reference_date = self._get_reference_date(date_obj, InvestmentType.IPCA)
        logger.debug("Using reference date: %s", reference_date)

        # For IPCA, we need to use month boundaries because IPCA is reported monthly
        # Get the first day of the month for start_date
        if historical_start_date:
            # Use the historical date provided, but make sure it's the first of the month
            start_date = date(historical_start_date.year, historical_start_date.month, 1)
        else:
            start_date = date(reference_date.year, reference_date.month, 1)

        # For end_date, use the first day of the next month
        if reference_date.month == 12:
            end_date = date(reference_date.year + 1, 1, 1)
        else:
            end_date = date(reference_date.year, reference_date.month + 1, 1)

        # Make sure we're not using future dates in the API request
        today = date.today()
        if start_date > today:
            logger.warning(
                "Adjusting future start date %s to first of current month for API request",
                start_date,
            )
            start_date = date(today.year, today.month, 1)
        if end_date > today:
            logger.warning(
                "Adjusting future end date %s to today %s for API request",
                end_date,
                today,
            )
            # For IPCA, if the end month is in the future, use current month
            if today.month == 1:
                end_date = date(today.year - 1, 12, 1)
            else:
                end_date = date(today.year, today.month, 1)

        formatted_start = start_date.strftime("%d/%m/%Y")
        formatted_end = end_date.strftime("%d/%m/%Y")
        logger.debug("Using date range: %s to %s", formatted_start, formatted_end)

        # Fixed URL format to match the working example from BCB API
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{self.SERIES_IPCA}/dados"
            f"?formato=json&dataInicial={formatted_start}&dataFinal={formatted_end}"
        )
        logger.debug("Requesting IPCA rate from URL: %s", url)

        try:
            # Try to get data from the API
            data = await self._make_request(url)
            if not data:
                raise ValueError("Empty response from BCB API")

            # Check if we got data for the month we're looking for
            # IPCA is reported as the inflation for the entire month
            # So we need to find the entry for the month of the reference date
            month_str = f"01/{reference_date.month:02d}/{reference_date.year}"
            rate_data = next((item for item in data if item["data"] == month_str), None)

            if rate_data:
                # Found data for the exact month
                # BCB API returns IPCA as monthly percentage
                monthly_rate = float(rate_data["valor"].replace(",", ".")) / 100

                # Convert monthly rate to annual: (1 + r_m)^12 - 1
                annual_rate = ((1 + monthly_rate) ** 12) - 1

                logger.debug(
                    "Retrieved IPCA rate for %s: %.4f%% monthly (%.4f%% annual)",
                    month_str,
                    monthly_rate * 100,
                    annual_rate * 100,
                )
                return annual_rate

            # If we couldn't find the exact month, but have data, use the latest available
            if data:
                # Sort by date (most recent last)
                sorted_data = sorted(data, key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y").date())
                # Get the most recent entry
                latest_data = sorted_data[-1]
                monthly_rate = float(latest_data["valor"].replace(",", ".")) / 100

                # Convert monthly rate to annual: (1 + r_m)^12 - 1
                annual_rate = ((1 + monthly_rate) ** 12) - 1

                logger.debug(
                    "Using most recent IPCA rate from %s: %.4f%% monthly (%.4f%% annual)",
                    latest_data["data"],
                    monthly_rate * 100,
                    annual_rate * 100,
                )
                return annual_rate

            # If we get here, the API didn't have any data
            raise ValueError("No IPCA data available for the requested period")

        except Exception as e:
            # Propagate the error to caller
            raise ValueError(f"Failed to retrieve historical IPCA rate for {date_obj}: {str(e)}") from e

    async def get_cdi_rate(self, date_obj: date) -> float:
        """
        Get CDI rate for the given date.

        Args:
            date_obj: Date to get the rate for

        Returns:
            CDI rate as a decimal (annual rate)
        """
        logger.debug("Fetching CDI rate for date: %s", date_obj)

        # Get today's actual date
        today = date.today()

        # CASE 1: Historical date - use actual API data
        if date_obj <= today:
            try:
                return await self._get_historical_cdi_rate(date_obj)
            except ValueError as e:
                # For historical dates, if we can't get data, this is a real error
                logger.error("Cannot get historical CDI data: %s", e)
                raise

        # CASE 2: Future date - use the future SELIC rate to calculate CDI
        logger.info("Requested CDI rate for future date: %s", date_obj)

        try:
            # CDI closely follows SELIC with a slight discount
            # Get the predicted SELIC rate for the target date
            future_selic = await self.get_selic_rate(date_obj)

            # CDI is typically about 0.1 percentage points below SELIC
            # Using 0.001 (0.1%) as the discount from SELIC to CDI
            cdi_rate = max(0, future_selic - 0.001)

            logger.info(
                "Calculated future CDI rate of %.4f%% based on SELIC %.4f%% for %s",
                cdi_rate * 100,
                future_selic * 100,
                date_obj,
            )

            # Sanity check
            if cdi_rate <= 0:
                raise ValueError(f"Calculated CDI rate ({cdi_rate:.4f}) is non-positive")

            return cdi_rate

        except Exception as e:
            logger.error("Failed to calculate CDI rate for future date: %s", e)
            raise ValueError(f"Failed to calculate CDI rate: {str(e)}") from e

    async def _get_historical_cdi_rate(self, date_obj: date, historical_start_date: Optional[date] = None) -> float:
        """
        Get historical CDI rate from the API.

        Args:
            date_obj: The date to get the rate for
            historical_start_date: Optional start date to use for the API request
                                  (useful when getting patterns for future predictions)
        """
        reference_date = self._get_reference_date(date_obj, InvestmentType.CDI)
        logger.debug("Using reference date: %s", reference_date)

        # Use the provided date range or calculate from reference date
        if self.start_date and self.end_date:
            start_date = self.start_date
            end_date = self.end_date
            logger.debug("Using provided date range: %s to %s", start_date, end_date)
        elif historical_start_date:
            # Use the historical date range provided (for future date predictions)
            start_date = historical_start_date
            end_date = date_obj
            logger.debug("Using historical date range: %s to %s", start_date, end_date)
        else:
            start_date = reference_date - timedelta(days=5)
            end_date = reference_date + timedelta(days=5)
            logger.debug("Using calculated date range: %s to %s", start_date, end_date)

        # Make sure we're not using future dates in the API request
        today = date.today()
        if start_date > today:
            logger.warning(
                "Adjusting future start date %s to today %s for API request",
                start_date,
                today,
            )
            start_date = today - timedelta(days=30)  # Use last 30 days of data
        if end_date > today:
            logger.warning(
                "Adjusting future end date %s to today %s for API request",
                end_date,
                today,
            )
            end_date = today

        formatted_start = start_date.strftime("%d/%m/%Y")
        formatted_end = end_date.strftime("%d/%m/%Y")
        logger.debug("Using date range: %s to %s", formatted_start, formatted_end)

        # Fixed URL format to match the working example from BCB API
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{self.SERIES_CDI}/dados"
            f"?formato=json&dataInicial={formatted_start}&dataFinal={formatted_end}"
        )
        logger.debug("Requesting CDI rate from URL: %s", url)

        try:
            data = await self._make_request(url)
            if not data:
                raise ValueError("Empty response from BCB API")

            # Handle the case where data is empty
            if not data:
                raise ValueError("API returned empty data")

            # Find the rate closest to our target date
            target_str = reference_date.strftime("%d/%m/%Y")

            # Try to find exact match, otherwise use the latest date
            rate_data = next((item for item in data if item["data"] == target_str), None)

            if not rate_data and data:
                # If no exact match found, use the latest date
                logger.debug("No exact date match found, using latest available data")
                # Sort by date (most recent last) and get the last item
                sorted_data = sorted(data, key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y").date())
                rate_data = sorted_data[-1] if sorted_data else None

            if not rate_data:
                raise ValueError("No suitable data found in response")

            # Get the rate value
            rate_str = rate_data["valor"].replace(",", ".")

            # BCB API returns CDI as daily percentage
            # Converting from percentage to decimal
            daily_rate = float(rate_str) / 100

            # Convert daily rate to annual rate: (1 + r_d)^252 - 1
            # Brazil uses 252 business days for CDI calculations
            annual_rate = ((1 + daily_rate) ** self.BUSINESS_DAYS_IN_YEAR) - 1

            # Sanity check the rate
            if annual_rate <= 0:
                raise ValueError(f"Retrieved CDI rate ({annual_rate:.4f}) is non-positive")

            logger.debug(
                "Retrieved CDI rate: %.6f%% daily (%.4f%% annual) for date %s",
                daily_rate * 100,
                annual_rate * 100,
                rate_data["data"],
            )
            return annual_rate
        except Exception as e:
            logger.error("Error fetching CDI rate: %s", str(e))
            raise ValueError(f"Failed to retrieve CDI rate: {str(e)}") from e

    async def _predict_ipca_rate(self, target_date: date) -> float:
        """Predict IPCA rate for a future date."""
        try:
            # Get historical IPCA data
            historical_data = await self._get_historical_ipca_data()
            if not historical_data:
                raise ValueError("No historical IPCA data available")

            # Calculate days until target date
            days_forward = (target_date - historical_data[-1]["date"]).days
            if days_forward <= 0:
                raise ValueError("Target date must be in the future")

            # Calculate volatility from historical data
            returns = []
            for i in range(1, len(historical_data)):
                daily_return = (historical_data[i]["rate"] - historical_data[i - 1]["rate"]) / historical_data[i - 1][
                    "rate"
                ]
                returns.append(daily_return)

            if not returns:
                raise ValueError("Insufficient historical data for volatility calculation")

            volatility = (sum(r * r for r in returns) / len(returns)) ** 0.5

            # Get current rate as base
            base_rate = historical_data[-1]["rate"]

            # Project rate using random walk with drift
            # Using a small drift to account for market expectations
            drift = 0.0001  # 0.01% daily drift
            projected_rate = base_rate * (1 + drift) ** days_forward

            # Add some randomness based on volatility
            random_factor = 1 + (volatility * (days_forward**0.5))
            projected_rate *= random_factor

            # Apply sanity checks
            projected_rate = max(min(projected_rate, 0.15), 0.02)  # Between 2% and 15%

            logger.debug(
                "Projected IPCA rate for %s: %.2f%% (base: %.2f%%, volatility: %.2f%%, days: %d)",
                target_date,
                projected_rate * 100,
                base_rate * 100,
                volatility * 100,
                days_forward,
            )

            return projected_rate

        except ValueError as predict_error:
            # Re-raise specific ValueError errors with better context
            raise ValueError(f"Failed to predict IPCA rate: {str(predict_error)}") from predict_error
        except (TypeError, IndexError, KeyError) as data_error:
            # Handle data structure errors
            raise ValueError(f"Data error while predicting IPCA rate: {str(data_error)}") from data_error
        except Exception as general_error:
            # Catch other unexpected errors
            logger.error("Unexpected error predicting IPCA rate: %s", str(general_error))
            raise ValueError(f"Unexpected error predicting IPCA rate: {str(general_error)}") from general_error

    async def _get_historical_ipca_data(self) -> list:
        """
        Get historical IPCA data for calculations.

        Returns:
            List of dictionaries with 'date' and 'rate' keys
        """
        logger.debug("Fetching historical IPCA data")

        # Calculate date range for historical data (use last 24 months)
        today = date.today()
        start_date = date(today.year - 2, today.month, 1)
        end_date = today

        formatted_start = start_date.strftime("%d/%m/%Y")
        formatted_end = end_date.strftime("%d/%m/%Y")

        # Fixed URL format to match the working example from BCB API
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{self.SERIES_IPCA}/dados"
            f"?formato=json&dataInicial={formatted_start}&dataFinal={formatted_end}"
        )
        logger.debug("Requesting historical IPCA data from URL: %s", url)

        try:
            # Get the data from API
            data = await self._make_request(url)
            if not data:
                raise ValueError("Empty response from BCB API")

            # Process the data into a consistent format
            historical_data = []
            for item in data:
                # Convert date string to date object
                date_obj = datetime.strptime(item["data"], "%d/%m/%Y").date()

                # Parse the rate (BCB API returns as percentage with comma as decimal separator)
                monthly_rate = float(item["valor"].replace(",", ".")) / 100

                # Convert monthly rate to annual: (1 + r_m)^12 - 1
                annual_rate = ((1 + monthly_rate) ** 12) - 1

                historical_data.append({"date": date_obj, "rate": annual_rate})

            # Define a sort key function with proper typing
            def get_date(item: dict[str, object]) -> date:
                return item["date"]  # type: ignore

            # Sort by date
            historical_data.sort(key=get_date)

            logger.debug("Retrieved %d historical IPCA data points", len(historical_data))
            return historical_data

        except Exception as e:
            logger.error("Error fetching historical IPCA data: %s", str(e))
            raise ValueError(f"Failed to retrieve historical IPCA data: {str(e)}") from e
