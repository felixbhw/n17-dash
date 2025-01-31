import os
import json
from pathlib import Path
import logging
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from datetime import datetime
from ...football_api import SimpleFootballAPI

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Known sources/journalists to exclude from player detection
KNOWN_SOURCES = {
    "Paul O Keefe",
    "Alasdair Gold",
    "Fabrizio Romano",
    "David Ornstein",
    "Dan Kilpatrick",
    "Charlie Eccleshare",
    "Jack Pitt-Brooke",
    "Matt Law",
    "Jonathan Veal",
    "Tom Barclay",
    "Mike McGrath",
    "John Percy",
    "Simon Stone",
    "James Ducker",
    "Jason Burt",
    "Sam Wallace",
    "Miguel Delaney",
    "Melissa Reddy",
    "James Olley",
    "Rob Dorsett",
    "Lyall Thomas",
    "Pete O'Rourke"
}

class LLMService:
    def __init__(self):
        """Initialize LLM service with OpenAI client and Football API"""
        logger.info("Initializing LLM Service...")
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")
            
        self.client = AsyncOpenAI(api_key=api_key)
        self.football_api = SimpleFootballAPI()
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        
        # Load manual player mappings
        self.manual_mappings = self._load_manual_mappings()
        logger.info(f"LLM Service initialized with data directory: {self.data_dir}")
        
    def _load_manual_mappings(self) -> Dict[str, Dict]:
        """Load manual player mappings from JSON file"""
        mappings_file = self.data_dir / 'manual_player_mappings.json'
        if not mappings_file.exists():
            # Create default mappings file if it doesn't exist
            default_mappings = {
                "Mathys Tel": {
                    "id": 270510,
                    "name": "M. Tel",
                    "current_club": "Bayern Munich",
                    "team_id": 157
                }
                # Add more manual mappings here as needed
            }
            mappings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(mappings_file, 'w') as f:
                json.dump(default_mappings, f, indent=2)
            return default_mappings
            
        try:
            with open(mappings_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading manual mappings: {e}")
            return {}
    
    def _check_manual_mapping(self, player_name: str) -> Optional[Dict]:
        """Check if player has a manual mapping"""
        # Try exact match first
        if player_name in self.manual_mappings:
            return self.manual_mappings[player_name]
            
        # Try case-insensitive match
        player_lower = player_name.lower()
        for name, data in self.manual_mappings.items():
            if name.lower() == player_lower:
                return data
                
        return None
    
    async def extract_info_from_news(self, news_file: Path) -> Dict:
        """Extract transfer-related information from a news file using LLM"""
        logger.info(f"Processing news file: {news_file.name}")
        
        # Load news data
        try:
            with open(news_file) as f:
                news_data = json.load(f)
            logger.debug(f"Loaded news data: {news_data['title']}")
        except Exception as e:
            logger.error(f"Failed to load news file {news_file.name}: {e}")
            return None
        
        # Prepare prompt for GPT-4
        prompt = f"""Analyze this football transfer news and extract key information.
Title: {news_data['title']}
Content: {news_data['content']}

IMPORTANT: The following are known journalists/sources and should NOT be treated as players:
{", ".join(sorted(KNOWN_SOURCES))}

Return a JSON object with EXACTLY this structure:
{{
    "players": [
        {{
            "name": "Full Player Name",
            "current_club": "Current Club Name"
        }}
    ],
    "clubs": ["Club Name 1", "Club Name 2"],
    "transfer_type": "transfer|loan|loan_with_option|loan_with_obligation|unclear",
    "direction": "incoming|outgoing",
    "price": {{
        "amount": number or null,
        "currency": "GBP|EUR|USD" or null
    }},
    "confidence": number between 0-100
}}

Only include information that is explicitly mentioned or very strongly implied.
Do NOT include any journalists or sources in the players list.
Ensure the response is VALID JSON that matches the structure above exactly.
"""
        
        # Get LLM response with JSON format enforced
        logger.debug("Sending request to GPT-4...")
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": "You are a football transfer news analyst. Extract key information from news articles and return it in strict JSON format matching the specified structure exactly."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            logger.debug("Received response from GPT-4")
        except Exception as e:
            logger.error(f"OpenAI API error for {news_file.name}: {e}")
            return None
        
        # Parse LLM response
        try:
            extracted = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully extracted information from {news_file.name}: {extracted}")
            return extracted
        except Exception as e:
            logger.error(f"Error parsing LLM response for {news_file.name}: {e}")
            return None
    
    def _get_unprocessed_news(self) -> List[Path]:
        """Get list of news files that haven't been processed into link files yet"""
        news_dir = self.data_dir / 'news'
        links_dir = self.data_dir / 'links'
        
        logger.debug(f"Checking for unprocessed news in {news_dir}")
        
        # Get all news files
        news_files = list(news_dir.glob('r-*.json'))
        logger.debug(f"Found {len(news_files)} total news files")
        
        # Filter out ones that already have link files
        unprocessed = []
        for news_file in news_files:
            news_id = news_file.stem  # filename without extension
            potential_link_files = list(links_dir.glob(f'*_{news_id}.json'))
            if not potential_link_files:
                logger.debug(f"Found unprocessed news file: {news_file.name}")
                unprocessed.append(news_file)
        
        return unprocessed
    
    async def process_pending_news(self):
        """Process all pending news files and create link files"""
        unprocessed = self._get_unprocessed_news()
        logger.info(f"Found {len(unprocessed)} unprocessed news files")
        
        for news_file in unprocessed:
            logger.info(f"Processing news file: {news_file.name}")
            try:
                # Extract info using LLM
                extracted = await self.extract_info_from_news(news_file)
                if not extracted:
                    logger.warning(f"No information extracted from {news_file.name}, skipping")
                    continue
                
                # Process each player
                processed_players = []
                for player in extracted['players']:
                    player_name = player['name']
                    logger.info(f"Processing player: {player_name}")
                    
                    # First check manual mappings
                    manual_mapping = self._check_manual_mapping(player_name)
                    if manual_mapping:
                        logger.info(f"Found manual mapping for {player_name}: {manual_mapping}")
                        player_data = {
                            'id': manual_mapping['id'],
                            'name': manual_mapping['name'],
                            'is_squad_player': False,
                            'team_id': manual_mapping.get('team_id')
                        }
                    else:
                        # Continue with existing squad/API search logic
                        # First try to find in current squad
                        current_players = self.football_api.get_all_players()
                        squad_player = next((p for p in current_players if p['name'].lower() == player_name.lower()), None)
                        
                        if squad_player:
                            logger.debug(f"Found {player_name} in current squad")
                            player_data = {
                                'id': squad_player['id'],
                                'name': squad_player['name'],
                                'is_squad_player': True
                            }
                        else:
                            logger.debug(f"Searching API for player: {player_name}")
                            # Search for player in API
                            search_results = await self.football_api.search_player(player_name)
                            if search_results:
                                found_player = search_results[0]
                                logger.info(f"Found {player_name} in API search with ID: {found_player['id']}")
                                player_data = {
                                    'id': found_player['id'],
                                    'name': found_player['name'],
                                    'is_squad_player': False,
                                    'last_updated': datetime.now().isoformat()
                                }
                                # Save to players directory
                                player_file = self.data_dir / 'players' / f"{found_player['id']}.json"
                                logger.debug(f"Saving player data to {player_file}")
                                with open(player_file, 'w') as f:
                                    json.dump(player_data, f, indent=2)
                            else:
                                logger.warning(f"Could not find {player_name} in API search")
                                player_data = {
                                    'name': player_name,
                                    'is_squad_player': False,
                                    'last_updated': datetime.now().isoformat()
                                }
                    
                    # Create processed player entry with all available data
                    processed_player = {
                        'name': player_data['name'],
                        'current_club': player['current_club'] or manual_mapping.get('current_club') if manual_mapping else player['current_club'],
                        'is_squad_player': player_data.get('is_squad_player', False)
                    }
                    if 'id' in player_data:
                        processed_player['id'] = player_data['id']
                        logger.debug(f"Added player ID {player_data['id']} to processed player data")
                    if 'team_id' in player_data:
                        processed_player['team_id'] = player_data['team_id']
                    processed_players.append(processed_player)
                    logger.debug(f"Processed player data: {processed_player}")
                
                # Create link file
                link_data = {
                    'players': processed_players,  # Now includes IDs when available
                    'clubs': extracted['clubs'],
                    'transfer_type': extracted['transfer_type'],
                    'direction': extracted['direction'],
                    'price': extracted.get('price'),
                    'confidence': extracted['confidence'],
                    'news_file': news_file.stem,
                    'last_updated': datetime.now().isoformat()
                }
                
                # Save link file
                link_file = self.data_dir / 'links' / f"link_{news_file.stem}.json"
                logger.info(f"Saving link file to {link_file}")
                with open(link_file, 'w') as f:
                    json.dump(link_data, f, indent=2)
                
                logger.info(f"Successfully created link file for {news_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing news file {news_file.name}: {e}", exc_info=True)
                continue 