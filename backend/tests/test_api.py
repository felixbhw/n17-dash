"""Test script for API-Football client."""

import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from football_api import APIFootballClient

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

async def test_api_responses():
    """Test various API endpoints and save responses."""
    client = APIFootballClient()
    
    # Test parameters
    team_id = 47  # Tottenham
    league_id = 39  # Premier League
    player_id = 186  # Son Heung-min
    season = 2023  # Current season
    
    # Test and save responses
    responses = {}
    
    try:
        # Get team info
        responses['team'] = await client.get_team_info(team_id)
        print("Got team info")
        
        # Get team squad
        responses['squad'] = await client.get_team_squad(team_id)
        print("Got team squad")
        
        # Get team statistics
        responses['team_stats'] = await client.get_team_statistics(team_id, league_id, season)
        print("Got team statistics")
        
        # Get matches
        responses['matches'] = await client.get_matches(team_id, season=season)
        print("Got matches")
        
        # Get injuries
        responses['injuries'] = await client.get_injuries(team_id, season=season)
        print("Got injuries")
        
        # Get player info
        responses['player'] = await client.get_player_info(player_id, season=season)
        print("Got player info")
        
        # Get player statistics
        responses['player_stats'] = await client.get_player_statistics(player_id, season=season)
        print("Got player statistics")
        
        # Get league standings
        responses['standings'] = await client.get_league_standings(league_id, season=season)
        print("Got league standings")
        
        # Save responses to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f'api_responses_{timestamp}.json', 'w') as f:
            json.dump(responses, f, indent=2)
        
        print(f"Responses saved to api_responses_{timestamp}.json")
        
        # Print rate limit info if available
        if 'x-ratelimit-remaining' in responses.get('team', {}).get('headers', {}):
            print(f"Rate limit remaining: {responses['team']['headers']['x-ratelimit-remaining']}")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print(f"API Key being used: {os.getenv('API_FOOTBALL_KEY')}")

if __name__ == "__main__":
    asyncio.run(test_api_responses()) 