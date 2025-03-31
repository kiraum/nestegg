"""
Command-line interface for the NestEgg application.
"""

import logging

import typer
import uvicorn

from .config import setup_logging

# Configure logging
setup_logging()

logger = logging.getLogger(__name__)

cli = typer.Typer()


@cli.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    debug: bool = False,
):
    """
    Start the NestEgg API server.

    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload
        debug: Enable debug mode
    """
    logger.info("Starting NestEgg API server")
    logger.debug(
        "Server configuration - host: %s, port: %d, reload: %s, debug: %s",
        host,
        port,
        reload,
        debug,
    )

    uvicorn.run(
        "nestegg.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug" if debug else "info",
    )


if __name__ == "__main__":
    cli()
