from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from ..services.reddit_service import RedditService
from ..services.llm_service import LLMService
from ..background import get_background_tasks

router = APIRouter()
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / 'data'

# Initialize services
reddit_service = RedditService()
llm_service = LLMService()

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
            
            # Skip players that are explicitly marked as not squad players
            if player_data.get("is_squad_player") is False:
                continue
                
            players.append({
                "id": player_data.get("id"),
                "name": player_data.get("name"),
                "number": player_data.get("number"),
                "position": player_data.get("position"),
                "age": player_data.get("age"),
                "photo": player_data.get("photo"),
                "is_squad_player": player_data.get("is_squad_player", True)  # Default to True for legacy data
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

@router.post("/squad/update")
async def update_squad():
    """Update the squad list from API-Football."""
    try:
        background_tasks = get_background_tasks()
        await background_tasks.llm_service.football_api.update_squad()
        return {"status": "success", "message": "Squad updated successfully"}
    except Exception as e:
        logger.error(f"Error updating squad: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/links/players")
async def get_player_links():
    """Get all player transfer links"""
    try:
        players = []
        links_dir = DATA_DIR / 'links'
        
        # Read all player files
        for player_file in links_dir.glob('player_*.json'):
            try:
                with open(player_file) as f:
                    player_data = json.load(f)
                    players.append(player_data)
            except Exception as e:
                logger.error(f"Error processing player file {player_file}: {e}")
                continue
        
        return players
        
    except Exception as e:
        logger.error(f"Error getting player links: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/links/players/stats")
async def get_transfer_linked_players_stats():
    """Get stats for all players with transfer links"""
    try:
        player_stats = {}
        links_dir = DATA_DIR / 'links'
        stats_dir = DATA_DIR / 'stats'
        
        # First get all transfer-linked players
        for player_file in links_dir.glob('player_*.json'):
            try:
                with open(player_file) as f:
                    player_data = json.load(f)
                    player_id = player_data.get('player_id')
                    
                    if player_id:
                        # Try to get stats for this player
                        stats_file = stats_dir / f"player_{player_id}.json"
                        if stats_file.exists():
                            with open(stats_file) as f:
                                stats_data = json.load(f)
                                player_stats[player_id] = {
                                    'player': stats_data.get('player', {}),
                                    'statistics': stats_data.get('statistics', [])
                                }
                        else:
                            logger.warning(f"No stats found for player {player_id}")
                            
            except Exception as e:
                logger.error(f"Error processing player file {player_file}: {e}")
                continue
        
        return player_stats
        
    except Exception as e:
        logger.error(f"Error getting player stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/links/player/{player_id}")
async def get_player_link_details(player_id: int):
    """Get detailed transfer information for a specific player"""
    base_dir = Path(__file__).parent.parent.parent
    player_file = base_dir / "data" / "links" / f"player_{player_id}.json"
    
    if not player_file.exists():
        raise HTTPException(status_code=404, detail="Player link data not found")
    
    try:
        with open(player_file) as f:
            data = json.load(f)
            
        # Load referenced news articles
        news_dir = base_dir / "data" / "news"
        news_items = {}
        
        for event in data['timeline']:
            for news_id in event['news_ids']:
                if news_id not in news_items:
                    news_file = news_dir / f"{news_id}.json"
                    if news_file.exists():
                        with open(news_file) as f:
                            news_data = json.load(f)
                            news_items[news_id] = {
                                "title": news_data['title'],
                                "url": news_data['url'],
                                "timestamp": news_data['timestamp']
                            }
        
        return {
            **data,
            "news_items": news_items
        }
        
    except Exception as e:
        logger.error(f"Error loading player link data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/links/events")
async def get_transfer_events():
    """Get all transfer timeline events"""
    try:
        events = []
        links_dir = DATA_DIR / 'links'
        
        # Read all player files and extract events
        for player_file in links_dir.glob('player_*.json'):
            try:
                with open(player_file) as f:
                    player_data = json.load(f)
                    
                    # Add each timeline event
                    for event in player_data.get('timeline', []):
                        events.append({
                            'date': event.get('date', datetime.now().isoformat()),
                            'player_id': player_data.get('player_id'),
                            'player_name': player_data.get('canonical_name', 'Unknown'),
                            'event_type': event.get('event_type', ''),
                            'details': event.get('details', ''),
                            'confidence': event.get('confidence'),
                            'news_ids': event.get('news_ids', [])  # Include news_ids in response
                        })
            except Exception as e:
                logger.error(f"Error processing events from {player_file}: {e}")
                continue
                
        # Sort by date descending
        events.sort(key=lambda x: x['date'], reverse=True)
        return events
        
    except Exception as e:
        logger.error(f"Error getting transfer events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/players/update-stats")
async def update_transfer_linked_players_stats():
    """Update stats for all players with transfer links from API-Football"""
    try:
        # Use the existing llm_service instance
        result = await llm_service.football_api.update_transfer_linked_players_stats()
        return result
    except Exception as e:
        logger.error(f"Error updating transfer linked players stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/links/player/{player_id}")
async def update_player_link(player_id: int, update_data: dict):
    """Update transfer link information for a player"""
    try:
        # If player ID is being changed, handle the file rename
        new_player_id = update_data.get('player_id')
        if new_player_id and new_player_id != player_id:
            old_file = DATA_DIR / 'links' / f"player_{player_id}.json"
            new_file = DATA_DIR / 'links' / f"player_{new_player_id}.json"
            
            # Check if new ID already exists
            if new_file.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Player with ID {new_player_id} already exists"
                )
            
            # Read existing data
            if not old_file.exists():
                raise HTTPException(
                    status_code=404,
                    detail="Player link data not found"
                )
                
            with open(old_file) as f:
                current_data = json.load(f)
            
            # Update the player ID and other fields
            current_data['player_id'] = new_player_id
            for field in ['transfer_status', 'direction', 'related_clubs']:
                if field in update_data:
                    current_data[field] = update_data[field]
            
            # Update timestamp
            current_data['last_updated'] = datetime.now().isoformat()
            
            # Save to new file and delete old
            with open(new_file, 'w') as f:
                json.dump(current_data, f, indent=2)
            old_file.unlink()
            
            # Fetch new player stats if needed
            try:
                await llm_service._ensure_player_stats(new_player_id, current_data['canonical_name'])
            except Exception as e:
                logger.warning(f"Error fetching stats for new player ID: {e}")
            
            return {"status": "success", "message": "Player link data updated with new ID"}
            
        else:
            # Regular update without ID change
            player_file = DATA_DIR / 'links' / f"player_{player_id}.json"
            
            if not player_file.exists():
                raise HTTPException(
                    status_code=404,
                    detail="Player link data not found"
                )
            
            # Read existing data
            with open(player_file) as f:
                current_data = json.load(f)
            
            # Update allowed fields
            for field in ['transfer_status', 'direction', 'related_clubs']:
                if field in update_data:
                    current_data[field] = update_data[field]
            
            # Update timestamp
            current_data['last_updated'] = datetime.now().isoformat()
            
            # Save updated data
            with open(player_file, 'w') as f:
                json.dump(current_data, f, indent=2)
            
            return {"status": "success", "message": "Player link data updated"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating player link data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/player/{player_id}/timeline")
async def add_timeline_event(player_id: int, event_data: dict):
    """Add a new timeline event for a player"""
    try:
        player_file = DATA_DIR / 'links' / f"player_{player_id}.json"
        
        if not player_file.exists():
            raise HTTPException(status_code=404, detail="Player link data not found")
        
        # Read existing data
        with open(player_file) as f:
            current_data = json.load(f)
        
        # Create new event
        new_event = {
            "event_type": event_data.get("event_type", "update"),
            "details": event_data.get("details", ""),
            "confidence": event_data.get("confidence", 50),
            "date": datetime.now().isoformat(),
            "news_ids": event_data.get("news_ids", [])
        }
        
        # Add to timeline
        if 'timeline' not in current_data:
            current_data['timeline'] = []
        current_data['timeline'].append(new_event)
        
        # Update timestamp
        current_data['last_updated'] = datetime.now().isoformat()
        
        # Save updated data
        with open(player_file, 'w') as f:
            json.dump(current_data, f, indent=2)
        
        return {"status": "success", "message": "Timeline event added"}
        
    except Exception as e:
        logger.error(f"Error adding timeline event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/links/player/{player_id}/timeline/{event_index}")
async def delete_timeline_event(player_id: int, event_index: int):
    """Delete a timeline event for a player"""
    try:
        player_file = DATA_DIR / 'links' / f"player_{player_id}.json"
        
        if not player_file.exists():
            raise HTTPException(status_code=404, detail="Player link data not found")
        
        # Read existing data
        with open(player_file) as f:
            current_data = json.load(f)
        
        # Check if timeline exists and index is valid
        if 'timeline' not in current_data or event_index >= len(current_data['timeline']):
            raise HTTPException(status_code=404, detail="Timeline event not found")
        
        # Remove event
        current_data['timeline'].pop(event_index)
        
        # Update timestamp
        current_data['last_updated'] = datetime.now().isoformat()
        
        # Save updated data
        with open(player_file, 'w') as f:
            json.dump(current_data, f, indent=2)
        
        return {"status": "success", "message": "Timeline event deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting timeline event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reddit/check-now")
async def check_reddit_now():
    """Manually trigger a Reddit check and LLM processing"""
    try:
        # Get the existing background tasks instance
        background_tasks = get_background_tasks()
        
        # Run Reddit check
        await background_tasks.reddit_service.check_new_posts()
        
        # Process any new news files with LLM
        await background_tasks.llm_service.process_pending_news()
        
        return {"status": "success", "message": "Reddit check and LLM processing completed"}
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/players/manual")
async def create_manual_player(player_data: dict):
    """Create a player record manually with API-Football ID"""
    try:
        name = player_data.get('name')
        player_id = player_data.get('player_id')
        
        if not name or not player_id:
            raise HTTPException(
                status_code=400,
                detail="Both name and player_id are required"
            )
            
        result = await llm_service.create_manual_player(name, player_id)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating manual player: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/player/{player_id}/link-news")
async def link_news_to_player(player_id: int, data: dict):
    """Manually link a news item to a player"""
    try:
        news_id = data.get('news_id')
        if not news_id:
            raise HTTPException(
                status_code=400,
                detail="news_id is required"
            )
            
        result = await llm_service.link_news_to_player(player_id, news_id)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking news to player: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/reprocess-unlinked")
async def reprocess_unlinked_news():
    """Reprocess all unlinked news items"""
    try:
        # Get all unlinked news
        unlinked_news = llm_service._get_unlinked_news()
        
        # Process each unlinked news file
        processed_count = 0
        for news_file in unlinked_news:
            try:
                await llm_service.process_news_file(news_file)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing news file {news_file.name}: {e}")
                continue
                
        return {
            "status": "success",
            "processed_count": processed_count,
            "total_unlinked": len(unlinked_news)
        }
        
    except Exception as e:
        logger.error(f"Error reprocessing unlinked news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.api_route("/reddit/fetch-historical/{days}", methods=["GET", "POST"])
async def fetch_historical_posts(days: int):
    """
    Fetch and process historical transfer posts from r/coys.
    Supports both GET and POST methods.
    
    Args:
        days: Number of days to look back (1-30)
        
    Returns:
        Dict with status and detailed stats about processed posts
    """
    if days < 1 or days > 30:
        raise HTTPException(
            status_code=400,
            detail="Days must be between 1 and 30"
        )
    
    try:
        # Get background tasks instance
        background_tasks = get_background_tasks()
        
        # Fetch historical posts
        logger.info(f"Starting historical fetch for past {days} days")
        stats = await background_tasks.reddit_service.fetch_historical(days)
        
        # Process new posts with LLM if any were saved
        if stats['saved'] > 0:
            logger.info("Processing new posts with LLM")
            await background_tasks.llm_service.process_pending_news()
        
        return {
            "status": "success",
            "message": f"Fetched and processed posts from past {days} days",
            "stats": {
                "posts_processed": stats['processed'],
                "posts_saved": stats['saved'],
                "posts_skipped": stats['skipped'],
                "errors": stats['errors']
            }
        }
        
    except Exception as e:
        logger.error(f"Historical fetch failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Historical fetch failed: {str(e)}"
        )
