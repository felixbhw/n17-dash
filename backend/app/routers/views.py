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

@router.get("/news/{news_id}")
async def news_event(request: Request, news_id: str):
    """News event page"""
    try:
        # Load news data
        news_file = Path(__file__).parent.parent.parent / "data" / "news" / f"{news_id}.json"
        if not news_file.exists():
            logger.error(f"News file not found: {news_id}")
            raise HTTPException(status_code=404, detail="News event not found")
            
        with open(news_file) as f:
            news_data = json.load(f)
        
        # Get tier styling
        tier_class = {
            1: 'success',
            2: 'info',
            3: 'warning',
            4: 'secondary'
        }.get(news_data.get('tier', 4), 'secondary')
        
        # Find related players
        links_dir = Path(__file__).parent.parent.parent / "data" / "links"
        related_players = []
        
        for player_file in links_dir.glob('player_*.json'):
            try:
                with open(player_file) as f:
                    player_data = json.load(f)
                    # Check if this news event is referenced in any timeline events
                    for event in player_data.get('timeline', []):
                        if news_id in event.get('news_ids', []):
                            related_players.append(player_data)
                            break
            except Exception as e:
                logger.error(f"Error checking player file {player_file}: {e}")
                continue
            
        return templates.TemplateResponse(
            "news.html",
            {
                "request": request,
                "news": news_data,
                "tier_class": tier_class,
                "related_players": related_players
            }
        )
    except Exception as e:
        logger.error(f"Error loading news event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 