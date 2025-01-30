"""
Database initialization script for N17 Dashboard.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from .session import engine
from ..models import Base, Team
from ..pipeline.api_clients.football_api import APIFootballClient
from ..pipeline.data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)

async def init_db() -> None:
    """Initialize database with tables and initial data."""
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Created database tables")
        
        # Initialize API client
        api_client = APIFootballClient()
        
        # Create async session
        async with AsyncSession(engine) as session:
            # Initialize ingestion service
            ingestion_service = DataIngestionService(api_client, session)
            
            # Perform initial sync for Tottenham (ID: 47)
            results = await ingestion_service.perform_initial_sync()
            
            if results['team']:
                logger.info(
                    f"Initial sync completed successfully:\n"
                    f"Players: {len(results['players'])}\n"
                    f"Injuries: {len(results['injuries'])}\n"
                    f"Matches: {len(results['matches'])}\n"
                    f"Transfers: {len(results['transfers'])}"
                )
            else:
                logger.error("Failed to sync initial team data")
                
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(init_db()) 