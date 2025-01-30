"""
API-Football Client for N17 Dashboard
Handles all interactions with the API-Football service for retrieving
squad, player, match, and competition data.
"""

import os
from typing import Dict, List, Optional, Union
import aiohttp
import asyncio
from datetime import datetime
import logging

from ...utils.validation import (
    validate_api_response,
    validate_player_data,
    validate_injury_data,
    validate_match_data,
    validate_transfer_data
)

logger = logging.getLogger(__name__)

class APIFootballClient:
    """Main client class for interacting with API-Football."""
    
    def __init__(self, api_key: str = None):
        """Initialize the API client with credentials."""
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set API_FOOTBALL_KEY environment variable.")
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        self.current_season = datetime.now().year
        
    async def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make API request with proper headers and validation"""
        try:
            async with aiohttp.ClientSession() as session:
                for attempt in range(3):
                    async with session.get(
                        f"{self.base_url}/{endpoint}",
                        headers=self.headers,
                        params=params
                    ) as response:
                        if response.status == 429:
                            retry_after = int(response.headers.get('Retry-After', 30))
                            logger.warning(f"Rate limited. Retrying in {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                        
                        response.raise_for_status()
                        data = await response.json()
                        
                        # Use updated validation
                        validated = validate_api_response(data)
                        if not validated:
                            logger.error(f"Empty response from {endpoint}")
                            return {}
                            
                        return validated
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return {}

    # Team-related methods
    async def get_team_info(self, team_id: int) -> Dict:
        """Get detailed information about a specific team."""
        return await self._get("teams", {"id": team_id})

    async def get_team_squad(self, team_id: int) -> List[Dict]:
        """Get current squad list for a team."""
        return await self._get("players", {
            "team": team_id,
            "season": self.current_season
        })

    async def get_team_statistics(self, team_id: int, league_id: int, season: Optional[int] = None) -> Dict:
        """Get team statistics for a specific season/league."""
        params = {
            "team": team_id,
            "league": league_id,
            "season": season or self.current_season
        }
        return await self._get("teams/statistics", params)

    # Player-related methods
    async def get_player_info(self, player_id: int, season: Optional[int] = None) -> Dict:
        """Get detailed information about a specific player."""
        params = {
            "id": player_id,
            "season": season or self.current_season
        }
        return await self._get("players", params)

    async def get_player_statistics(self, player_id: int, season: Optional[int] = None) -> Dict:
        """Get player statistics for a specific season."""
        params = {
            "id": player_id,
            "season": season or self.current_season
        }
        return await self._get("players", params)

    async def get_player_transfers(self, player_id: int) -> List[Dict]:
        """Get transfer history for a player."""
        return await self._get("transfers", {"player": player_id})

    # Match-related methods
    async def get_matches(self, team_id: int, status: str = "SCHEDULED", season: Optional[int] = None) -> List[Dict]:
        """Get matches for a team with required season parameter."""
        params = {
            "team": team_id,
            "status": status,
            "season": season or self.current_season  # Ensure season is always included
        }
        return await self._get("fixtures", params)

    async def get_match_statistics(self, match_id: int) -> Dict:
        """Get detailed statistics for a specific match."""
        return await self._get("fixtures/statistics", {"fixture": match_id})

    async def get_head_to_head(self, team1_id: int, team2_id: int, season: Optional[int] = None) -> List[Dict]:
        """Get head-to-head record between two teams."""
        params = {
            "h2h": f"{team1_id}-{team2_id}",
            "season": season or self.current_season
        }
        return await self._get("fixtures/headtohead", params)

    # League/Competition methods
    async def get_league_standings(self, league_id: int, season: Optional[int] = None) -> List[Dict]:
        """Get current league standings."""
        params = {
            "league": league_id,
            "season": season or self.current_season
        }
        return await self._get("standings", params)

    async def get_league_topscorers(self, league_id: int, season: Optional[int] = None) -> List[Dict]:
        """Get top scorers for a league/season."""
        params = {
            "league": league_id,
            "season": season or self.current_season
        }
        return await self._get("players/topscorers", params)

    # Injury-related methods
    async def get_injuries(self, team_id: int, season: Optional[int] = None) -> Dict:
        """Get team injuries with season parameter."""
        params = {
            "team": team_id,
            "season": season or self.current_season  # Add required season
        }
        return await self._get("injuries", params)

    # Transfer-related methods
    async def get_transfer_rumors(self, team_id: Optional[int] = None, player_id: Optional[int] = None) -> List[Dict]:
        """Get transfer rumors for a team or player."""
        params = {}
        if team_id:
            params["team"] = team_id
        if player_id:
            params["player"] = player_id
        return await self._get("transfers", params)

    async def get_transfer_history(self, team_id: int, season: Optional[int] = None) -> List[Dict]:
        """Get transfer history for a team."""
        params = {"team": team_id}
        if season:
            params["season"] = season
        return await self._get("transfers", params)

    # Utility methods
    async def search_players(self, query: str) -> List[Dict]:
        """Search for players by name."""
        return await self._get("players/search", {"search": query})

    async def get_seasons(self, league_id: int) -> List[int]:
        """Get available seasons for a league."""
        return await self._get("leagues/seasons", {"league": league_id})

class DataTransformer:
    """
    Handles transformation of API responses into database models.
    Separates data transformation logic from API client.
    """
    
    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse and format date string."""
        if not date_str:
            return None
        try:
            # Handle different date formats from API
            if 'T' in date_str:
                # Format: 2023-08-13T13:00:00+00:00
                return date_str.split('T')[0]
            return date_str
        except Exception:
            return None
    
    @staticmethod
    def transform_player(api_data: Dict, team_id: int = None) -> Optional[Dict]:
        """Handle squad response format with direct team context."""
        if not validate_api_response(api_data):
            return None
            
        # Handle both player detail and squad list responses
        player = api_data.get('player', api_data)  # Account for different response structures
        statistics = api_data.get('statistics', [{}])[-1]
        
        transformed_data = {
            'player_id': player.get('id'),
            'name': player.get('name'),
            'date_of_birth': DataTransformer._parse_date(player.get('birth', {}).get('date')),
            'nationality': player.get('nationality'),
            'position': player.get('position', 'Unknown'),  # Use direct position from squad response
            'team_id': team_id  # Use context team_id from squad sync
        }
        
        return validate_player_data(transformed_data)
    
    @staticmethod
    def transform_team(api_data: Dict) -> Optional[Dict]:
        """Transform team data into database model format."""
        if not validate_api_response(api_data):
            return None
            
        team_data = api_data['response'][0]
        team = team_data.get('team', {})
        venue = team_data.get('venue', {})
        
        return {
            'team_id': team.get('id'),
            'name': team.get('name'),
            'code': team.get('code'),  # E.g., "TOT"
            'stadium': venue.get('name'),
            'founded': team.get('founded'),
            'league': team.get('country')  # Using country as a fallback
        }

    @staticmethod
    def transform_match(api_data: Dict) -> List[Dict]:
        """Transform match data into database model format."""
        if not validate_api_response(api_data):
            return []
            
        matches = []
        for match in api_data['response']:
            fixture = match.get('fixture', {})
            teams = match.get('teams', {})
            goals = match.get('goals', {})
            league = match.get('league', {})
            
            # Skip matches without proper IDs
            if not fixture.get('id') or not teams.get('home', {}).get('id') or not teams.get('away', {}).get('id'):
                continue
                
            transformed_data = {
                'match_id': fixture.get('id'),
                'home_team_id': teams.get('home', {}).get('id'),
                'away_team_id': teams.get('away', {}).get('id'),
                'match_date': DataTransformer._parse_date(fixture.get('date')),
                'scoreline': f"{goals.get('home', 0)}-{goals.get('away', 0)}",
                'competition': league.get('name')
            }
            
            validated = validate_match_data(transformed_data)
            if validated:
                matches.append(validated)
                
        return matches

    @staticmethod
    def transform_transfer(api_data: Dict) -> List[Dict]:
        """Transform transfer data into database model format."""
        if not validate_api_response(api_data):
            return []
            
        transfers = []
        for transfer in api_data['response']:
            transfer_info = transfer.get('transfers', [{}])[0]
            
            # Skip transfers without proper player ID
            if not transfer.get('player', {}).get('id'):
                continue
                
            transformed_data = {
                'player_id': transfer.get('player', {}).get('id'),
                'status': transfer_info.get('type', 'Completed'),  # API only returns completed transfers
                'last_update': DataTransformer._parse_date(transfer_info.get('date')),
                'destination_club': transfer_info.get('teams', {}).get('out', {}).get('name'),
                'transfer_fee': transfer_info.get('fee')
            }
            
            validated = validate_transfer_data(transformed_data)
            if validated:
                transfers.append(validated)
                
        return transfers

    @staticmethod
    def transform_injury(api_data: Dict) -> List[Dict]:
        """Transform injury data into database model format."""
        if not validate_api_response(api_data):
            return []
            
        injuries = []
        for injury in api_data['response']:
            # Skip injuries without proper player ID
            if not injury.get('player', {}).get('id'):
                continue
                
            transformed_data = {
                'player_id': injury.get('player', {}).get('id'),
                'description': injury.get('type') or injury.get('reason'),
                'injury_date': DataTransformer._parse_date(injury.get('fixture', {}).get('date')),
                'recovery_estimated': None,  # Not provided in API
                'severity': injury.get('type')  # Will be mapped in validation
            }
            
            validated = validate_injury_data(transformed_data)
            if validated:
                injuries.append(validated)
                
        return injuries

    @staticmethod
    def transform_news(api_data: Dict) -> List[Dict]:
        """Transform news data into database model format."""
        # Note: API-Football doesn't provide news directly
        # This would need to be implemented with a different data source
        return []

# Error Classes
class APIFootballError(Exception):
    """Base exception for API-Football errors."""
    pass

class RateLimitError(APIFootballError):
    """Raised when API rate limit is exceeded."""
    pass

class AuthenticationError(APIFootballError):
    """Raised when API authentication fails."""
    pass

class EndpointError(APIFootballError):
    """Raised when an API endpoint returns an error."""
    pass
