import praw
import json
import os
from datetime import datetime
import time

def setup_reddit():
    """Initialize Reddit API connection"""
    return praw.Reddit(
        client_id="YOUR_CLIENT_ID",  # To be added to .env
        client_secret="YOUR_CLIENT_SECRET",  # To be added to .env
        user_agent="n17-dash:v1.0.0 (by /u/YOUR_USERNAME)",
        username="YOUR_USERNAME",  # Optional if just reading
        password="YOUR_PASSWORD"  # Optional if just reading
    )

def generate_news_id(source='r'):
    """Generate a unique news ID in the format r-YYYYMMDDHHmm-001"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M')
    
    # Check existing files to determine next sequence number
    news_dir = os.path.join('data', 'news')
    existing_files = [f for f in os.listdir(news_dir) 
                     if f.startswith(f'{source}-{timestamp}')]
    
    sequence = len(existing_files) + 1
    return f'{source}-{timestamp}-{sequence:03d}'

def save_post_as_news(post):
    """Convert a Reddit post to our news format and save it"""
    news_data = {
        "id": generate_news_id('r'),
        "source": "r",
        "timestamp": datetime.utcfromtimestamp(post.created_utc).isoformat(),
        "tier": 4,  # Default tier for Reddit posts, can be adjusted later
        "url": f"https://reddit.com{post.permalink}",
        "title": post.title,
        "content": post.selftext,
        "related_players": [],  # To be filled by AI analysis
        "related_clubs": [],    # To be filled by AI analysis
        "related_links": [],    # To be filled by AI analysis
        "sentiment": {
            "score": 0,
            "confidence": 0
        },
        "keywords": []  # To be filled by AI analysis
    }
    
    # Save to file
    filename = os.path.join('data', 'news', f"{news_data['id']}.json")
    with open(filename, 'w') as f:
        json.dump(news_data, f, indent=4)
    
    return news_data['id']

def monitor_subreddit():
    """Monitor r/coys for new posts"""
    reddit = setup_reddit()
    subreddit = reddit.subreddit('coys')
    
    # Keep track of processed posts to avoid duplicates
    processed_posts = set()
    
    print("Starting to monitor r/coys...")
    
    while True:
        try:
            # Get new posts
            for post in subreddit.new(limit=10):
                if post.id not in processed_posts:
                    print(f"New post found: {post.title}")
                    news_id = save_post_as_news(post)
                    processed_posts.add(post.id)
                    print(f"Saved as {news_id}")
            
            # Sleep to respect rate limits (1 request per 2 seconds)
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(60)  # Wait longer if there's an error

if __name__ == "__main__":
    monitor_subreddit() 