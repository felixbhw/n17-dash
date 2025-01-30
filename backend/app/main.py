from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import uvicorn
from dotenv import load_dotenv
import logging
from .background import background_tasks

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

from .routers import api, pages

app = FastAPI(title="N17 Dashboard API")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api.router, prefix="/api")
app.include_router(pages.router)

# Mount static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path / "src")), name="static")
app.mount("/", StaticFiles(directory=str(frontend_path / "templates"), html=True), name="templates")

# Load environment variables
load_dotenv()

@app.on_event("startup")
async def startup_event():
    """Start background tasks when app starts"""
    background_tasks.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks when app shuts down"""
    background_tasks.stop()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
