#!/usr/bin/env python3
"""
Reddit Scraping System Setup Example

This script demonstrates how to set up and configure the Reddit scraping system.
"""

import os
from dotenv import load_dotenv
from .management import RedditScrapingManager
from .models import DatabaseManager

def setup_example_subreddits():
    """
    Example setup for multiple subreddits with different API credentials
    
    This demonstrates how to configure multiple subreddits, each with their own
    Reddit API credentials to avoid rate limit conflicts.
    """
    
    print("🚀 Setting up Reddit Scraping System")
    print("=" * 50)
    
    # Initialize the system
    print("\n1. Initializing database...")
    manager = RedditScrapingManager()
    if not manager.initialize_system():
        print("❌ Failed to initialize system")
        return False
    
    # Example subreddit configurations
    # In practice, you would have different API credentials for each subreddit
    subreddit_configs = [
        {
            "name": "programming",
            "client_id": os.getenv("R_CLIENT_ID_1", "your_client_id_1"),
            "client_secret": os.getenv("R_CLIENT_SECRET_1", "your_client_secret_1"),
            "username": os.getenv("R_USERNAME_1", "your_username_1"),
            "password": os.getenv("R_PASSWORD_1", "your_password_1"),
            "user_agent": os.getenv("R_USER_AGENT_1", "RedditScraper:v1.0 (by /u/your_username_1)"),
            "scraping_interval_hours": 12,
            "max_posts_per_scrape": 50,
            "scrape_comments": True,
            "max_comments_per_post": 200
        },
        {
            "name": "MachineLearning",
            "client_id": os.getenv("R_CLIENT_ID_2", "your_client_id_2"),
            "client_secret": os.getenv("R_CLIENT_SECRET_2", "your_client_secret_2"),
            "username": os.getenv("R_USERNAME_2", "your_username_2"),
            "password": os.getenv("R_PASSWORD_2", "your_password_2"),
            "user_agent": os.getenv("R_USER_AGENT_2", "RedditScraper:v1.0 (by /u/your_username_2)"),
            "scraping_interval_hours": 8,
            "max_posts_per_scrape": 75,
            "scrape_comments": True,
            "max_comments_per_post": 300
        },
        {
            "name": "technology",
            "client_id": os.getenv("R_CLIENT_ID_3", "your_client_id_3"),
            "client_secret": os.getenv("R_CLIENT_SECRET_3", "your_client_secret_3"),
            "username": os.getenv("R_USERNAME_3", "your_username_3"),
            "password": os.getenv("R_PASSWORD_3", "your_password_3"),
            "user_agent": os.getenv("R_USER_AGENT_3", "RedditScraper:v1.0 (by /u/your_username_3)"),
            "scraping_interval_hours": 6,
            "max_posts_per_scrape": 100,
            "scrape_comments": True,
            "max_comments_per_post": 500
        }
    ]
    
    print(f"\n2. Adding {len(subreddit_configs)} subreddit configurations...")
    
    successful_configs = 0
    for config in subreddit_configs:
        print(f"\n   Setting up r/{config['name']}...")
        
        # Check if credentials are provided
        if config['client_id'].startswith('your_'):
            print(f"   ⚠️  Skipping r/{config['name']} - no credentials provided")
            print(f"      Please set environment variables for this subreddit:")
            print(f"      R_CLIENT_ID_{config['name'].upper()}")
            print(f"      R_CLIENT_SECRET_{config['name'].upper()}")
            print(f"      R_USERNAME_{config['name'].upper()}")
            print(f"      R_PASSWORD_{config['name'].upper()}")
            print(f"      R_USER_AGENT_{config['name'].upper()}")
            continue
        
        success = manager.add_subreddit(**config)
        if success:
            successful_configs += 1
            print(f"   ✅ Successfully configured r/{config['name']}")
        else:
            print(f"   ❌ Failed to configure r/{config['name']}")
    
    print(f"\n3. Configuration Summary:")
    print(f"   Successfully configured: {successful_configs}/{len(subreddit_configs)} subreddits")
    
    if successful_configs > 0:
        print(f"\n4. Testing initial scrape...")
        # Test scrape one subreddit
        first_config = next((c for c in subreddit_configs if not c['client_id'].startswith('your_')), None)
        if first_config:
            print(f"   Testing scrape for r/{first_config['name']}...")
            success = manager.scrape_subreddit(first_config['name'], "day", 5)
            if success:
                print(f"   ✅ Test scrape successful!")
            else:
                print(f"   ❌ Test scrape failed")
    
    return successful_configs > 0

def create_env_template():
    """Create a template .env file with all necessary environment variables"""
    
    env_template = """# Reddit API Credentials for Multiple Subreddits
# Each subreddit should have its own set of credentials to avoid rate limit conflicts

# MongoDB Connection
MONGODB_URI=mongodb://localhost:27017/

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Reddit API Credentials Set 1 (for r/programming)
R_CLIENT_ID_1=your_reddit_client_id_1
R_CLIENT_SECRET_1=your_reddit_client_secret_1
R_USERNAME_1=your_reddit_username_1
R_PASSWORD_1=your_reddit_password_1
R_USER_AGENT_1=RedditScraper:v1.0 (by /u/your_reddit_username_1)

# Reddit API Credentials Set 2 (for r/MachineLearning)
R_CLIENT_ID_2=your_reddit_client_id_2
R_CLIENT_SECRET_2=your_reddit_client_secret_2
R_USERNAME_2=your_reddit_username_2
R_PASSWORD_2=your_reddit_password_2
R_USER_AGENT_2=RedditScraper:v1.0 (by /u/your_reddit_username_2)

# Reddit API Credentials Set 3 (for r/technology)
R_CLIENT_ID_3=your_reddit_client_id_3
R_CLIENT_SECRET_3=your_reddit_client_secret_3
R_USERNAME_3=your_reddit_username_3
R_PASSWORD_3=your_reddit_password_3
R_USER_AGENT_3=RedditScraper:v1.0 (by /u/your_reddit_username_3)

# Add more credential sets as needed for additional subreddits
# R_CLIENT_ID_4=...
# R_CLIENT_SECRET_4=...
# etc.
"""
    
    env_file_path = ".env.template"
    
    try:
        with open(env_file_path, 'w') as f:
            f.write(env_template)
        print(f"✅ Created environment template: {env_file_path}")
        print("   Please copy this to .env and fill in your Reddit API credentials")
        return True
    except Exception as e:
        print(f"❌ Failed to create environment template: {e}")
        return False

def show_usage_examples():
    """Show usage examples for the Reddit scraping system"""
    
    print("\n" + "=" * 60)
    print("📚 USAGE EXAMPLES")
    print("=" * 60)
    
    print("\n1. Management Commands:")
    print("   python -m src.reddit.management init")
    print("   python -m src.reddit.management list")
    print("   python -m src.reddit.management scrape programming")
    print("   python -m src.reddit.management scrape-all")
    print("   python -m src.reddit.management stats")
    
    print("\n2. Scheduler Commands:")
    print("   python -m src.reddit.scheduler")
    print("   python -m src.reddit.scheduler daemon")
    
    print("\n3. Celery Commands:")
    print("   # Start Celery worker")
    print("   celery -A src.celery_app worker --loglevel=info")
    print("   ")
    print("   # Start Celery beat (for scheduled tasks)")
    print("   celery -A src.celery_app beat --loglevel=info")
    print("   ")
    print("   # Monitor Celery tasks")
    print("   celery -A src.celery_app flower")
    
    print("\n4. Python API Examples:")
    print("""
   from src.reddit.management import RedditScrapingManager
   from src.reddit.models import DatabaseManager
   
   # Initialize system
   manager = RedditScrapingManager()
   manager.initialize_system()
   
   # Add subreddit
   manager.add_subreddit(
       name="programming",
       client_id="your_client_id",
       client_secret="your_client_secret",
       username="your_username",
       password="your_password",
       user_agent="your_user_agent"
   )
   
   # Scrape subreddit
   manager.scrape_subreddit("programming", "day", 50)
   
   # Get statistics
   stats = manager.get_stats()
   print(stats)
   
   # Get comment tree for a post
   tree = manager.get_comment_tree("post_id_here")
   """)
    
    print("\n5. Database Collections:")
    print("   - subreddits: Subreddit configurations with API credentials")
    print("   - posts: Reddit posts (without comments)")
    print("   - comments: Reddit comments with parent-child relationships")
    print("   - rate_limits: Rate limit tracking for each API credential set")

def main():
    """Main setup function"""
    load_dotenv()
    
    print("Reddit Scraping System Setup")
    print("=" * 40)
    print("1. Create environment template")
    print("2. Setup example subreddits")
    print("3. Show usage examples")
    print("4. All of the above")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice in ["1", "4"]:
        print("\n📝 Creating environment template...")
        create_env_template()
    
    if choice in ["2", "4"]:
        print("\n⚙️  Setting up example subreddits...")
        setup_example_subreddits()
    
    if choice in ["3", "4"]:
        show_usage_examples()
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Fill in your Reddit API credentials in .env")
    print("2. Start MongoDB and Redis services")
    print("3. Run: python -m src.reddit.management init")
    print("4. Add your subreddit configurations")
    print("5. Start scraping!")

if __name__ == "__main__":
    main() 