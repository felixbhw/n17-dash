import asyncio
from datetime import datetime
import logging
from typing import Optional
from .services import RedditService

logger = logging.getLogger(__name__)

class BackgroundTasks:
    def __init__(self):
        self.reddit_service = RedditService()
        self.reddit_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    async def reddit_monitor(self):
        """Background task to monitor Reddit"""
        while self.is_running:
            try:
                await self.reddit_service.check_new_posts()
                # Wait 2 minutes before checking again
                await asyncio.sleep(120)
            except Exception as e:
                logger.error(f"Error in Reddit monitor: {e}")
                # Wait longer if there's an error
                await asyncio.sleep(300)
    
    def start(self):
        """Start background tasks"""
        if not self.is_running:
            self.is_running = True
            self.reddit_task = asyncio.create_task(self.reddit_monitor())
            logger.info("Started Reddit monitoring task")
    
    def stop(self):
        """Stop background tasks"""
        if self.is_running:
            self.is_running = False
            if self.reddit_task:
                self.reddit_task.cancel()
            logger.info("Stopped Reddit monitoring task")

# Global instance
background_tasks = BackgroundTasks() 