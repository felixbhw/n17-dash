from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()

@router.get("/links", response_class=HTMLResponse)
async def links_page():
    """Serve the transfer links page."""
    html_path = Path(__file__).parent.parent.parent.parent / "frontend" / "templates" / "links.html"
    with open(html_path) as f:
        return f.read()

@router.get("/", response_class=HTMLResponse)
async def index_page():
    """Serve the main squad page."""
    html_path = Path(__file__).parent.parent.parent.parent / "frontend" / "templates" / "index.html"
    with open(html_path) as f:
        return f.read() 