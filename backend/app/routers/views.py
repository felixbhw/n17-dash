from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

# Get absolute path to templates directory
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/player/{player_id}/stats")
async def player_stats(request: Request, player_id: int):
    """Player stats page"""
    try:
        # Load player stats from file
        stats_file = Path(__file__).parent.parent.parent / "data" / "stats" / f"player_{player_id}.json"
        if not stats_file.exists():
            logger.error(f"Stats file not found for player {player_id}")
            raise HTTPException(status_code=404, detail="Player stats not found")
            
        with open(stats_file) as f:
            stats_data = json.load(f)
            
        return templates.TemplateResponse(
            "player_stats.html",
            {
                "request": request,
                "player": stats_data["player"],
                "statistics": stats_data["statistics"]
            }
        )
    except Exception as e:
        logger.error(f"Error loading player stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 