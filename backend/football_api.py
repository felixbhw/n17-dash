"""
Simple Football API Client for N17 Dashboard
This module handles getting Tottenham data from API-Football and storing it in JSON files.
No database needed - just simple JSON files!
"""

import os
import json
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file in parent directory
load_dotenv('../.env')

# Constants for Tottenham and Premier League
TOTTENHAM_TEAM_ID = 47
PREMIER_LEAGUE_ID = 39
CURRENT_SEASON = datetime.now().year  # Using current season since we have pro plan

class SimpleFootballAPI:
    """
    A simple client for getting Tottenham data from API-Football.
    Everything is stored in JSON files in the data/ directory.
    """
    
    def __init__(self, api_key: str = None):
        """Set up the API client with your API key."""
        # Get API key from environment variable if not provided
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        if not self.api_key:
            raise ValueError("Please set your API_FOOTBALL_KEY environment variable!")
            
        # API settings
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-apisports-key": self.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        
        # Make sure our data folders exist
        self._setup_data_folders()
    
    def _setup_data_folders(self):
        """Create folders to store our JSON files if they don't exist."""
        folders = ['data', 'data/players', 'data/matches', 'data/injuries', 'data/stats']
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make a request to the API and handle any errors.
        
        Args:
            endpoint: API endpoint (e.g. "players")
            params: Query parameters (e.g. {"team": 47})
            
        Returns:
            Dict with the API response
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    response_data = await response.json()
                    
                    # API-Football specific error handling
                    if not response_data.get('response') and response_data.get('errors'):
                        error_msg = "; ".join(response_data['errors'].values())
                        raise Exception(f"API Error: {error_msg}")
                    
                    # Check for common errors
                    if response.status == 429:  # Too many requests
                        raise Exception("Whoa! We hit the API rate limit. Wait a bit and try again.")
                    elif response.status == 401:  # Bad API key
                        raise Exception("Your API key isn't working. Check if it's correct!")
                    elif response.status != 200:  # Any other error
                        error_text = await response.text()
                        raise Exception(f"API error (status {response.status}): {error_text}")
                    
                    # Return the JSON response if everything's okay
                    return response_data
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {str(e)}")
    
    def _save_json(self, folder: str, filename: str, data: Dict):
        """
        Save data to a JSON file safely.
        
        Args:
            folder: Folder name (e.g. "players")
            filename: File name (e.g. "123.json")
            data: Data to save
        """
        filepath = os.path.join('data', folder, filename)
        
        try:
            # First write to a temporary file
            temp_path = filepath + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Then rename it to the real file (this is atomic and safer)
            os.replace(temp_path, filepath)
            
        except Exception as e:
            raise Exception(f"Couldn't save to {filepath}: {str(e)}")
    
    def _load_json(self, folder: str, filename: str) -> Optional[Dict]:
        """
        Load data from a JSON file.
        
        Args:
            folder: Folder name (e.g. "players")
            filename: File name (e.g. "123.json")
            
        Returns:
            Dict with the data, or None if file doesn't exist
        """
        filepath = os.path.join('data', folder, filename)
        
        try:
            if os.path.exists(filepath):
                with open(filepath, encoding='utf-8') as f:
                    return json.load(f)
            return None
            
        except Exception as e:
            raise Exception(f"Couldn't read {filepath}: {str(e)}")
    
    async def update_squad(self):
        """
        Get the current Tottenham squad and save each player's info.
        This creates/updates a JSON file for each player in data/players/.
        """
        # Get the current squad from API
        response = await self._make_request("players/squads", {"team": TOTTENHAM_TEAM_ID})
        
        if not response.get('response'):
            if response.get('errors'):
                error_msg = "; ".join(response['errors'].values())
                raise Exception(f"API Error with squad: {error_msg}")
            raise Exception("Couldn't get squad data from API - empty response")
        
        # Process each player
        squad_data = response['response'][0]
        for player in squad_data.get('players', []):
            # Create a more detailed player record
            player_data = {
                'id': player.get('id'),
                'name': player.get('name'),
                'firstname': player.get('firstname'),
                'lastname': player.get('lastname'),
                'age': player.get('age'),
                'number': player.get('number'),
                'position': player.get('position'),
                'photo': player.get('photo'),
                'last_updated': datetime.now().isoformat()
            }
            
            # Save to a JSON file named with the player's ID
            self._save_json('players', f"{player['id']}.json", player_data)
            
            # Get and save detailed statistics for the player
            await self._update_player_stats(player['id'])
    
    async def _update_player_stats(self, player_id: int):
        """Get and save detailed statistics for a player."""
        response = await self._make_request("players", {
            "id": player_id,
            "season": CURRENT_SEASON,
            "league": PREMIER_LEAGUE_ID
        })
        
        if response.get('response'):
            stats_data = response['response'][0]
            self._save_json('stats', f"player_{player_id}.json", stats_data)
    
    async def update_matches(self, status: str = "all"):
        """
        Get Tottenham's matches and save them.
        
        Args:
            status: Match status ("all", "NS-scheduled", "LIVE", "FT-finished", etc.)
        """
        # Get matches from API
        params = {
            "team": TOTTENHAM_TEAM_ID,
            "season": CURRENT_SEASON
        }
        
        # Only add status if not "all"
        if status.lower() != "all":
            params["status"] = status.upper()
            
        response = await self._make_request("fixtures", params)
        
        if not response.get('response'):
            if response.get('errors'):
                error_msg = "; ".join(response['errors'].values())
                raise Exception(f"API Error with matches: {error_msg}")
            raise Exception("Couldn't get match data from API - empty response")
        
        # Process each match
        for match in response['response']:
            match_data = {
                'id': match['fixture']['id'],
                'date': match['fixture']['date'],
                'referee': match['fixture'].get('referee'),
                'venue': match['fixture'].get('venue', {}).get('name'),
                'status': {
                    'long': match['fixture']['status']['long'],
                    'short': match['fixture']['status']['short'],
                    'elapsed': match['fixture']['status']['elapsed']
                },
                'league': {
                    'id': match['league']['id'],
                    'name': match['league']['name'],
                    'round': match['league']['round']
                },
                'teams': {
                    'home': {
                        'id': match['teams']['home']['id'],
                        'name': match['teams']['home']['name'],
                        'logo': match['teams']['home']['logo'],
                        'winner': match['teams']['home']['winner']
                    },
                    'away': {
                        'id': match['teams']['away']['id'],
                        'name': match['teams']['away']['name'],
                        'logo': match['teams']['away']['logo'],
                        'winner': match['teams']['away']['winner']
                    }
                },
                'goals': match['goals'],
                'score': match['score'],
                'last_updated': datetime.now().isoformat()
            }
            
            # Save to a JSON file named with the match ID
            self._save_json('matches', f"{match['fixture']['id']}.json", match_data)
            
            # Get and save statistics for finished matches
            if match['fixture']['status']['short'] == 'FT':
                await self._update_match_stats(match['fixture']['id'])
    
    async def _update_match_stats(self, match_id: int):
        """Get and save statistics for a specific match."""
        response = await self._make_request("fixtures/statistics", {"fixture": match_id})
        
        if response.get('response'):
            self._save_json('stats', f"match_{match_id}.json", response['response'])
    
    async def update_injuries(self):
        """Get and save current Tottenham injuries."""
        # Get injury data from API
        params = {
            "team": TOTTENHAM_TEAM_ID,
            "season": CURRENT_SEASON,
            "league": PREMIER_LEAGUE_ID
        }
        response = await self._make_request("injuries", params)
        
        if not response.get('response'):
            if response.get('errors'):
                error_msg = "; ".join(response['errors'].values())
                raise Exception(f"API Error with injuries: {error_msg}")
            raise Exception("Couldn't get injury data from API - empty response")
        
        # Save all injuries in one file since there usually aren't many
        injuries_data = {
            'injuries': [
                {
                    'player': {
                        'id': injury['player']['id'],
                        'name': injury['player']['name'],
                        'photo': injury['player'].get('photo')
                    },
                    'team': {
                        'id': injury['team']['id'],
                        'name': injury['team']['name'],
                        'logo': injury['team'].get('logo')
                    },
                    'fixture': injury.get('fixture'),
                    'reason': injury.get('type') or injury.get('reason'),
                    'since': injury.get('fixture', {}).get('date')
                }
                for injury in response['response']
            ],
            'last_updated': datetime.now().isoformat()
        }
        
        # Save to a single injuries file
        self._save_json('injuries', 'current.json', injuries_data)
    
    def get_all_players(self) -> List[Dict]:
        """
        Get all saved player data.
        
        Returns:
            List of player dictionaries
        """
        players = []
        player_dir = os.path.join('data', 'players')
        
        # Read each player file in the players directory
        for filename in os.listdir(player_dir):
            if filename.endswith('.json'):
                player_data = self._load_json('players', filename)
                if player_data:
                    # Try to get player stats too
                    stats = self._load_json('stats', f"player_{player_data['id']}.json")
                    if stats:
                        player_data['statistics'] = stats.get('statistics', [])
                    players.append(player_data)
        
        return players
    
    def get_recent_matches(self, limit: int = 5) -> List[Dict]:
        """
        Get most recent matches.
        
        Args:
            limit: Maximum number of matches to return
            
        Returns:
            List of match dictionaries
        """
        matches = []
        match_dir = os.path.join('data', 'matches')
        
        # Read all match files
        for filename in os.listdir(match_dir):
            if filename.endswith('.json'):
                match_data = self._load_json('matches', filename)
                if match_data:
                    # Try to get match stats too
                    stats = self._load_json('stats', f"match_{match_data['id']}.json")
                    if stats:
                        match_data['statistics'] = stats
                    matches.append(match_data)
        
        # Sort by date (newest first) and return limited number
        matches.sort(key=lambda x: x['date'], reverse=True)
        return matches[:limit]
    
    def get_current_injuries(self) -> Dict:
        """
        Get current injury list.
        
        Returns:
            Dictionary with current injuries
        """
        return self._load_json('injuries', 'current.json') or {'injuries': []}

# Example usage:
async def main():
    """Example of how to use the API client."""
    try:
        # Create API client
        api = SimpleFootballAPI()
        
        # Update all data
        print("Updating squad data...")
        await api.update_squad()
        
        print("Updating match data...")
        await api.update_matches()
        
        print("Updating injury data...")
        await api.update_injuries()
        
        # Read some data back
        print("\nCurrent squad:")
        for player in api.get_all_players():
            print(f"- {player['name']} ({player['position']})")
        
        print("\nRecent matches:")
        for match in api.get_recent_matches(3):
            print(f"- {match['teams']['home']['name']} vs {match['teams']['away']['name']}")
        
        print("\nCurrent injuries:")
        injuries = api.get_current_injuries()
        for injury in injuries['injuries']:
            print(f"- {injury['player']['name']}: {injury['reason']}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
