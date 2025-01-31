import asyncpraw
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import logging
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / '.env')

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class RedditService:
    """Service for collecting transfer news from r/coys subreddit"""
    
    # Map r/coys flairs to our tier system
    TIER_MAPPINGS = {
        'Transfer News: Tier 1': 1,
        'Transfer News: Tier 2': 2,
        'Transfer News: Tier 3': 3,
        'Tier: Here We Go!': 1,
        'Transfer: News': 4,
        'Transfer News': 4
    }
    
    def __init__(self):
        """Initialize Reddit API client"""
        # Get Reddit API credentials
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("Missing Reddit API credentials in .env file")
        
        # Initialize Reddit client
        self.reddit = asyncpraw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="n17-dash:v1.0.0"
        )
        
        # Set up data directory
        self.data_dir = PROJECT_ROOT / 'backend' / 'data' / 'news'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Reddit service initialized successfully")
    
    def _get_tier(self, flair: str) -> Optional[int]:
        """Convert Reddit flair to our tier system"""
        return self.TIER_MAPPINGS.get(flair or "")
    
    def _save_news(self, post_id: str, title: str, url: str, flair: str) -> bool:
        """Save news to a JSON file if it doesn't already exist"""
        # Generate filename based on timestamp and post ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        filename = f"r-{timestamp}-{post_id}.json"
        filepath = self.data_dir / filename
        
        # Check if we already have this post ID in any existing file
        existing_files = list(self.data_dir.glob('r-*-*.json'))
        for existing in existing_files:
            if post_id in existing.name:
                return False
        
        # Clean and normalize the title
        clean_title = title.encode('utf-8').decode('utf-8')
        
        # Save new file
        news_data = {
            "id": f"r-{timestamp}-{post_id}",
            "source": "reddit",
            "reddit_id": post_id,
            "timestamp": datetime.now().isoformat(),
            "title": clean_title,
            "content": "",  # Will be fetched by LLM service
            "url": url,
            "tier": self._get_tier(flair),
            "metadata": {
                "flair": flair,
                "saved_at": datetime.now().isoformat()
            }
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(news_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved: {clean_title[:60]}...")
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False
    
    async def check_new_posts(self):
        """Check r/coys for new transfer posts"""
        try:
            new_posts = 0
            subreddit = await self.reddit.subreddit('coys')
            
            # Check latest posts
            async for post in subreddit.new(limit=25):
                # Skip if not transfer related
                if not self._get_tier(post.link_flair_text):
                    continue
                
                # Save as news file
                if self._save_news(post.id, post.title, post.url, post.link_flair_text):
                    new_posts += 1
            
            if new_posts:
                logger.info(f"Added {new_posts} new transfer posts")
                
        except Exception as e:
            logger.error(f"Reddit check failed: {e}")
    
    async def fetch_historical(self, days: int = 7) -> Dict[str, int]:
        """Fetch historical transfer posts"""
        stats = {"processed": 0, "saved": 0, "skipped": 0, "errors": 0}
        cutoff = datetime.utcnow() - timedelta(days=days)
        seen_posts = set()
        
        try:
            subreddit = await self.reddit.subreddit('coys')
            
            # Helper to process posts
            async def process_posts(posts_iterator):
                async for post in posts_iterator:
                    stats['processed'] += 1
                    
                    try:
                        # Skip if already seen
                        if post.id in seen_posts:
                            stats['skipped'] += 1
                            continue
                        seen_posts.add(post.id)
                        
                        # Skip old posts
                        post_time = datetime.utcfromtimestamp(post.created_utc)
                        if post_time < cutoff:
                            stats['skipped'] += 1
                            continue
                        
                        # Save if transfer related
                        if self._get_tier(post.link_flair_text):
                            if self._save_news(post.id, post.title, post.url, post.link_flair_text):
                                stats['saved'] += 1
                            else:
                                stats['skipped'] += 1
                                
                    except Exception as e:
                        logger.error(f"Post processing failed: {e}")
                        stats['errors'] += 1
            
            # Process posts from different sort methods
            for sort_method in ['new', 'top', 'hot', 'controversial']:
                await process_posts(getattr(subreddit, sort_method)(limit=100))
            
            logger.info(f"Historical fetch: {stats['saved']} saved, {stats['skipped']} skipped")
            return stats
            
        except Exception as e:
            logger.error(f"Historical fetch failed: {e}")
            stats['errors'] += 1
            return stats 