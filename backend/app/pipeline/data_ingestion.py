"""
Data ingestion service for N17 Dashboard.
Handles fetching and storing data from API-Football.
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from ..models import Player, Team, Match
from .api_clients.football_api import APIFootballClient, DataTransformer
from ..db.session import get_db

logger = logging.getLogger(__name__)

class DataIngestionService:
    """Service for ingesting data from API-Football into the database."""
    
    def __init__(self, api_client: APIFootballClient, session: AsyncSession):
        self.api_client = api_client
        self.session = session
        self.transformer = DataTransformer()
        
    async def ingest_team(self, team_id: int) -> Optional[Team]:
        """Fetch and store team data."""
        try:
            team_data = await self.api_client.get_team_info(team_id)
            if not team_data:
                logger.error(f"No team data found for ID {team_id}")
                return None
                
            transformed_team = self.transformer.transform_team(team_data)
            if not transformed_team:
                logger.error(f"Failed to transform team data for ID {team_id}")
                return None
                
            # Check if team exists
            stmt = select(Team).where(Team.team_id == team_id)
            result = await self.session.execute(stmt)
            team = result.scalar_one_or_none()
            
            if team:
                # Update existing team
                await self.session.execute(
                    update(Team)
                    .where(Team.team_id == team_id)
                    .values(**transformed_team)
                )
            else:
                # Create new team
                team = Team(**transformed_team)
                self.session.add(team)
            
            await self.session.commit()
            return team
            
        except Exception as e:
            logger.error(f"Error ingesting team data: {str(e)}")
            await self.session.rollback()
            return None
            
    async def ingest_squad(self, team_id: int) -> List[Player]:
        """Fetch and store current squad data."""
        try:
            squad_data = await self.api_client.get_team_squad(team_id)
            if not squad_data:
                logger.error(f"No squad data found for team ID {team_id}")
                return []
                
            players = []
            for player_data in squad_data.get('response', []):
                transformed_player = self.transformer.transform_player({'response': [player_data]})
                if not transformed_player:
                    continue
                    
                # Check if player exists
                stmt = select(Player).where(Player.player_id == transformed_player['player_id'])
                result = await self.session.execute(stmt)
                player = result.scalar_one_or_none()
                
                if player:
                    # Update existing player
                    await self.session.execute(
                        update(Player)
                        .where(Player.player_id == transformed_player['player_id'])
                        .values(**transformed_player)
                    )
                    players.append(player)
                else:
                    # Create new player
                    player = Player(**transformed_player)
                    self.session.add(player)
                    players.append(player)
            
            await self.session.commit()
            return players
            
        except Exception as e:
            logger.error(f"Error ingesting squad data: {str(e)}")
            await self.session.rollback()
            return []
            
    async def ingest_matches(self, team_id: int, status: str = "SCHEDULED") -> List[Match]:
        """Fetch and store match data."""
        try:
            match_data = await self.api_client.get_matches(team_id, status)
            if not match_data:
                logger.error(f"No match data found for team ID {team_id}")
                return []
                
            matches = []
            transformed_matches = self.transformer.transform_match(match_data)
            
            for match_info in transformed_matches:
                # Check if match exists
                stmt = select(Match).where(Match.match_id == match_info['match_id'])
                result = await self.session.execute(stmt)
                match = result.scalar_one_or_none()
                
                if match:
                    # Update existing match
                    await self.session.execute(
                        update(Match)
                        .where(Match.match_id == match_info['match_id'])
                        .values(**match_info)
                    )
                    matches.append(match)
                else:
                    # Create new match
                    match = Match(**match_info)
                    self.session.add(match)
                    matches.append(match)
            
            await self.session.commit()
            return matches
            
        except Exception as e:
            logger.error(f"Error ingesting match data: {str(e)}")
            await self.session.rollback()
            return []

    async def perform_initial_sync(self, team_id: int = 47) -> Dict:
        """
        Perform initial sync of all data for a team.
        Default team_id 47 is Tottenham Hotspur.
        """
        results = {
            'team': None,
            'players': [],
            'matches': []
        }
        
        # Sync team data
        team = await self.ingest_team(team_id)
        if team:
            results['team'] = team
            
            # Sync squad data
            results['players'] = await self.ingest_squad(team_id)
            
            # Sync matches (both scheduled and finished)
            scheduled_matches = await self.ingest_matches(team_id, "SCHEDULED")
            finished_matches = await self.ingest_matches(team_id, "FINISHED")
            results['matches'] = scheduled_matches + finished_matches
            
        return results 