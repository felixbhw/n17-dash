from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...pipeline.api_clients.football_api import APIFootballClient
from ...pipeline.data_ingestion import DataIngestionService

router = APIRouter()

@router.post("/initial-sync")
async def perform_initial_sync(
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Perform initial data sync for Tottenham Hotspur.
    Fetches and stores team, squad, injuries, and match data.
    """
    try:
        api_client = APIFootballClient()
        ingestion_service = DataIngestionService(api_client, session)
        
        results = await ingestion_service.perform_initial_sync()
        
        if not results['team']:
            raise HTTPException(
                status_code=500,
                detail="Failed to sync team data"
            )
            
        return {
            "status": "success",
            "data": {
                "players_synced": len(results['players']),
                "injuries_synced": len(results['injuries']),
                "matches_synced": len(results['matches']),
                "transfers_synced": len(results['transfers'])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )

@router.post("/sync/{data_type}")
async def sync_specific_data(
    data_type: str,
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Sync specific type of data for Tottenham Hotspur.
    Available types: squad, injuries, matches, transfers
    """
    try:
        api_client = APIFootballClient()
        ingestion_service = DataIngestionService(api_client, session)
        
        sync_methods = {
            "squad": ingestion_service.ingest_squad,
            "injuries": ingestion_service.ingest_injuries,
            "matches": ingestion_service.ingest_matches,
            "transfers": ingestion_service.ingest_transfers
        }
        
        if data_type not in sync_methods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data type. Available types: {', '.join(sync_methods.keys())}"
            )
            
        results = await sync_methods[data_type](team_id=47)  # Tottenham's ID
        
        return {
            "status": "success",
            "data": {
                f"{data_type}_synced": len(results)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        ) 