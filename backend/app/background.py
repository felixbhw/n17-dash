import asyncio
import logging
from typing import Optional
from .services.reddit_service import RedditService
from .services.llm_service import LLMService

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class BackgroundTasks:
    """Manages background tasks for the application"""
    
    def __init__(self, reddit_service: RedditService, llm_service: LLMService):
        """Initialize with service dependencies"""
        self.reddit_service = reddit_service
        self.llm_service = llm_service
        self.reddit_task: Optional[asyncio.Task] = None
        self.llm_task: Optional[asyncio.Task] = None
        logger.info("Background tasks manager initialized")
    
    async def start(self):
        """Start all background tasks"""
        # Start Reddit monitor first to ensure we have news to process
        self.reddit_task = asyncio.create_task(self.reddit_monitor())
        logger.info("Starting Reddit monitor")
        
        # Wait a short time to allow initial news fetch
        await asyncio.sleep(2)
        
        # Then start LLM processor
        self.llm_task = asyncio.create_task(self.news_processor())
        logger.info("Starting news processor")
        
        logger.info("All background tasks started")
    
    async def stop(self):
        """Stop all background tasks"""
        if self.reddit_task:
            self.reddit_task.cancel()
            logger.info("Cancelled reddit task")
        
        if self.llm_task:
            self.llm_task.cancel()
            logger.info("Cancelled llm task")
        
        logger.info("All background tasks stopped")
    
    async def reddit_monitor(self):
        """Monitor Reddit for new transfer posts"""
        while True:
            try:
                await self.reddit_service.check_new_posts()
                await asyncio.sleep(120)  # Check every 2 minutes
            except Exception as e:
                logger.error(f"Error in Reddit monitor: {e}")
                await asyncio.sleep(300)  # Wait longer after error
    
    async def news_processor(self):
        """Process pending news with LLM"""
        while True:
            try:
                await self.llm_service.process_pending_news()
                await asyncio.sleep(60)  # Process every minute
            except Exception as e:
                logger.error(f"Error in news processor: {e}")
                await asyncio.sleep(300)  # Wait longer after error

    async def reprocess_unlinked(self):
        """Reprocess all unlinked news items"""
        try:
            unlinked_news = self.llm_service._get_unlinked_news()
            
            for news_file in unlinked_news:
                try:
                    await self.llm_service.process_news_file(news_file)
                except Exception as e:
                    logger.error(f"Error processing news file {news_file.name}: {e}")
                    continue
                
            return True
        except Exception as e:
            logger.error(f"Error reprocessing unlinked news: {e}")
            return False

# Global instance
_instance: Optional[BackgroundTasks] = None

def get_background_tasks(
    reddit_service: Optional[RedditService] = None,
    llm_service: Optional[LLMService] = None
) -> BackgroundTasks:
    """Get or create the global background tasks instance"""
    global _instance
    if _instance is None:
        if not reddit_service or not llm_service:
            raise ValueError("Services must be provided for first initialization")
        _instance = BackgroundTasks(reddit_service, llm_service)
    return _instance 