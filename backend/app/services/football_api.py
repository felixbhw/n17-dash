import asyncio
import json
from pathlib import Path
import aiohttp
from log import logger

class FootballAPI:
    def __init__(self, base_url, data_dir, current_season, headers):
        self.base_url = base_url
        self.data_dir = data_dir
        self.current_season = current_season
        self.headers = headers
        self.session = None

    async def ensure_session(self):
        """Ensure we have an active aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def update_transfer_linked_players_stats(self):
        """Fetch and update stats for all players that have transfer links"""
        try:
            links_dir = Path(self.data_dir) / 'links'
            stats_dir = Path(self.data_dir) / 'stats'
            stats_dir.mkdir(exist_ok=True)
            
            # Ensure we have an active session
            session = await self.ensure_session()
            
            # Get all player IDs from transfer links
            player_ids = set()
            for player_file in links_dir.glob('player_*.json'):
                try:
                    with open(player_file) as f:
                        player_data = json.load(f)
                        if player_id := player_data.get('player_id'):
                            player_ids.add(player_id)
                except Exception as e:
                    logger.error(f"Error reading player file {player_file}: {e}")
                    continue

            # Track results
            results = {
                'success': [],
                'not_found': [],
                'error': []
            }

            # Fetch stats for each player
            for player_id in player_ids:
                try:
                    # Get player info for current season
                    player_response = await session.get(
                        f"{self.base_url}/players",
                        params={
                            "id": player_id,
                            "season": self.current_season,
                            "league": 39  # Premier League ID
                        },
                        headers=self.headers
                    )
                    
                    if player_response.status != 200:
                        logger.error(f"API error for player {player_id}: {player_response.status}")
                        results['error'].append(player_id)
                        continue

                    player_data = await player_response.json()

                    if not player_data.get('response'):
                        # Try previous season if current season data not found
                        player_response = await session.get(
                            f"{self.base_url}/players",
                            params={
                                "id": player_id,
                                "season": self.current_season - 1,
                                "league": 39  # Premier League ID
                            },
                            headers=self.headers
                        )
                        player_data = await player_response.json()

                    if not player_data.get('response'):
                        # Try without league filter as last resort
                        player_response = await session.get(
                            f"{self.base_url}/players",
                            params={
                                "id": player_id,
                                "season": self.current_season
                            },
                            headers=self.headers
                        )
                        player_data = await player_response.json()

                    if not player_data.get('response'):
                        logger.warning(f"No data found for player {player_id} in any search")
                        results['not_found'].append(player_id)
                        continue

                    # Save player stats
                    stats_file = stats_dir / f"player_{player_id}.json"
                    with open(stats_file, 'w') as f:
                        json.dump(player_data['response'][0], f, indent=2)
                    
                    logger.info(f"Updated stats for player {player_id}")
                    results['success'].append(player_id)
                    
                    # API rate limiting - sleep between requests
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error fetching stats for player {player_id}: {e}")
                    results['error'].append(player_id)
                    continue
            
            return {
                "status": "success", 
                "message": f"Updated stats for {len(results['success'])} players",
                "details": {
                    "successful": results['success'],
                    "not_found": results['not_found'],
                    "errors": results['error']
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating transfer linked players stats: {e}")
            raise Exception(f"Failed to update player stats: {str(e)}")

    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_player_info(self, player_id: int) -> dict:
        """Fetch player information from API-Football v2 using search"""
        try:
            session = await self.ensure_session()
            
            # Use v2 API endpoint
            v2_url = "https://v2.api-football.com"
            v2_headers = {"x-apisports-key": self.headers["x-apisports-key"]}
            
            # First search for the player by ID in the search results
            response = await session.get(
                f"{v2_url}/players/search/disasi",  # Search by last name
                headers=v2_headers
            )
            
            if response.status != 200:
                raise Exception(f"API error: {response.status}")
                
            data = await response.json()
            
            # v2 API response format for search
            if not data.get('api', {}).get('results'):
                return None
            
            # Find the player with matching ID in search results
            players = data['api']['players']
            for player in players:
                if player.get('player_id') == player_id:
                    return player
                    
            return None
            
        except Exception as e:
            logger.error(f"Error fetching player info for ID {player_id}: {e}")
            return None 

    async def search_players(self, name: str) -> list:
        """Search for players by name using API-Football v2"""
        try:
            session = await self.ensure_session()
            
            # Use v2 API endpoint
            v2_url = "https://v2.api-football.com"
            v2_headers = {"x-apisports-key": self.headers["x-apisports-key"]}
            
            # Extract last name and ensure it's at least 4 characters
            last_name = name.split()[-1].lower()
            if len(last_name) < 4:
                raise ValueError("Last name must be at least 4 characters")
            
            response = await session.get(
                f"{v2_url}/players/search/{last_name}",
                headers=v2_headers
            )
            
            if response.status != 200:
                raise Exception(f"API error: {response.status}")
                
            data = await response.json()
            
            if not data.get('api', {}).get('results'):
                return []
                
            return data['api']['players']
            
        except Exception as e:
            logger.error(f"Error searching players with name {name}: {e}")
            return [] 