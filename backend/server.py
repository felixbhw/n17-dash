"""
FastAPI server for N17 Dashboard.
"""

import os
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.pipeline.data_ingestion import DataIngestionService
from app.pipeline.api_clients.football_api import APIFootballClient
from app.db.session import get_db
from app.models import Team, Player, Match
from app.utils.logging import setup_logging

# Configure logging
setup_logging()

app = FastAPI(title="N17 Dashboard API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API client
api_key = os.getenv("API_FOOTBALL_KEY")
if not api_key:
    raise ValueError("API_FOOTBALL_KEY environment variable not set")
api_client = APIFootballClient(api_key)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "N17 Dashboard API"}

@app.get("/api/team/{team_id}")
async def get_team(
    team_id: int,
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """Get team information."""
    try:
        stmt = select(Team).where(Team.team_id == team_id)
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()
        
        if not team:
            raise HTTPException(
                status_code=404,
                detail=f"Team with ID {team_id} not found"
            )
            
        return {
            "status": "success",
            "data": {
                "id": team.team_id,
                "name": team.name,
                "code": team.code,
                "stadium": team.stadium,
                "founded": team.founded,
                "league": team.league
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching team data: {str(e)}"
        )

@app.get("/api/team/{team_id}/squad")
async def get_squad(
    team_id: int,
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """Get current squad for a team."""
    try:
        stmt = select(Player).where(Player.team_id == team_id)
        result = await session.execute(stmt)
        players = result.scalars().all()
        
        return {
            "status": "success",
            "data": [
                {
                    "id": p.player_id,
                    "name": p.name,
                    "position": p.position,
                    "nationality": p.nationality
                }
                for p in players
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching squad data: {str(e)}"
        )

@app.get("/api/team/{team_id}/matches")
async def get_matches(
    team_id: int,
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """Get matches for a team."""
    try:
        # Get both home and away matches
        stmt = select(Match).where(
            (Match.home_team_id == team_id) | (Match.away_team_id == team_id)
        ).order_by(Match.match_date)
        
        result = await session.execute(stmt)
        matches = result.scalars().all()
        
        return {
            "status": "success",
            "data": [
                {
                    "id": m.match_id,
                    "date": m.match_date.isoformat(),
                    "home_team_id": m.home_team_id,
                    "away_team_id": m.away_team_id,
                    "scoreline": m.scoreline,
                    "competition": m.competition
                }
                for m in matches
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching match data: {str(e)}"
        )

@app.post("/api/sync/initial-setup")
async def initial_sync(
    team_id: int = 47,  # Default to Tottenham
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Perform initial sync of all data for a team.
    Default team_id 47 is Tottenham Hotspur.
    """
    try:
        ingestion_service = DataIngestionService(api_client, session)
        results = await ingestion_service.perform_initial_sync(team_id)
        
        if not results['team']:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to sync team data for ID {team_id}"
            )
            
        return {
            "status": "success",
            "data": {
                "team": str(results['team']),
                "players_synced": len(results['players']),
                "matches_synced": len(results['matches'])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during initial sync: {str(e)}"
        )

@app.get("/api/sync/status")
async def sync_status(
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """Get the current sync status of the database."""
    try:
        # Get counts from each table
        team_count = await session.execute("SELECT COUNT(*) FROM teams")
        player_count = await session.execute("SELECT COUNT(*) FROM players")
        match_count = await session.execute("SELECT COUNT(*) FROM matches")
        
        return {
            "status": "success",
            "data": {
                "teams": team_count.scalar(),
                "players": player_count.scalar(),
                "matches": match_count.scalar()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting sync status: {str(e)}"
        )
