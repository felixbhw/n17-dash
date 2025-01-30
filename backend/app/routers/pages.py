from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

@router.get("/player/{player_id}", response_class=HTMLResponse)
async def player_page(player_id: str):
    """Serve the player details page."""
    html_path = Path(__file__).parent.parent.parent.parent / "frontend" / "templates" / "player.html"
    with open(html_path) as f:
        return f.read() 