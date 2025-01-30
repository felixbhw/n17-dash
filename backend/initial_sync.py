"""
Initial data sync script for N17 Dashboard
This script performs the first sync of Tottenham squad data from API-Football.
"""

import asyncio
import logging
from datetime import datetime
from football_api import SimpleFootballAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_initial_sync():
    """Run the initial sync of squad data."""
    try:
        logger.info("Starting initial squad data sync...")
        start_time = datetime.now()
        
        # Create API client
        api = SimpleFootballAPI()
        
        # Get squad data (includes player stats)
        logger.info("Fetching squad data...")
        await api.update_squad()
        logger.info("✓ Squad data synced")
        
        # Calculate and log total time
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Initial sync completed in {duration.total_seconds():.1f} seconds")
        
        # Print summary
        logger.info("\nData sync summary:")
        
        # Show squad info
        players = api.get_all_players()
        logger.info(f"Players synced: {len(players)}")
        for player in players:
            logger.info(f"- {player['name']} ({player['position']})")
        
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_initial_sync()) 