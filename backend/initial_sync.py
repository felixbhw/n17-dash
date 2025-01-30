"""
Initial data sync script for N17 Dashboard
This script performs the first sync of Tottenham squad data from API-Football.
"""

import asyncio
import logging
from datetime import datetime
from football_api import SimpleFootballAPI
import json
from pathlib import Path

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
        await sync_players()
        logger.info("✓ Squad data synced")
        
        # Calculate and log total time
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Initial sync completed in {duration.total_seconds():.1f} seconds")
        
        # Print summary
        logger.info("\nData sync summary:")
        
        # Show squad info from the data files instead of api
        player_dir = Path("data/players")
        players = []
        for file in player_dir.glob("*.json"):
            with open(file) as f:
                players.append(json.load(f))
        logger.info(f"Players synced: {len(players)}")
        for player in players:
            logger.info(f"- {player['name']} ({player['position']})")
        
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        raise

async def sync_players():
    logger.info("Syncing players...")
    
    # Ensure data directory exists
    player_dir = Path("data/players")
    player_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create API client
        api = SimpleFootballAPI()
        
        # Get squad data from API
        squad = await api.get_squad()
        
        # Clear existing player files
        for file in player_dir.glob("*.json"):
            file.unlink()
        
        # Save each player
        for player in squad:
            player_file = player_dir / f"{player['id']}.json"
            logger.info(f"Saving player {player['name']} to {player_file}")
            
            with open(player_file, "w") as f:
                json.dump(player, f, indent=2)
        
        logger.info(f"Players synced: {len(squad)}")
    except Exception as e:
        logger.error(f"Error syncing players: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_initial_sync()) 