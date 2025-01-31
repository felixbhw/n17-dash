import asyncpraw
import json
import os
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from dotenv import load_dotenv

# Get the project root directory and load .env from there
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_PATH = PROJECT_ROOT / '.env'
load_dotenv(ENV_PATH)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class RedditService:
    def __init__(self):
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        
        logger.debug(f"Project root: {PROJECT_ROOT}")
        logger.debug(f".env path: {ENV_PATH}")
        logger.debug(f"Initializing Reddit service with client_id present: {client_id is not None}")
        logger.debug(f"Initializing Reddit service with client_secret present: {client_secret is not None}")
        
        if not client_id or not client_secret:
            logger.error("Missing Reddit API credentials in environment")
            raise ValueError("Missing Reddit API credentials. Please check your .env file.")
        
        self.reddit = asyncpraw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="n17-dash:v1.0.0",
        )
        self.data_dir = PROJECT_ROOT / 'backend' / 'data'
        self.processed_posts = self._load_processed_posts()
        
        # Ensure directories exist
        (self.data_dir / 'news').mkdir(parents=True, exist_ok=True)
        
        # Tier mappings (r/coys flair -> our system)
        self.tier_mappings = {
            'Transfer News: Tier 1': 1,
            'Transfer News: Tier 2': 2,
            'Transfer News: Tier 3': 3,
            'Tier: Here We Go!': 1,
            'Transfer: News': 4,
            'Transfer News': 4
        }
        
        logger.info(f"RedditService initialized with data directory: {self.data_dir}")
    
    def _load_processed_posts(self) -> Dict[str, dict]:
        """Load previously processed posts from news files"""
        processed = {}
        news_dir = self.data_dir / 'news'
        if news_dir.exists():
            for file in news_dir.glob('r-*.json'):
                try:
                    with open(file) as f:
                        data = json.load(f)
                        processed[data['reddit_id']] = {
                            'news_id': data['id'],
                            'tier': data['tier']
                        }
                except Exception as e:
                    logger.error(f"Error loading processed post from {file}: {e}")
        
        logger.info(f"Loaded {len(processed)} previously processed posts")
        return processed
    
    def _get_tier_from_flair(self, flair: str) -> Optional[int]:
        """Convert r/coys flair to our tier system"""
        return self.tier_mappings.get(flair)
    
    def _create_news_file(self, post, tier: int) -> str:
        """Create a news file for a post"""
        news_id = f"r-{datetime.utcnow().strftime('%Y%m%d%H%M')}-{len(self.processed_posts) % 999 + 1:03d}"
        
        news_data = {
            "id": news_id,
            "reddit_id": post.id,
            "source": "r",
            "timestamp": datetime.utcfromtimestamp(post.created_utc).isoformat(),
            "tier": tier,
            "url": f"https://reddit.com{post.permalink}",
            "title": post.title,
            "content": post.selftext,
            "related_players": [],  # Will be filled by LLM
            "related_clubs": [],    # Will be filled by LLM
            "related_links": [],    # Will be filled by LLM
            "sentiment": {          # Will be filled by LLM
                "score": 0,
                "confidence": 0
            },
            "keywords": []          # Will be filled by LLM
        }
        
        filepath = self.data_dir / 'news' / f"{news_id}.json"
        logger.debug(f"Creating news file at: {filepath}")
        with open(filepath, 'w') as f:
            json.dump(news_data, f, indent=2)
        
        logger.info(f"Created news file {news_id} for post {post.id}")
        return news_id
    
    async def process_transfer_post(self, post) -> Tuple[Optional[str], bool]:
        """Process a transfer-related post
        Returns: (news_id, is_new_post)"""
        flair = post.link_flair_text or ""
        tier = self._get_tier_from_flair(flair)
        
        if tier is None:
            return None, False
            
        # Check if we've seen this post before
        if post.id in self.processed_posts:
            existing = self.processed_posts[post.id]
            # Only update if new tier is better (lower number)
            if tier < existing['tier']:
                logger.info(f"Upgrading tier for post {post.id} from {existing['tier']} to {tier}")
                news_file = self.data_dir / 'news' / f"{existing['news_id']}.json"
                with open(news_file) as f:
                    news_data = json.load(f)
                news_data['tier'] = tier
                with open(news_file, 'w') as f:
                    json.dump(news_data, f, indent=2)
                return existing['news_id'], False
            return None, False
        
        # Create new news file
        news_id = self._create_news_file(post, tier)
        
        # Update processed posts
        self.processed_posts[post.id] = {
            'news_id': news_id,
            'tier': tier
        }
        
        return news_id, True
    
    async def check_new_posts(self):
        """Check for new transfer-related posts"""
        try:
            new_posts = 0
            updated_posts = 0
            
            subreddit = await self.reddit.subreddit('coys')
            async for post in subreddit.new(limit=25):
                news_id, is_new = await self.process_transfer_post(post)
                if news_id:
                    if is_new:
                        new_posts += 1
                    else:
                        updated_posts += 1
            
            if new_posts or updated_posts:
                logger.info(f"Processed {new_posts} new posts, updated {updated_posts} existing posts")
                
        except Exception as e:
            logger.error(f"Error checking new posts: {e}")
    
    async def fetch_historical(self, days: int = 7) -> Dict[str, int]:
        """Fetch historical transfer posts from the past X days
        Returns: Stats about processed posts"""
        logger.info(f"Starting historical fetch for past {days} days")
        stats = {
            "processed": 0,
            "new_posts": 0,
            "updated_posts": 0,
            "skipped": 0
        }
        
        # Calculate cutoff time
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            subreddit = await self.reddit.subreddit('coys')
            
            # First try top posts of the week
            async for post in subreddit.top('week', limit=100):
                stats["processed"] += 1
                
                # Skip if too old
                if datetime.utcfromtimestamp(post.created_utc) < cutoff:
                    stats["skipped"] += 1
                    continue
                
                news_id, is_new = await self.process_transfer_post(post)
                if news_id:
                    if is_new:
                        stats["new_posts"] += 1
                    else:
                        stats["updated_posts"] += 1
            
            # Then try controversial posts to catch anything missed
            async for post in subreddit.controversial('week', limit=100):
                stats["processed"] += 1
                
                # Skip if too old
                if datetime.utcfromtimestamp(post.created_utc) < cutoff:
                    stats["skipped"] += 1
                    continue
                
                news_id, is_new = await self.process_transfer_post(post)
                if news_id:
                    if is_new:
                        stats["new_posts"] += 1
                    else:
                        stats["updated_posts"] += 1
            
            logger.info(f"Historical fetch complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during historical fetch: {e}")
            return stats 