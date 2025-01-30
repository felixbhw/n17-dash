"""Test script for API-Football data transformers."""

import asyncio
import json
from datetime import datetime
from football_api import APIFootballClient, DataTransformer

async def test_transformers():
    """Test the data transformers with live API data."""
    client = APIFootballClient()
    
    # Test parameters
    team_id = 47  # Tottenham
    league_id = 39  # Premier League
    player_id = 186  # Son Heung-min
    season = 2023  # Current season
    
    try:
        # Test team transformation
        print("\nTesting team transformation:")
        team_response = await client.get_team_info(team_id)
        team_data = DataTransformer.transform_team(team_response)
        print(json.dumps(team_data, indent=2))
        
        # Test player transformation
        print("\nTesting player transformation:")
        player_response = await client.get_player_info(player_id, season=season)
        player_data = DataTransformer.transform_player(player_response)
        print(json.dumps(player_data, indent=2))
        
        # Test matches transformation
        print("\nTesting matches transformation:")
        matches_response = await client.get_matches(team_id, season=season)
        matches_data = DataTransformer.transform_match(matches_response)
        if matches_data:
            print(json.dumps(matches_data[0], indent=2))  # Print first match as example
        
        # Test injuries transformation
        print("\nTesting injuries transformation:")
        injuries_response = await client.get_injuries(team_id, season=season)
        injuries_data = DataTransformer.transform_injury(injuries_response)
        if injuries_data:
            print(json.dumps(injuries_data[0], indent=2))  # Print first injury as example
        
        # Test transfers transformation
        print("\nTesting transfers transformation:")
        transfers_response = await client.get_transfer_history(team_id)
        transfers_data = DataTransformer.transform_transfer(transfers_response)
        if transfers_data:
            print(json.dumps(transfers_data[0], indent=2))  # Print first transfer as example
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_transformers()) 