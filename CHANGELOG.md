# Changelog

All notable changes to nestegg will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2025-4-01
### Added
- Initial development release
- FastAPI application for comparing Brazilian investment indexes
- Support for multiple investment types (Poupança, SELIC, CDB, LCI, LCA, IPCA+, CDI, Bitcoin)
- Automatic tax calculation based on Brazilian tax rules
- Historical data fetching from Brazilian Central Bank (BCB) API
- Bitcoin price data from CryptoCompare API
- Future rate projections based on historical volatility and trends
- Compare endpoint for side-by-side investment comparisons
- Calculate endpoint for detailed analysis of single investments
- Comprehensive error handling and logging
- Type safety with mypy integration
- Robust API documentation with OpenAPI/Swagger

### Dependencies
- fastapi for API framework
- uvicorn for ASGI server
- pydantic for data validation
- httpx for async HTTP requests
- backoff for API request retries
- python-dateutil for date operations
- typer for CLI interface

[0.0.1 ⋅ Release]: https://github.com/kiraum/nestegg/releases/tag/v0.0.1
