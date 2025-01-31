from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import uvicorn
from dotenv import load_dotenv
import logging
from .services.reddit_service import RedditService
from .services.llm_service import LLMService
from .background import get_background_tasks
from .routers import api, pages, views

# Configure logging - cleaner, less verbose
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Reduce noise from other loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
logging.getLogger("asyncprawcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Create logger for this module
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="N17 Dashboard API")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "frontend")), name="static")

# Include routers
app.include_router(api.router, prefix="/api")  # API routes first
app.include_router(pages.router)  # Then page routes
app.include_router(views.router)  # Finally template routes

# Initialize services
reddit_service = RedditService()
llm_service = LLMService()

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup"""
    background_tasks = get_background_tasks(reddit_service, llm_service)
    await background_tasks.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks on shutdown"""
    background_tasks = get_background_tasks(reddit_service, llm_service)
    await background_tasks.stop()

if __name__ == "__main__":
    # Get port from environment variable, default to 8000
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
