import praw
import json
import os
from datetime import datetime
from dotenv import load_dotenv

def test_reddit_fetch():
    """Test fetching recent and top posts from r/coys"""
    # Load environment variables
    load_dotenv()
    
    # Initialize Reddit instance
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent="n17-dash:v1.0.0 (testing)",
    )
    
    # Get subreddit
    subreddit = reddit.subreddit('coys')
    
    # Fetch posts
    posts = []
    
    print("Fetching new posts...")
    for post in subreddit.new(limit=25):
        post_data = {
            'id': post.id,
            'created_utc': datetime.utcfromtimestamp(post.created_utc).isoformat(),
            'title': post.title,
            'author': str(post.author),
            'url': post.url,
            'permalink': f"https://reddit.com{post.permalink}",
            'selftext': post.selftext,
            'score': post.score,
            'upvote_ratio': post.upvote_ratio,
            'num_comments': post.num_comments,
            'link_flair_text': post.link_flair_text,
            'is_self': post.is_self
        }
        posts.append(post_data)
    
    print("Fetching top posts from past day...")
    for post in subreddit.top('day', limit=25):
        post_data = {
            'id': post.id,
            'created_utc': datetime.utcfromtimestamp(post.created_utc).isoformat(),
            'title': post.title,
            'author': str(post.author),
            'url': post.url,
            'permalink': f"https://reddit.com{post.permalink}",
            'selftext': post.selftext,
            'score': post.score,
            'upvote_ratio': post.upvote_ratio,
            'num_comments': post.num_comments,
            'link_flair_text': post.link_flair_text,
            'is_self': post.is_self
        }
        # Avoid duplicates
        if not any(p['id'] == post_data['id'] for p in posts):
            posts.append(post_data)
    
    # Save to a test output file
    output_file = 'tests/reddit_sample.json'
    with open(output_file, 'w') as f:
        json.dump(posts, f, indent=2)
    
    print(f"\nSaved {len(posts)} unique posts to {output_file}")
    print("\nPosts with interesting flairs:")
    for post in posts:
        flair = post.get('link_flair_text', '')
        if any(keyword in flair.lower() for keyword in ['tier', 'rumour', 'news', 'transfer']):
            print(f"\nTitle: {post['title']}")
            print(f"Flair: {flair}")
            print(f"Score: {post['score']}")
            print(f"Comments: {post['num_comments']}")

if __name__ == "__main__":
    test_reddit_fetch() 