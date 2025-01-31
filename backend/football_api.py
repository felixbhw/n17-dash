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
from pathlib import Path
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Load environment variables from project root .env file
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / '.env'
load_dotenv(ENV_PATH)

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
        # Handle v2 endpoints differently
        if endpoint.startswith('v2/'):
            endpoint = endpoint[3:]  # Remove 'v2/' prefix
            url = f"https://v2.api-football.com/{endpoint}"
            headers = {
                "x-apisports-key": self.api_key
            }
        else:
            url = f"{self.base_url}/{endpoint}"
            headers = self.headers
        
        try:
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_data = await response.json()
                    
                    # Handle v2 API response format
                    if endpoint.startswith('players/search/'):
                        if response_data.get('api', {}).get('results') == 0:
                            return {'response': []}
                        return {'response': response_data.get('api', {}).get('players', [])}
                    
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
    
    def _load_json(self, subdir: str, filename: str) -> Optional[Dict]:
        """Load JSON data from a file."""
        try:
            filepath = PROJECT_ROOT / 'backend' / 'data' / subdir / filename
            if filepath.exists():
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
    
    def _score_player_match(self, search_name: str, api_player: Dict) -> float:
        """
        Score how well an API player result matches our search target.
        Returns a score between 0-1, where 1 is a perfect match.
        """
        search_parts = search_name.lower().split()
        if len(search_parts) < 2:
            return 0
            
        search_first, search_last = search_parts[0], search_parts[-1]
        
        # Get API player names, safely handling None values
        api_first = (api_player.get('firstname') or '').lower()
        api_last = (api_player.get('lastname') or '').lower()
        
        score = 0.0
        
        # Exact last name match is most important
        if search_last == api_last:
            score += 0.6
        elif search_last in api_last or api_last in search_last:
            score += 0.3
            
        # First name match adds points
        if search_first == api_first:
            score += 0.4
        elif search_first and api_first and search_first[0] == api_first[0]:  # Initial matches
            score += 0.2
        elif search_first in api_first or api_first in search_first:
            score += 0.1
            
        return min(1.0, score)  # Cap at 1.0

    async def search_player(self, name: str, team_id: int = None) -> List[Dict]:
        """
        Search for a player by name using an improved search strategy:
        1. If team_id provided, check that team's current squad first
        2. Try v2 search with various name combinations that meet 4-char minimum
        3. Use smarter name matching that handles abbreviated names (e.g. "M. Tel")
        
        Args:
            name: Player name to search for
            team_id: Optional team ID to check squad first
            
        Returns:
            List containing matches, best matches first
        """
        results = []
        name = name.strip()
        
        # If team_id provided, check that team's squad first
        if team_id:
            logger.debug(f"Checking squad for team {team_id}")
            squad_response = await self._make_request("players/squads", {"team": team_id})
            
            if squad_response.get('response'):
                for player in squad_response['response'][0]['players']:
                    score = self._score_player_match_v2(name, {
                        'player_name': player['name'],
                        'firstname': player.get('firstname'),
                        'lastname': player.get('lastname')
                    })
                    if score > 0.5:  # Higher threshold for squad matches
                        logger.info(f"Found player in team squad: {player['name']} (score: {score:.2f})")
                        return [{
                            'id': player['id'],
                            'name': player['name'],
                            'firstname': player.get('firstname'),
                            'lastname': player.get('lastname'),
                            'team': team_id,
                            'position': player.get('position'),
                            'photo': player.get('photo'),
                            'match_score': score
                        }]

        # Clean name - API requires alphabetic characters only
        clean_name = ''.join(c for c in name if c.isalpha() or c.isspace())
        name_parts = clean_name.split()
        
        # Generate search variants that meet 4-char minimum
        search_variants = set()
        
        # If we have multiple parts, try combinations
        if len(name_parts) > 1:
            # Full name if 4+ chars
            full_name = ''.join(name_parts)
            if len(full_name) >= 4:
                search_variants.add(full_name)
            
            # First + Last initial if first name is 4+ chars
            if len(name_parts[0]) >= 4:
                search_variants.add(name_parts[0])
            
            # Last name if 4+ chars
            if len(name_parts[-1]) >= 4:
                search_variants.add(name_parts[-1])
            
            # Try middle name if present and 4+ chars
            if len(name_parts) > 2:
                for part in name_parts[1:-1]:
                    if len(part) >= 4:
                        search_variants.add(part)
        
        # If we have a single part that's 4+ chars, use it
        elif len(clean_name) >= 4:
            search_variants.add(clean_name)
            
        if not search_variants:
            logger.warning(f"No valid search variants (4+ chars) found for: {name}")
            return []
            
        # Try each variant
        seen_players = set()  # Track unique players
        for search_term in search_variants:
            logger.debug(f"Searching API with term: {search_term}")
            response = await self._make_request(f"v2/players/search/{search_term}")
            
            if response.get('response'):
                for player in response['response']:
                    player_id = player['player_id']
                    if player_id in seen_players:
                        continue
                        
                    seen_players.add(player_id)
                    score = self._score_player_match_v2(name, player)
                    
                    if score > 0.6:  # Higher threshold for general search
                        result = {
                            'id': player_id,
                            'name': player['player_name'],
                            'firstname': player['firstname'],
                            'lastname': player['lastname'],
                            'team': None,
                            'position': player['position'],
                            'photo': None,
                            'match_score': score
                        }
                        results.append(result)
        
        # Sort by match score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Return all matches above threshold
        matches = [r for r in results if r['match_score'] > 0.6]  # Higher threshold
        if matches:
            logger.info(f"Found {len(matches)} matches for {name}, best: {matches[0]['name']} (score: {matches[0]['match_score']:.2f})")
            return matches
            
        logger.warning(f"No confident matches found for: {name}")
        return []
    
    def _score_player_match_v2(self, search_name: str, api_player: Dict) -> float:
        """
        Improved scoring for player name matches that handles:
        - Abbreviated first names (e.g. "M. Tel" matches "Mathys Tel")
        - Middle names
        - Partial matches
        
        Returns:
            Float score between 0-1, where 1 is perfect match
        """
        # Get API player names, safely handling None values
        api_name = api_player.get('player_name', '').lower()
        api_first = (api_player.get('firstname') or '').lower()
        api_last = (api_player.get('lastname') or '').lower()
        
        search_name = search_name.lower()
        search_parts = search_name.split()
        
        score = 0.0
        
        # Exact full name match
        if search_name == api_name:
            return 1.0
            
        # Handle single word search
        if len(search_parts) == 1:
            search_term = search_parts[0]
            # Check if it matches last name
            if search_term == api_last:
                score += 0.8
            # Or first name
            elif search_term == api_first:
                score += 0.7
            # Or is contained in either
            elif search_term in api_last or api_last in search_term:
                score += 0.4
            elif search_term in api_first or api_first in search_term:
                score += 0.3
            return score
            
        # Multiple word search
        search_first, search_last = search_parts[0], search_parts[-1]
        
        # Last name matching (most important)
        if search_last == api_last:
            score += 0.6
        elif search_last in api_last or api_last in search_last:
            score += 0.3
            
        # First name matching
        if search_first == api_first:
            score += 0.4
        # Handle abbreviated first names (e.g. "M. Tel" matches "Mathys Tel")
        elif len(search_first) == 1 and api_first.startswith(search_first):
            score += 0.35
        elif search_first and api_first and search_first[0] == api_first[0]:
            score += 0.2
        elif search_first in api_first or api_first in search_first:
            score += 0.1
            
        return min(1.0, score)
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """
        Helper to check if two names match, handling:
        - Case differences
        - Abbreviated first names
        - Different word orders
        """
        name1 = name1.lower()
        name2 = name2.lower()
        
        # Exact match
        if name1 == name2:
            return True
            
        # Split into parts
        parts1 = name1.split()
        parts2 = name2.split()
        
        # Handle abbreviated first names
        if len(parts1) > 1 and len(parts2) > 1:
            # Check if first parts match as abbreviation
            first1, first2 = parts1[0], parts2[0]
            if len(first1) == 1 and first2.startswith(first1):
                return parts1[-1] == parts2[-1]
            if len(first2) == 1 and first1.startswith(first2):
                return parts1[-1] == parts2[-1]
                
        # Check if all parts from one name exist in the other
        return all(part in parts2 for part in parts1) or all(part in parts1 for part in parts2)
    
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
        player_dir = PROJECT_ROOT / 'backend' / 'data' / 'players'
        
        # Read each player file in the players directory
        if not player_dir.exists():
            logger.error(f"Player directory not found: {player_dir}")
            return []
            
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

    async def update_transfer_linked_players_stats(self):
        """Fetch and update stats for all players that have transfer links"""
        try:
            links_dir = PROJECT_ROOT / 'backend' / 'data' / 'links'
            stats_dir = PROJECT_ROOT / 'backend' / 'data' / 'stats'
            stats_dir.mkdir(exist_ok=True)
            
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

            # Fetch stats for each player
            for player_id in player_ids:
                try:
                    # Get player info
                    response = await self._make_request("players", {
                        "id": player_id,
                        "season": CURRENT_SEASON
                    })

                    if not response.get('response'):
                        logger.warning(f"No data found for player {player_id}")
                        continue

                    # Save player stats
                    stats_file = stats_dir / f"player_{player_id}.json"
                    with open(stats_file, 'w') as f:
                        json.dump(response['response'][0], f, indent=2)
                    
                    logger.info(f"Updated stats for player {player_id}")
                    
                    # API rate limiting - sleep between requests
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error fetching stats for player {player_id}: {e}")
                    continue
                
            return {"status": "success", "message": f"Updated stats for {len(player_ids)} players"}
            
        except Exception as e:
            logger.error(f"Error updating transfer linked players stats: {e}")
            raise Exception(f"Failed to update player stats: {str(e)}")

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
