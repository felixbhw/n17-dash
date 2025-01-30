from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
import os
import logging
from ..background import background_tasks
from typing import Dict

router = APIRouter()

logger = logging.getLogger(__name__)

# Helper function to load JSON data
def load_json_file(file_path: Path) -> dict:
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/squad")
async def get_squad():
    """Get all players in the squad."""
    # Get absolute path to data directory - fix the path resolution
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data" / "players"
    
    # Log the path we're checking
    logger.info(f"Looking for player data in: {data_dir}")
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        raise HTTPException(status_code=500, detail="Player data directory not found")
    
    files = list(data_dir.glob("*.json"))
    logger.info(f"Found {len(files)} player files")
    
    players = []
    
    try:
        for file_path in files:
            logger.info(f"Reading player file: {file_path}")
            player_data = load_json_file(file_path)
            players.append({
                "id": player_data.get("id"),
                "name": player_data.get("name"),
                "number": player_data.get("number"),
                "position": player_data.get("position"),
                "age": player_data.get("age"),
                "photo": player_data.get("photo")
            })
        return players
    except Exception as e:
        logger.error(f"Error reading player data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/player/{player_id}")
async def get_player(player_id: str):
    """Get detailed information about a specific player."""
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data" / "stats"
    player_file = data_dir / f"player_{player_id}.json"
    
    # Add detailed logging
    logger.info(f"Base directory: {base_dir}")
    logger.info(f"Looking for player file at: {player_file}")
    
    # List all available files to help debug
    available_files = list(data_dir.glob("player_*.json"))
    logger.info(f"Available player files in stats: {[f.name for f in available_files]}")
    
    if not player_file.exists():
        # If the stats file doesn't exist, try to get basic info from players directory
        players_dir = base_dir / "data" / "players"
        basic_file = players_dir / f"{player_id}.json"
        
        if basic_file.exists():
            player_data = load_json_file(basic_file)
            return {
                "id": player_data.get("id"),
                "name": player_data.get("name"),
                "firstname": None,
                "lastname": None,
                "age": player_data.get("age"),
                "birth": {},
                "nationality": None,
                "height": None,
                "weight": None,
                "injured": False,
                "photo": player_data.get("photo")
            }
    
    try:
        data = load_json_file(player_file)
        return data["player"]
    except Exception as e:
        logger.error(f"Error loading player {player_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Player not found: {str(e)}")

@router.get("/stats/{player_id}")
async def get_player_stats(player_id: str):
    """Get statistics for a specific player."""
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data" / "stats"
    stats_file = data_dir / f"player_{player_id}.json"
    
    # Add detailed logging
    logger.info(f"Base directory: {base_dir}")
    logger.info(f"Looking for stats file at: {stats_file}")
    logger.info(f"File exists: {stats_file.exists()}")
    
    try:
        data = load_json_file(stats_file)
        # Return just the statistics array from the file
        return data["statistics"]
    except Exception as e:
        logger.error(f"Error loading stats for player {player_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Stats not found: {str(e)}")

@router.post("/reddit/fetch-historical")
async def fetch_historical_posts(days: int = 7) -> Dict[str, int]:
    """Fetch historical transfer posts from r/coys
    
    Args:
        days: Number of days to look back (default: 7)
    
    Returns:
        Stats about processed posts
    """
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 30")
    
    return await background_tasks.reddit_service.fetch_historical(days)
