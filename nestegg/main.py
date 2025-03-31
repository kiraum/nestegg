"""
Main FastAPI application module.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .calculator import InvestmentCalculator
from .config import API_CONFIG, CORS_CONFIG, INVESTMENT_DESCRIPTIONS, setup_logging
from .models import (
    InvestmentRequest,
    InvestmentResponse,
    InvestmentType,
)

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)

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

# Add CORS middleware
app.add_middleware(CORSMiddleware, **CORS_CONFIG)


# Application state
class AppState:
    """Holds application state including calculator instance."""

    calculator = None


APP_STATE = AppState()


@app.on_event("startup")
async def startup_event():
    """Initialize the calculator on startup."""
    logger.info("Starting up NestEgg API")
    APP_STATE.calculator = InvestmentCalculator()


@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Shutting down NestEgg API")
    if APP_STATE.calculator:
        await APP_STATE.calculator.close()
        logger.info("Closed calculator resources")


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

    For CDB investments, you must provide the CDB rate.
    For other investment types, the rate is fetched from BCB.
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
) -> InvestmentResponse:
    """
    Calculate investment returns for different Brazilian investment types.

    Args:
        investment_type: Type of investment (POUPANCA, SELIC, CDB, LCI, LCA)
        amount: Initial investment amount
        start_date: Start date for the investment period
        end_date: End date for the investment period
        cdb_rate: CDB rate as percentage (e.g., 12.5 for 12.5%)
        lci_rate: LCI rate as percentage (e.g., 11.0 for 11.0%)
        lca_rate: LCA rate as percentage (e.g., 10.5 for 10.5%)

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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


@api_router.post(
    "/compare",
    tags=["investments"],
    summary="Compare different investment types",
    description="""
    Compare returns between different investment types and provide recommendations.

    The comparison includes:
    * Poupança (always included)
    * SELIC (always included, can add spread with selic_spread parameter)
    * IPCA (always included, can add spread with ipca_spread parameter)
    * CDI (always included, can specify percentage with cdi_percentage parameter)
    * CDB (if rate provided)
    * LCI (if rate provided)
    * LCA (if rate provided)

    Results are sorted by effective rate and include tax implications.
    """,
    response_description="List of investment comparisons with recommendations",
)
async def compare_investments(
    amount: float,
    start_date: date,  # Required
    end_date: date,  # Required
    cdb_rate: Optional[float] = None,
    lci_rate: Optional[float] = None,
    lca_rate: Optional[float] = None,
    ipca_spread: float = 0.0,
    selic_spread: float = 0.0,
    cdi_percentage: float = 100.0,
):
    """
    Compare different investment types and provide recommendations.

    Args:
        amount: Initial investment amount
        start_date: Start date for the investment period
        end_date: End date for the investment period
        cdb_rate: CDB rate as percentage (e.g., 12.5 for 12.5%)
        lci_rate: LCI rate as percentage (e.g., 11.0 for 11.0%)
        lca_rate: LCA rate as percentage (e.g., 10.5 for 10.5%)
        ipca_spread: Spread to add to IPCA rate in percentage points (e.g., 5.0 for IPCA+5%)
        selic_spread: Spread to add to SELIC rate in percentage points (e.g., 3.0 for SELIC+3%)
        cdi_percentage: Percentage of CDI (e.g., 109.0 for 109% of CDI)

    Returns:
        List of investment comparisons with recommendations

    Raises:
        HTTPException: If comparison fails or parameters are invalid
    """
    try:
        # Calculate and log the period for information
        days = (end_date - start_date).days
        period_years = days / 365
        logger.debug(
            "Investment period: %.2f years (%d days)",
            period_years,
            days,
        )

        logger.info(
            "Comparing investments - Amount: R$ %.2f, Period: %.1f years",
            amount,
            period_years,
        )
        logger.info(
            "Rates - CDB: %.1f%%, LCI: %.1f%%, LCA: %.1f%%, IPCA+%.1f%%, SELIC+%.1f%%, %.1f%% of CDI",
            cdb_rate or 0,
            lci_rate or 0,
            lca_rate or 0,
            ipca_spread,
            selic_spread,
            cdi_percentage,
        )
        logger.info("Using date range: %s to %s", start_date, end_date)

        # Create a new calculator instance with the specified date range
        calc = InvestmentCalculator(start_date=start_date, end_date=end_date)
        results = await calc.compare_investments(
            initial_amount=amount,
            period_years=period_years,
            cdb_rate=cdb_rate,
            lci_rate=lci_rate,
            lca_rate=lca_rate,
            ipca_spread=ipca_spread,
            selic_spread=selic_spread,
            cdi_percentage=cdi_percentage,
        )

        return results

    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# Include the API router in the main app
app.include_router(api_router)
