"""
Main FastAPI application module.
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .calculator import InvestmentCalculator
from .config import API_CONFIG, CORS_CONFIG, INVESTMENT_DESCRIPTIONS, setup_logging
from .external_api import CryptoApiClient
from .models import (
    InvestmentComparisonResult,
    InvestmentRequest,
    InvestmentResponse,
    InvestmentType,
)

# Check if debug mode is enabled via command line arguments or environment variable
debug_mode = "--debug" in sys.argv or os.environ.get("DEBUG", "").lower() in (
    "1",
    "true",
    "yes",
)

# Setup logging with the appropriate debug level
setup_logging(debug=debug_mode)

# Create Jinja2 templates instance
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

logger = logging.getLogger(__name__)
if debug_mode:
    logger.info("Debug logging enabled")
else:
    logger.info("Debug logging disabled (use --debug to enable)")

# Create API router with prefix and tags
api_router = APIRouter(
    prefix=API_CONFIG["prefix"],
    responses={404: {"description": "Not found"}},
)

app = FastAPI(
    title=API_CONFIG["title"],
    description=API_CONFIG["description"],
    version=API_CONFIG["version"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Add CORS middleware
app.add_middleware(CORSMiddleware, **CORS_CONFIG)


# Application state
class AppState:
    """Holds application state including calculator instance."""

    calculator = None
    crypto_client = None


APP_STATE = AppState()


@app.on_event("startup")
async def startup_event():
    """Initialize the calculator on startup."""
    logger.info("Starting up NestEgg API")

    # Create a single crypto client instance to be shared across all requests
    APP_STATE.crypto_client = CryptoApiClient()
    # Mark this instance as shared so calculators don't close it
    APP_STATE.crypto_client.is_shared = True
    logger.info("Initialized shared crypto client for consistent pricing data")

    # Create the calculator with the shared crypto client
    APP_STATE.calculator = InvestmentCalculator(crypto_client=APP_STATE.crypto_client)
    logger.info("Initialized calculator with shared crypto client")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Shutting down NestEgg API")
    if APP_STATE.calculator:
        await APP_STATE.calculator.close()
        logger.info("Closed calculator resources")
    if APP_STATE.crypto_client:
        await APP_STATE.crypto_client.close()
        logger.info("Closed shared crypto client")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request, exc):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """Render the main UI page."""
    return templates.TemplateResponse("index.html", {"request": request})


@api_router.get(
    "/investment-types",
    tags=["investments"],
    summary="List supported investment types",
    description="""
    Returns a list of all supported investment types with their descriptions.

    Each investment type includes:
    * `id`: The value to use in API requests
    * `name`: A human-readable name
    * `description`: A detailed description of the investment type
    """,
    response_description="List of supported investment types",
)
async def list_investment_types():
    """
    List all supported investment types with their descriptions.

    Returns:
        List of investment types with their descriptions
    """
    logger.debug("Listing supported investment types")
    types = [
        {
            "id": investment_type.value,
            "name": investment_type.name.title(),
            "description": INVESTMENT_DESCRIPTIONS[investment_type],
        }
        for investment_type in InvestmentType
    ]
    logger.debug("Found %d investment types", len(types))
    return types


@api_router.post(
    "/calculate",
    tags=["investments"],
    response_model=InvestmentResponse,
    summary="Calculate investment returns",
    description="""
    Calculate investment returns for different Brazilian investment types.

    The calculation considers:
    * Investment type and amount
    * Investment period
    * Current market rates from BCB
    * Applicable taxes based on investment type and period
    * For Bitcoin, real market prices from CoinGecko API

    For CDB investments, you must provide the CDB rate.
    For LCI/LCA investments, you must provide the respective rate.
    For CDI-based LCI/LCA (LCI_CDI/LCA_CDI), you must provide the cdi_percentage.
    For IPCA-based LCI/LCA (LCI_IPCA/LCA_IPCA), you must provide the ipca_spread.
    For other investment types, the rate is fetched from BCB or CoinGecko.
    """,
    response_description="Calculated investment returns including taxes",
)
async def calculate_investment(
    investment_type: str,  # Accept as string to handle case-insensitive conversion
    amount: float,
    start_date: date,  # Required
    end_date: date,  # Required
    cdb_rate: Optional[float] = None,
    lci_rate: Optional[float] = None,
    lca_rate: Optional[float] = None,
    ipca_spread: float = 0.0,
    selic_spread: float = 0.0,
    cdi_percentage: float = 100.0,
) -> InvestmentResponse:
    """
    Calculate investment returns for different Brazilian investment types.

    Args:
        investment_type: Type of investment
            (POUPANCA, SELIC, CDB, LCI, LCA, IPCA, CDI, BTC,
            LCI_CDI, LCA_CDI, LCI_IPCA, LCA_IPCA)
        amount: Initial investment amount
        start_date: Start date for the investment period
        end_date: End date for the investment period
        cdb_rate: CDB rate as percentage (e.g., 12.5 for 12.5%)
        lci_rate: LCI rate as percentage (e.g., 11.0 for 11.0%)
        lca_rate: LCA rate as percentage (e.g., 10.5 for 10.5%)
        ipca_spread: IPCA spread in percentage points (e.g., 5.0 for IPCA+5%)
        selic_spread: SELIC spread in percentage points (e.g., 3.0 for SELIC+3%)
        cdi_percentage: CDI percentage (e.g., 109.0 for 109% of CDI)

    Returns:
        InvestmentResponse with calculated values

    Raises:
        HTTPException: If calculation fails or parameters are invalid
    """
    try:
        # Convert investment_type to enum (case-insensitive)
        try:
            investment_type_enum = InvestmentType(investment_type.lower())
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid investment type: {investment_type}. "
                f"Must be one of: {', '.join(t.value for t in InvestmentType)}",
            ) from exc

        # Log the calculated period (now handled by the model)
        days = (end_date - start_date).days
        logger.debug(
            "Investment period: %.2f years (%d days)",
            days / 365,
            days,
        )

        request = InvestmentRequest(
            investment_type=investment_type_enum,
            initial_amount=amount,
            cdb_rate=cdb_rate,
            lci_rate=lci_rate,
            lca_rate=lca_rate,
            ipca_spread=ipca_spread,
            selic_spread=selic_spread,
            cdi_percentage=cdi_percentage,
            start_date=start_date,
            end_date=end_date,
        )
        if APP_STATE.calculator is None:
            raise HTTPException(
                status_code=500,
                detail="Calculator not initialized. Please try again later.",
            )
        return await APP_STATE.calculator.calculate_investment(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Failed to calculate investment: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


def get_calculator():
    """Get the initialized calculator instance from app state."""
    if APP_STATE.calculator is None:
        raise HTTPException(
            status_code=500,
            detail="Calculator not initialized. Please try again later.",
        )
    return APP_STATE.calculator


@app.get("/api/v1/compare", response_model=list[InvestmentComparisonResult])
async def compare_investments_endpoint(
    amount: float = Query(..., description="Amount to invest (R$)"),
    period: Optional[float] = Query(None, description="Investment period in years"),
    cdb_rate: Optional[float] = Query(None, description="CDB prefixed annual rate (%)"),
    lci_rate: Optional[float] = Query(None, description="LCI prefixed annual rate (%)"),
    lca_rate: Optional[float] = Query(None, description="LCA prefixed annual rate (%)"),
    ipca_spread: Optional[float] = Query(
        None, description="Spread to add to IPCA for IPCA+ investments (e.g., 5.5 for IPCA+5.5%)"
    ),
    selic_spread: Optional[float] = Query(
        None, description="Spread to add to SELIC for Tesouro SELIC investments (e.g., 0.2 for SELIC+0.2%)"
    ),
    cdi_percentage: Optional[float] = Query(
        None, description="Percentage of CDI for CDB investment (e.g., 110 for 110% of CDI)"
    ),
    lci_cdi_percentage: Optional[float] = Query(
        None, description="Percentage of CDI for LCI investment (e.g., 93 for 93% of CDI)"
    ),
    lca_cdi_percentage: Optional[float] = Query(
        None, description="Percentage of CDI for LCA investment (e.g., 95 for 95% of CDI)"
    ),
    lci_ipca_spread: Optional[float] = Query(
        None, description="Spread to add to IPCA for LCI_IPCA investment (e.g., 5.5 for IPCA+5.5%)"
    ),
    lca_ipca_spread: Optional[float] = Query(
        None, description="Spread to add to IPCA for LCA_IPCA investment (e.g., 5.5 for IPCA+5.5%)"
    ),
    cdb_ipca_spread: Optional[float] = Query(
        None, description="Spread to add to IPCA for CDB_IPCA investment (e.g., 5.5 for IPCA+5.5%)"
    ),
    include_poupanca: bool = Query(False, description="Whether to include Poupança in the comparison"),
    include_selic: bool = Query(
        False, description="Whether to include base SELIC (only needed if not providing selic_spread)"
    ),
    include_btc: bool = Query(False, description="Whether to include Bitcoin in the comparison"),
    include_cdb_ipca: bool = Query(
        False,
        description="Whether to include CDB_IPCA with default spread (only needed if not providing cdb_ipca_spread)",
    ),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Compare different investment types and provide the most profitable option.

    This endpoint allows comparing different investment types based on:
    - Initial investment amount
    - Time period
    - Different rates and parameters for investment types

    Investment types that can be compared:
    * Poupança (only if include_poupanca=true)
    * Tesouro SELIC (if provide selic_spread or include_selic=true)
    * CDB Prefixado (only if cdb_rate is provided)
    * CDB CDI (only if cdi_percentage is provided)
    * LCI Prefixado (only if lci_rate is provided)
    * LCA Prefixado (only if lca_rate is provided)
    * LCI CDI (only if lci_cdi_percentage is provided)
    * LCA CDI (only if lca_cdi_percentage is provided)
    * Tesouro IPCA+ (only if ipca_spread is provided)
    * LCI IPCA+ (only if lci_ipca_spread is provided)
    * LCA IPCA+ (only if lca_ipca_spread is provided)
    * CDB_IPCA (if provide cdb_ipca_spread or include_cdb_ipca=true)
    * Bitcoin (only if include_btc=true)

    Returns a list of investment options sorted by most profitable first.
    """
    # Set date format description for start_date and end_date
    if start_date is None:
        start_date = Query(None, description="Optional start date (format: YYYY-MM-DD)")
    if end_date is None:
        end_date = Query(None, description="Optional end date (format: YYYY-MM-DD)")

    # Validate input: either period or both dates must be provided
    if period is None and (start_date is None or end_date is None):
        raise HTTPException(
            status_code=400,
            detail="Either period or both start_date and end_date must be provided",
        )

    # If dates are provided but period is not, calculate period
    if period is None and start_date is not None and end_date is not None:
        days = (end_date - start_date).days
        period = days / 365
        logger.debug("Calculated period: %.2f years from dates %s to %s", period, start_date, end_date)

    logger.info(
        "Comparing investments: amount=R$ %.2f, period=%.1f years",
        amount,
        period,
    )

    # Log rates for investments being compared
    if cdb_rate is not None:
        logger.info("CDB Prefixado: %.1f%%", cdb_rate)
    if lci_rate is not None:
        logger.info("LCI Prefixado: %.1f%%", lci_rate)
    if lca_rate is not None:
        logger.info("LCA Prefixado: %.1f%%", lca_rate)
    if ipca_spread is not None:
        logger.info("IPCA+: %.1f%%", ipca_spread)
    if selic_spread is not None:
        logger.info("SELIC+: %.1f%%", selic_spread)
    if cdi_percentage is not None:
        logger.info("CDB CDI: %.1f%%", cdi_percentage)
    if lci_cdi_percentage is not None:
        logger.info("LCI CDI: %.1f%%", lci_cdi_percentage)
    if lca_cdi_percentage is not None:
        logger.info("LCA CDI: %.1f%%", lca_cdi_percentage)
    if lci_ipca_spread is not None:
        logger.info("LCI IPCA+: %.1f%%", lci_ipca_spread)
    if lca_ipca_spread is not None:
        logger.info("LCA IPCA+: %.1f%%", lca_ipca_spread)
    if cdb_ipca_spread is not None:
        logger.info("CDB_IPCA: IPCA+%.1f%%", cdb_ipca_spread)

    # Log inclusion flags
    include_info = []
    if include_poupanca:
        include_info.append("Poupança")
    if include_selic:
        include_info.append("SELIC")
    if cdi_percentage is not None:
        include_info.append("CDI")
    if include_btc:
        include_info.append("Bitcoin")
    if include_cdb_ipca:
        include_info.append("CDB_IPCA")

    if include_info:
        logger.info("Including: %s", ", ".join(include_info))

    try:
        # Get calculator instance
        calculator = get_calculator()

        # Compare investments
        results = await calculator.compare_investments(
            initial_amount=amount,
            period_years=period,
            cdb_rate=cdb_rate,
            lci_rate=lci_rate,
            lca_rate=lca_rate,
            ipca_spread=ipca_spread,
            selic_spread=selic_spread,
            cdi_percentage=cdi_percentage,
            lci_cdi_percentage=lci_cdi_percentage,
            lca_cdi_percentage=lca_cdi_percentage,
            lci_ipca_spread=lci_ipca_spread,
            lca_ipca_spread=lca_ipca_spread,
            cdb_ipca_spread=cdb_ipca_spread,
            include_poupanca=include_poupanca,
            include_selic=include_selic,
            include_btc=include_btc,
            include_cdb_ipca=include_cdb_ipca,
            start_date_param=start_date,
            end_date_param=end_date,
        )

        # Convert to response model and return
        return [
            InvestmentComparisonResult(
                type=result["type"],
                rate=float(result["rate"]),
                effective_rate=float(result["effective_rate"]),
                gross_profit=float(result["gross_profit"]),
                net_profit=float(result["net_profit"]),
                tax_amount=float(result["tax_amount"]),
                final_amount=float(result["final_amount"]),
                tax_free=bool(result["tax_free"]),
                fgc_coverage=bool(
                    result["fgc_coverage"].is_covered
                    if hasattr(result["fgc_coverage"], "is_covered")
                    else result["fgc_coverage"]
                ),
                recommendation=result.get("recommendation", ""),
            )
            for result in results
        ]
    except Exception as e:
        logger.error("Error comparing investments: %s", e, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Error comparing investments: {str(e)}",
        ) from e


# Include the API router in the main app
app.include_router(api_router)
