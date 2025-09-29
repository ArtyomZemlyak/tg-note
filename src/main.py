"""Main application entry point."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from src.config.settings import settings


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting TG-Note application", environment=settings.environment)
    
    # Initialize database
    # TODO: Add database initialization
    
    # Initialize Redis connection
    # TODO: Add Redis initialization
    
    # Start Telegram bot
    # TODO: Add bot initialization
    
    yield
    
    # Cleanup
    logger.info("Shutting down TG-Note application")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="TG-Note API",
        description="Intelligent Telegram Bot for Knowledge Management",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "environment": settings.environment}
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "TG-Note API is running"}
    
    # TODO: Add webhook endpoint for Telegram
    # TODO: Add API endpoints for management
    
    return app


def main():
    """Main function."""
    if not settings.has_ai_service:
        logger.error("No AI service configured. Please set up OpenAI, Anthropic, or Ollama.")
        sys.exit(1)
    
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()