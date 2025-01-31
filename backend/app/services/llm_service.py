import os
import json
import copy
from pathlib import Path
import logging
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from datetime import datetime
from httpx import AsyncClient
from bs4 import BeautifulSoup
from ...football_api import SimpleFootballAPI

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# List of known journalists to exclude from player detection
KNOWN_JOURNALISTS = {
    "Paul O Keefe", "Alasdair Gold", "Fabrizio Romano", "David Ornstein",
    "Dan Kilpatrick", "Charlie Eccleshare", "Jack Pitt-Brooke", "Matt Law",
    "Jonathan Veal", "Tom Barclay", "Mike McGrath", "John Percy",
    "Simon Stone", "James Ducker", "Jason Burt", "Sam Wallace",
    "Miguel Delaney", "Melissa Reddy", "James Olley", "Rob Dorsett",
    "Lyall Thomas", "Pete O'Rourke"
}

class LLMService:
    """Service for processing transfer news using GPT-4 and managing player data"""
    
    def __init__(self):
        """Initialize the service with OpenAI and Football API clients"""
        # Get OpenAI API key from environment
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in .env file")
        
        # Initialize clients
        self.client = AsyncOpenAI(api_key=api_key)
        self.football_api = SimpleFootballAPI()
        
        # Set up data directories
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        for subdir in ['links', 'players', 'news']:
            (self.data_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Load player mappings
        self.player_mappings = self._load_player_mappings()
        
        logger.info("LLM Service initialized successfully")
    
    def _load_player_mappings(self) -> Dict[str, Dict]:
        """Load manual player name mappings from JSON file"""
        mappings_file = self.data_dir / 'manual_player_mappings.json'
        
        # Create default mappings if file doesn't exist
        if not mappings_file.exists():
            default_mappings = {
                "Mathys Tel": {
                    "id": 270510,
                    "name": "M. Tel",
                    "current_club": "Bayern Munich",
                    "team_id": 157
                }
            }
            with open(mappings_file, 'w') as f:
                json.dump(default_mappings, f, indent=2)
            return default_mappings
        
        # Load existing mappings
        try:
            with open(mappings_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading player mappings: {e}")
            return {}
    
    def _normalize_player_name(self, name: str) -> str:
        """Normalize player name to prevent duplicates"""
        # Remove common prefixes/suffixes
        name = name.lower().strip()
        prefixes = ['mr ', 'sir ']
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        # Handle common nicknames and variations
        name_variations = {
            'dan': 'daniel',
            'danny': 'daniel',
            'mike': 'michael',
            'micky': 'michael',
            'alex': 'alexander',
            'rob': 'robert',
            'bob': 'robert',
            'jim': 'james',
            'jimmy': 'james',
            'tom': 'thomas',
            'tommy': 'thomas',
            'bill': 'william',
            'billy': 'william',
            'will': 'william'
        }
        
        # Split name into parts
        parts = name.split()
        if len(parts) > 0:
            # Check if first name has a known variation
            if parts[0] in name_variations:
                parts[0] = name_variations[parts[0]]
        
        return ' '.join(parts)

    async def _get_player_id(self, name: str) -> Optional[int]:
        """Find player ID using various methods (mappings, squad, API)"""
        normalized_name = self._normalize_player_name(name)
        
        # Check existing player files first
        existing_files = list((self.data_dir / 'links').glob('player_*.json'))
        for file in existing_files:
            try:
                with open(file) as f:
                    data = json.load(f)
                    if self._normalize_player_name(data['canonical_name']) == normalized_name:
                        return data['player_id']
            except Exception:
                continue
        
        # Check manual mappings
        for mapped_name, data in self.player_mappings.items():
            if self._normalize_player_name(mapped_name) == normalized_name:
                return data['id']
        
        # Check current squad
        squad = self.football_api.get_all_players()
        squad_player = next(
            (p for p in squad if self._normalize_player_name(p['name']) == normalized_name),
            None
        )
        if squad_player:
            return squad_player['id']
        
        # Search API as last resort
        api_results = await self.football_api.search_player(name)
        if api_results:
            return api_results[0]['id']
        
        return None
    
    async def _get_article_text(self, url: str) -> str:
        """Scrape article text content from URL"""
        try:
            async with AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                soup = BeautifulSoup(response.text, 'html.parser')
                return ' '.join(p.get_text() for p in soup.find_all('p'))
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return ""
    
    def _get_llm_prompt(self, title: str, content: str, player_data: dict) -> str:
        """Build prompt for GPT-4 analysis"""
        return f"""
        Analyze this transfer news update and respond with a JSON object.
        
        Current Player Status:
        {json.dumps(player_data, indent=2)}
        
        New Information:
        Title: {title}
        Content: {content[:3000]}
        
        Return a JSON object with ONLY these fields if they change:
        {{
            "transfer_status": "hearsay|rumors|developing|here we go!",
            "direction": "incoming|outgoing",
            "timeline": {{
                "event_type": "string",
                "details": "string",
                "confidence": number
            }},
            "related_clubs": [
                {{
                    "name": "string",
                    "role": "current|destination|interested"
                }}
            ]
        }}
        
        Status Guidelines:
        - hearsay: Initial reports or weak sources
        - rumors: Multiple sources reporting but no concrete moves
        - developing: Active negotiations or strong interest
        - here we go!: Deal is confirmed by club or highly reliable source
        
        Club Role Guidelines:
        - current: The player's current club
        - destination: The club the player is confirmed to be joining
        - interested: Club showing interest but no agreement
        
        Direction Guidelines:
        - incoming: Player potentially joining Tottenham
        - outgoing: Current Tottenham player potentially leaving
        
        Status should be "here we go!" when:
        1. Club has officially announced the transfer
        2. Medical is completed
        3. Personal terms are agreed AND clubs have reached full agreement
        4. Multiple tier 1 sources confirm it's a done deal
        
        Only include fields that have new/changed information. Focus on facts and confidence levels.
        """
    
    async def _analyze_with_gpt4(self, prompt: str) -> dict:
        """Get structured analysis from GPT-4o-mini"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a football transfer analyst. You must ALWAYS respond with valid JSON only, no other text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {str(e)[:100]}...")
                return {"error": "Invalid response format", "players": []}
                
        except Exception as e:
            logger.error(f"GPT analysis failed: {e}")
            return {"error": str(e), "players": []}
    
    def _parse_amount(self, amount_str: str) -> tuple:
        """Parse amount string into numeric value and type"""
        if not amount_str:
            return 0, None
            
        original_str = str(amount_str).lower().strip()
        
        # Handle loan cases
        if 'loan' in original_str:
            return 0, 'loan'
            
        # Determine currency from original string
        currency = '€'  # Default to euros
        if '£' in original_str:
            currency = '£'
        elif '$' in original_str:
            currency = '$'
        
        # Clean string for numeric extraction
        amount_str = original_str.replace('€', '').replace('£', '').replace('$', '').strip()
        
        # Extract numeric value
        import re
        numeric_match = re.search(r'(\d+(?:\.\d+)?)', amount_str)
        if not numeric_match:
            return 0, currency
            
        amount = float(numeric_match.group(1))
        
        # Convert to millions if needed
        if 'm' in original_str or 'million' in original_str:
            amount = amount  # Already in millions
        elif 'k' in original_str or 'thousand' in original_str:
            amount = amount / 1000
        
        return amount, currency

    def _update_player_data(self, current: dict, new: dict, news_id: str) -> dict:
        """Merge new analysis with existing player data"""
        result = copy.deepcopy(current)
        
        # Initialize required fields if missing
        result.setdefault('timeline', [])
        result.setdefault('related_clubs', [])
        result.setdefault('transfer_status', 'hearsay')
        result.setdefault('direction', None)
        
        # Add timeline event
        if 'timeline' in new:
            # Handle both string and dict timeline events
            if isinstance(new['timeline'], list):
                for event in new['timeline']:
                    if isinstance(event, str):
                        event_data = {
                            "event": event,
                            "date": datetime.now().isoformat(),
                            "news_ids": [news_id]
                        }
                    else:
                        event_data = {
                            **event,
                            "date": datetime.now().isoformat(),
                            "news_ids": [news_id]
                        }
                    result['timeline'].append(event_data)
            elif isinstance(new['timeline'], dict):
                event_data = {
                    **new['timeline'],
                    "date": datetime.now().isoformat(),
                    "news_ids": [news_id]
                }
                result['timeline'].append(event_data)
        
        # Update status if confidence is higher
        if 'transfer_status' in new:
            status_levels = {
                'hearsay': 0,
                'rumors': 1,
                'developing': 2,
                'here we go!': 3
            }
            current_level = status_levels.get(result['transfer_status'], 0)
            new_level = status_levels.get(new['transfer_status'], 0)
            
            if new_level > current_level:
                result['transfer_status'] = new['transfer_status']
        
        # Update direction
        if 'direction' in new:
            result['direction'] = new['direction']
        
        # Update clubs
        if 'related_clubs' in new:
            # Handle both string and dict club references
            new_clubs = []
            for club in new['related_clubs']:
                if isinstance(club, str):
                    club_data = {
                        "name": club,
                        "role": "interested"  # Default role
                    }
                else:
                    club_data = club
                new_clubs.append(club_data)
            
            # Merge with existing clubs, using tuple of name and role as key
            result['related_clubs'] = list({
                (c.get('name', ''), c.get('role', '')): c
                for c in [*current.get('related_clubs', []), *new_clubs]
            }.values())
        
        return result
    
    def _get_unprocessed_news(self) -> List[Path]:
        """Get list of news files that haven't been processed"""
        processed_file = self.data_dir / 'processed_news.json'
        
        # Load processed IDs
        processed_ids = set()
        if processed_file.exists():
            try:
                with open(processed_file) as f:
                    processed_ids = set(json.load(f))
            except Exception as e:
                logger.error(f"Error loading processed news IDs: {e}")
        
        # Find unprocessed files
        all_news = list(self.data_dir.glob('news/r-*.json'))
        return [f for f in all_news if f.stem not in processed_ids]
    
    def _mark_processed(self, news_id: str):
        """Mark a news item as processed"""
        processed_file = self.data_dir / 'processed_news.json'
        
        # Load existing
        processed_ids = set()
        if processed_file.exists():
            with open(processed_file) as f:
                processed_ids = set(json.load(f))
        
        # Add new and save
        processed_ids.add(news_id)
        with open(processed_file, 'w') as f:
            json.dump(list(processed_ids), f)
    
    async def _ensure_player_stats(self, player_id: int, player_name: str):
        """Ensure player stats are fetched and stored"""
        stats_file = self.data_dir / 'stats' / f'player_{player_id}.json'
        
        if not stats_file.exists():
            logger.info(f"Fetching stats for {player_name} (ID: {player_id})")
            try:
                # Get player info and stats from API
                player_info = await self.football_api.get_player_info(player_id)
                player_stats = await self.football_api.get_player_stats(player_id)
                
                # Combine into single stats file
                stats_data = {
                    "player": {
                        "id": player_id,
                        "name": player_name,
                        "firstname": player_info.get('firstname'),
                        "lastname": player_info.get('lastname'),
                        "age": player_info.get('age'),
                        "birth": player_info.get('birth', {}),
                        "nationality": player_info.get('nationality'),
                        "height": player_info.get('height'),
                        "weight": player_info.get('weight'),
                        "injured": player_info.get('injured', False),
                        "photo": player_info.get('photo')
                    },
                    "statistics": player_stats
                }
                
                # Save to file
                stats_file.parent.mkdir(parents=True, exist_ok=True)
                with open(stats_file, 'w') as f:
                    json.dump(stats_data, f, indent=2)
                    
                logger.info(f"Saved stats for {player_name}")
                
            except Exception as e:
                logger.error(f"Failed to fetch stats for {player_name}: {e}")

    async def process_pending_news(self):
        """Main function to process new transfer news"""
        unprocessed = self._get_unprocessed_news()
        if not unprocessed:
            return
            
        logger.info(f"Processing {len(unprocessed)} news items")
        
        for news_file in unprocessed:
            try:
                # Load news data
                with open(news_file) as f:
                    news = json.load(f)
                
                # Get full article content
                article_text = await self._get_article_text(news['url'])
                
                # Initial player detection
                initial_analysis = await self._analyze_with_gpt4(
                    f"""Analyze this transfer news and extract ONLY players that are:
                    1. Currently at Tottenham and might leave, OR
                    2. Potentially joining Tottenham (being linked with a move)
                    
                    Title: {news['title']}
                    Content: {article_text[:1000]}
                    
                    You must respond with ONLY a JSON object in this exact format:
                    {{
                        "players": [
                            {{"name": "Player Full Name", "tottenham_role": "current|target"}}
                        ],
                        "confidence": 90
                    }}
                    
                    The confidence should be between 0-100 indicating how confident you are about the Tottenham connection.
                    Only include players if there is a clear Tottenham connection in the news.
                    Do not include any explanatory text, only the JSON object.
                    """
                )
                
                # Process each player
                players_updated = 0
                for player in initial_analysis.get('players', []):
                    # Skip if no clear Tottenham connection
                    if not player.get('tottenham_role'):
                        continue
                        
                    # Get player ID
                    player_id = await self._get_player_id(player['name'])
                    if not player_id:
                        logger.warning(f"Unknown player: {player['name']}")
                        continue
                    
                    # Ensure we have player stats
                    await self._ensure_player_stats(player_id, player['name'])
                    
                    # Process player updates
                    player_file = self.data_dir / 'links' / f"player_{player_id}.json"
                    if player_file.exists():
                        with open(player_file) as f:
                            player_data = json.load(f)
                    else:
                        player_data = {
                            "player_id": player_id,
                            "canonical_name": player['name'],
                            "transfer_status": "hearsay",
                            "timeline": [],
                            "related_clubs": []
                        }
                    
                    # Get detailed analysis
                    detailed_analysis = await self._analyze_with_gpt4(
                        self._get_llm_prompt(news['title'], article_text, player_data)
                    )
                    
                    # Update player data
                    updated_data = self._update_player_data(
                        player_data,
                        detailed_analysis,
                        news_file.stem
                    )
                    
                    # Save updates
                    with open(player_file, 'w') as f:
                        json.dump(updated_data, f, indent=2)
                    players_updated += 1
                
                # Mark as processed
                self._mark_processed(news_file.stem)
                if players_updated:
                    logger.info(f"Updated {players_updated} players from {news['title'][:60]}...")
                
            except Exception as e:
                logger.error(f"Failed to process {news_file.name}: {e}")
                continue

    async def process_news_file(self, news_file: Path) -> None:
        """Process a single news file and extract transfer information"""
        try:
            # Load the news file
            with open(news_file) as f:
                news_data = json.load(f)
            
            # Get article content if not already fetched
            content = news_data.get('content', '')
            if not content and news_data.get('url'):
                content = await self._get_article_text(news_data['url'])
                news_data['content'] = content
                # Save updated content
                with open(news_file, 'w') as f:
                    json.dump(news_data, f, indent=2)
            
            # Initial player detection
            initial_analysis = await self._analyze_with_gpt4(
                f"""Analyze this transfer news and extract ONLY players that are:
                1. Currently at Tottenham and might leave, OR
                2. Potentially joining Tottenham (being linked with a move)
                
                Title: {news_data['title']}
                Content: {content[:1000]}
                
                You must respond with ONLY a JSON object in this exact format:
                {{
                    "players": [
                        {{"name": "Player Full Name", "tottenham_role": "current|target"}}
                    ],
                    "confidence": 90
                }}
                
                The confidence should be between 0-100 indicating how confident you are about the Tottenham connection.
                Only include players if there is a clear Tottenham connection in the news.
                Do not include any explanatory text, only the JSON object.
                """
            )
            
            # Process each mentioned player
            for player in initial_analysis.get('players', []):
                # Skip if no clear Tottenham connection
                if not player.get('tottenham_role'):
                    continue
                    
                player_name = player['name']
                # Skip known journalists
                if player_name in KNOWN_JOURNALISTS:
                    continue
                    
                # Get or create player ID
                player_id = await self._get_player_id(player_name)
                if not player_id:
                    # Try to search for the player
                    search_results = await self.football_api.search_players(player_name)
                    if search_results:
                        # Use the first result's ID
                        player_id = search_results[0].get('player_id')
                        if player_id:
                            logger.info(f"Found new player {player_name} with ID {player_id}")
                
                if not player_id:
                    logger.warning(f"Could not find ID for player: {player_name}")
                    continue
                
                # Ensure we have player stats
                await self._ensure_player_stats(player_id, player_name)
                
                # Update player links
                links_file = self.data_dir / 'links' / f'player_{player_id}.json'
                current_data = {}
                if links_file.exists():
                    with open(links_file) as f:
                        current_data = json.load(f)
                else:
                    # Create new player record
                    current_data = {
                        "player_id": player_id,
                        "canonical_name": player_name,
                        "transfer_status": "hearsay",
                        "timeline": [],
                        "related_clubs": []
                    }
                
                # Get detailed analysis
                detailed_analysis = await self._analyze_with_gpt4(
                    self._get_llm_prompt(news_data['title'], content, current_data)
                )
                
                # Update with new information
                updated_data = self._update_player_data(
                    current_data,
                    detailed_analysis,
                    news_data['id']
                )
                
                # Save updated data
                links_file.parent.mkdir(parents=True, exist_ok=True)
                with open(links_file, 'w') as f:
                    json.dump(updated_data, f, indent=2)
                
                logger.info(f"Updated player data for {player_name}")
            
            # Mark as processed
            self._mark_processed(news_data['id'])
            
            logger.info(f"Processed news file: {news_file.name}")
            
        except Exception as e:
            logger.error(f"Error processing news file {news_file.name}: {e}")
            raise

    async def create_manual_player(self, name: str, player_id: int) -> dict:
        """Create a player record manually and fetch their data from API"""
        try:
            # Check if player exists
            player_file = self.data_dir / 'links' / f'player_{player_id}.json'
            if player_file.exists():
                raise ValueError(f"Player with ID {player_id} already exists")
            
            # First search for player by name to validate ID
            search_results = await self.football_api.search_players(name)
            if not search_results:
                raise ValueError(f"No players found matching name: {name}")
            
            # Verify the ID matches one of the search results
            player_info = None
            for player in search_results:
                if player.get('player_id') == player_id:
                    player_info = player
                    break
            
            if not player_info:
                raise ValueError(f"Player ID {player_id} not found in search results for {name}")
            
            # Create initial player record
            player_data = {
                "player_id": player_id,
                "canonical_name": name,
                "transfer_status": "hearsay",
                "timeline": [],
                "related_clubs": [],
                "last_updated": datetime.now().isoformat()
            }
            
            # Save player data
            player_file.parent.mkdir(parents=True, exist_ok=True)
            with open(player_file, 'w') as f:
                json.dump(player_data, f, indent=2)
            
            # Save player stats
            stats_dir = self.data_dir / 'stats'
            stats_dir.mkdir(exist_ok=True)
            stats_file = stats_dir / f"player_{player_id}.json"
            
            # Format player info for stats file
            stats_data = {
                "player": {
                    "id": player_id,
                    "name": player_info.get('player_name'),
                    "firstname": player_info.get('firstname'),
                    "lastname": player_info.get('lastname'),
                    "age": player_info.get('age'),
                    "birth": {
                        "date": player_info.get('birth_date'),
                        "place": player_info.get('birth_place'),
                        "country": player_info.get('birth_country')
                    },
                    "nationality": player_info.get('nationality'),
                    "height": player_info.get('height'),
                    "weight": player_info.get('weight'),
                    "injured": False,
                    "photo": None
                },
                "statistics": []
            }
            
            with open(stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2)
            
            # Process any unlinked news for this player
            await self.process_unlinked_news_for_player(player_id)
            
            return player_data
            
        except Exception as e:
            logger.error(f"Error creating manual player: {e}")
            raise

    async def process_unlinked_news_for_player(self, player_id: int) -> None:
        """Process all unlinked news items for a specific player"""
        try:
            # Get all unprocessed news
            unlinked_news = self._get_unlinked_news()
            
            for news_file in unlinked_news:
                try:
                    with open(news_file) as f:
                        news_data = json.load(f)
                    
                    # Get article content if needed
                    content = news_data.get('content', '')
                    if not content and news_data.get('url'):
                        content = await self._get_article_text(news_data['url'])
                        news_data['content'] = content
                    
                    # Check if news mentions this player
                    analysis = await self._analyze_with_gpt4(
                        f"""Does this transfer news mention or relate to the player with ID {player_id}?
                        
                        Title: {news_data['title']}
                        Content: {content[:1000]}
                        
                        Return ONLY a JSON object in this format:
                        {{
                            "is_relevant": true/false,
                            "confidence": 0-100
                        }}
                        """
                    )
                    
                    if analysis.get('is_relevant') and analysis.get('confidence', 0) > 50:
                        # Link news to player
                        await self.link_news_to_player(player_id, news_file.stem)
                        
                except Exception as e:
                    logger.error(f"Error processing news file {news_file.name} for player {player_id}: {e}")
                    continue
                
        except Exception as e:
            logger.error(f"Error processing unlinked news for player {player_id}: {e}")
            raise

    async def link_news_to_player(self, player_id: int, news_id: str) -> dict:
        """Manually link a news item to a player"""
        try:
            # Get player data
            player_file = self.data_dir / 'links' / f'player_{player_id}.json'
            if not player_file.exists():
                raise ValueError(f"Player {player_id} not found")
            
            with open(player_file) as f:
                player_data = json.load(f)
            
            # Get news data
            news_file = self.data_dir / 'news' / f'{news_id}.json'
            if not news_file.exists():
                raise ValueError(f"News item {news_id} not found")
            
            with open(news_file) as f:
                news_data = json.load(f)
            
            # Get article content if needed
            content = news_data.get('content', '')
            if not content and news_data.get('url'):
                content = await self._get_article_text(news_data['url'])
                news_data['content'] = content
            
            # Analyze news content
            analysis = await self._analyze_with_gpt4(
                self._get_llm_prompt(news_data['title'], content, player_data)
            )
            
            # Update player data with analysis
            updated_data = self._update_player_data(
                player_data,
                analysis,
                news_id
            )
            
            # Save updated player data
            with open(player_file, 'w') as f:
                json.dump(updated_data, f, indent=2)
            
            return updated_data
            
        except Exception as e:
            logger.error(f"Error linking news {news_id} to player {player_id}: {e}")
            raise

    def _get_unlinked_news(self) -> List[Path]:
        """Get list of news files that haven't been linked to any player"""
        processed_file = self.data_dir / 'processed_news.json'
        
        # Load processed IDs
        processed_ids = set()
        if processed_file.exists():
            try:
                with open(processed_file) as f:
                    processed_ids = set(json.load(f))
            except Exception as e:
                logger.error(f"Error loading processed news IDs: {e}")
        
        # Get all news files
        all_news = list(self.data_dir.glob('news/r-*.json'))
        
        # Filter for unlinked news
        return [
            f for f in all_news 
            if f.stem not in processed_ids
        ] 

    async def update_player_id(self, old_id: int, new_id: int) -> dict:
        """Update a player's ID and fetch new data if needed"""
        try:
            old_file = self.data_dir / 'links' / f'player_{old_id}.json'
            new_file = self.data_dir / 'links' / f'player_{new_id}.json'
            
            if not old_file.exists():
                raise ValueError(f"Player {old_id} not found")
            
            if new_file.exists():
                raise ValueError(f"Player {new_id} already exists")
            
            # Read existing data
            with open(old_file) as f:
                player_data = json.load(f)
            
            # Update player ID
            player_data['player_id'] = new_id
            
            # Save to new location
            with open(new_file, 'w') as f:
                json.dump(player_data, f, indent=2)
            
            # Delete old file
            old_file.unlink()
            
            # Fetch new stats
            await self._ensure_player_stats(new_id, player_data['canonical_name'])
            
            return player_data
            
        except Exception as e:
            logger.error(f"Error updating player ID: {e}")
            raise 