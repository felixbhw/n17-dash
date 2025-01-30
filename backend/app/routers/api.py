from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
import os

router = APIRouter()

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
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "players"
    players = []
    
    try:
        for file_path in data_dir.glob("*.json"):
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
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/player/{player_id}")
async def get_player(player_id: str):
    """Get detailed information about a specific player."""
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "players"
    player_file = data_dir / f"{player_id}.json"
    
    try:
        return load_json_file(player_file)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Player not found: {str(e)}")

@router.get("/stats/{player_id}")
async def get_player_stats(player_id: str):
    """Get statistics for a specific player."""
    data_dir = Path(__file__).parent.parent.parent.parent / "data" / "stats"
    stats_file = data_dir / f"player_{player_id}.json"
    
    try:
        return load_json_file(stats_file)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Stats not found: {str(e)}")
