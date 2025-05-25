# Reddit Content Analysis - Advanced Scraping System

A comprehensive Reddit scraping system designed for continuous data collection with proper rate limiting, multiple API credentials, and hierarchical data organization.

## 🏗️ Architecture Overview

### Database Collections

1. **`subreddits`** - Subreddit configurations with unique API credentials
2. **`posts`** - Reddit posts (without comments for better performance)
3. **`comments`** - Comments with parent-child relationships for tree reconstruction
4. **`rate_limits`** - Rate limit tracking per API credential set

### Key Features

- ✅ **Multiple API Credentials**: Each subreddit uses unique Reddit API keys to avoid rate limit conflicts
- ✅ **Hierarchical Comments**: Comments stored with parent-child relationships for tree reconstruction
- ✅ **Rate Limit Management**: Intelligent rate limiting with automatic waiting
- ✅ **Continuous Scraping**: Scheduled scraping with configurable intervals
- ✅ **Celery Integration**: Asynchronous task processing with progress tracking
- ✅ **Comprehensive Data**: Full post and comment metadata extraction
- ✅ **MongoDB Optimization**: Proper indexing for fast queries

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install praw pymongo celery redis schedule python-dotenv
```

### 2. Setup Environment

```bash
# Run the setup script
python -m src.reddit.setup_example

# This creates .env.template - copy to .env and fill in your credentials
cp .env.template .env
```

### 3. Configure Reddit API Credentials

Edit `.env` with your Reddit API credentials:

```env
# MongoDB Connection
MONGODB_URI=mongodb://localhost:27017/

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Reddit API Credentials Set 1
R_CLIENT_ID_1=your_reddit_client_id_1
R_CLIENT_SECRET_1=your_reddit_client_secret_1
R_USERNAME_1=your_reddit_username_1
R_PASSWORD_1=your_reddit_password_1
R_USER_AGENT_1=RedditScraper:v1.0 (by /u/your_reddit_username_1)

# Add more credential sets for additional subreddits...
```

### 4. Initialize System

```bash
python -m src.reddit.management init
```

### 5. Add Subreddit Configurations

```python
from src.reddit.management import RedditScrapingManager

manager = RedditScrapingManager()

# Add a subreddit with its own API credentials
manager.add_subreddit(
    name="programming",
    client_id="your_client_id",
    client_secret="your_client_secret",
    username="your_username",
    password="your_password",
    user_agent="RedditScraper:v1.0 (by /u/your_username)",
    scraping_interval_hours=12,
    max_posts_per_scrape=100,
    scrape_comments=True,
    max_comments_per_post=500
)
```

## 📋 Management Commands

### Basic Operations

```bash
# Initialize the system
python -m src.reddit.management init

# List all configured subreddits
python -m src.reddit.management list

# Scrape a specific subreddit
python -m src.reddit.management scrape programming

# Scrape all active subreddits
python -m src.reddit.management scrape-all

# Get system statistics
python -m src.reddit.management stats

# Activate/deactivate subreddits
python -m src.reddit.management activate programming
python -m src.reddit.management deactivate programming
```

## ⏰ Continuous Scraping

### Using the Scheduler

```bash
# Interactive scheduler
python -m src.reddit.scheduler

# Run as daemon (continuous background process)
python -m src.reddit.scheduler daemon
```

### Using Celery (Recommended for Production)

```bash
# Terminal 1: Start Celery worker
celery -A src.celery_app worker --loglevel=info

# Terminal 2: Start Celery beat (for scheduled tasks)
celery -A src.celery_app beat --loglevel=info

# Terminal 3: Monitor with Flower (optional)
celery -A src.celery_app flower
```

## 🔧 Python API Usage

### Basic Scraping

```python
from src.reddit.management import RedditScrapingManager
from src.reddit.models import DatabaseManager

# Initialize
manager = RedditScrapingManager()

# Scrape specific subreddit
posts = manager.scrape_subreddit("programming", "day", 50)

# Scrape all active subreddits
results = manager.scrape_all_subreddits()

# Get statistics
stats = manager.get_stats()
print(f"Total posts: {stats['total_posts']:,}")
print(f"Total comments: {stats['total_comments']:,}")
```

### Working with Comments

```python
from src.reddit.models import DatabaseManager

# Get hierarchical comment tree for a post
tree = DatabaseManager.get_comment_tree("post_id_here")

print(f"Total comments: {tree['total_comments']}")
print(f"Root comments: {len(tree['root_comments'])}")

# Each comment in the tree has a 'children' list for nested replies
for comment in tree['root_comments']:
    print(f"Comment: {comment['body'][:100]}...")
    print(f"Replies: {len(comment['children'])}")
```

### Advanced Configuration

```python
from src.reddit.models import SubredditConfig, DatabaseManager

# Create detailed configuration
config = SubredditConfig(
    name="MachineLearning",
    client_id="your_client_id",
    client_secret="your_client_secret",
    username="your_username",
    password="your_password",
    user_agent="your_user_agent",
    scraping_interval_hours=8,
    max_posts_per_scrape=75,
    scrape_comments=True,
    max_comments_per_post=300
)

# Save configuration
DatabaseManager.save_subreddit_config(config)
```

## 📊 Data Schema

### Posts Collection

```javascript
{
  "_id": ObjectId,
  "id": "reddit_post_id",
  "subreddit": "programming",
  "title": "Post title",
  "body": "Post content",
  "score": 1234,
  "upvote_ratio": 0.95,
  "num_comments": 56,
  "created_utc": 1640995200.0,
  "url": "https://...",
  "author": "username",
  "permalink": "/r/programming/comments/...",
  "is_self": true,
  "is_video": false,
  "over_18": false,
  "spoiler": false,
  "stickied": false,
  "locked": false,
  "archived": false,
  "gilded": 2,
  "distinguished": null,
  "link_flair_text": "Discussion",
  "scraped_at": ISODate("2024-01-01T12:00:00Z")
}
```

### Comments Collection

```javascript
{
  "_id": ObjectId,
  "id": "reddit_comment_id",
  "post_id": "reddit_post_id",
  "subreddit": "programming",
  "parent_id": "parent_comment_id", // null for top-level comments
  "body": "Comment text",
  "author": "username",
  "score": 42,
  "created_utc": 1640995800.0,
  "edited": false,
  "is_submitter": false,
  "stickied": false,
  "gilded": 0,
  "distinguished": null,
  "depth": 1, // nesting level (0 = top-level)
  "permalink": "/r/programming/comments/.../comment_id/",
  "scraped_at": ISODate("2024-01-01T12:00:00Z")
}
```

### Subreddits Collection

```javascript
{
  "_id": ObjectId,
  "name": "programming",
  "client_id": "reddit_client_id",
  "client_secret": "reddit_client_secret",
  "username": "reddit_username",
  "password": "reddit_password",
  "user_agent": "RedditScraper:v1.0",
  "active": true,
  "created_at": ISODate("2024-01-01T10:00:00Z"),
  "updated_at": ISODate("2024-01-01T12:00:00Z"),
  "last_scraped": ISODate("2024-01-01T11:30:00Z"),
  "scraping_interval_hours": 12,
  "max_posts_per_scrape": 100,
  "scrape_comments": true,
  "max_comments_per_post": 500
}
```

## 🔄 Rate Limiting Strategy

### Multiple API Credentials

Each subreddit uses its own Reddit API credentials to avoid rate limit conflicts:

```python
# Different credentials for each subreddit
subreddit_configs = {
    "programming": {
        "client_id": "credentials_set_1",
        # ... other credentials
    },
    "MachineLearning": {
        "client_id": "credentials_set_2",
        # ... other credentials
    },
    "technology": {
        "client_id": "credentials_set_3",
        # ... other credentials
    }
}
```

### Intelligent Rate Limiting

- Automatic rate limit checking before each API call
- Waits for rate limit reset when necessary
- Tracks rate limits per credential set in database
- Configurable minimum remaining requests threshold

## 📈 Monitoring and Analytics

### System Statistics

```python
from src.reddit.management import RedditScrapingManager

manager = RedditScrapingManager()
stats = manager.get_stats()

print(f"""
System Statistics:
- Configured subreddits: {stats['subreddits']}
- Active subreddits: {stats['active_subreddits']}
- Total posts: {stats['total_posts']:,}
- Total comments: {stats['total_comments']:,}
- Posts today: {stats['posts_today']:,}
- Comments today: {stats['comments_today']:,}
""")
```

### Scheduler Statistics

```python
from src.reddit.scheduler import RedditScrapingScheduler

scheduler = RedditScrapingScheduler()
stats = scheduler.get_stats()

print(f"""
Scheduler Statistics:
- Total runs: {stats['total_runs']}
- Successful runs: {stats['successful_runs']}
- Failed runs: {stats['failed_runs']}
- Last run: {stats['last_run']}
- Next run: {stats['next_run']}
""")
```

## 🛠️ Advanced Features

### Custom Scraping Intervals

Each subreddit can have its own scraping interval:

```python
# High-activity subreddit - scrape every 4 hours
config1 = SubredditConfig(
    name="technology",
    scraping_interval_hours=4,
    # ... other config
)

# Low-activity subreddit - scrape daily
config2 = SubredditConfig(
    name="programming",
    scraping_interval_hours=24,
    # ... other config
)
```

### Comment Tree Reconstruction

```python
# Get complete comment tree with nested structure
tree = DatabaseManager.get_comment_tree("post_id")

def print_comment_tree(comments, indent=0):
    for comment in comments:
        print("  " * indent + f"- {comment['author']}: {comment['body'][:50]}...")
        if comment['children']:
            print_comment_tree(comment['children'], indent + 1)

print_comment_tree(tree['root_comments'])
```

### Celery Task Monitoring

```python
from src.reddit.new_tasks import scrape_all_subreddits_task

# Start async task
task = scrape_all_subreddits_task.delay()

# Monitor progress
while not task.ready():
    result = task.result
    if result and 'status' in result:
        print(f"Status: {result['status']}")
    time.sleep(5)

# Get final result
final_result = task.get()
print(f"Scraping completed: {final_result}")
```

## 🔧 Troubleshooting

### Common Issues

1. **Rate Limit Errors**: Ensure each subreddit has unique API credentials
2. **MongoDB Connection**: Check `MONGODB_URI` in `.env`
3. **Redis Connection**: Ensure Redis is running for Celery
4. **API Credentials**: Verify Reddit API credentials are correct

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check rate limits manually
from src.reddit.reddit_manager import RedditAPIManager
from src.reddit.models import DatabaseManager

config = DatabaseManager.get_subreddit_config("programming")
api_manager = RedditAPIManager(config)
rate_limit = api_manager.check_rate_limit()
print(f"Rate limit: {rate_limit}")
```

## 📝 Best Practices

1. **Use Multiple API Credentials**: One set per subreddit to avoid conflicts
2. **Monitor Rate Limits**: Keep track of API usage across all credentials
3. **Reasonable Intervals**: Don't scrape too frequently (respect Reddit's resources)
4. **Error Handling**: Monitor logs for failed scraping attempts
5. **Database Maintenance**: Regularly check database size and performance
6. **Backup Data**: Regular backups of your MongoDB collections

## 🚀 Production Deployment

### Docker Setup (Recommended)

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run scheduler daemon
CMD ["python", "-m", "src.reddit.scheduler", "daemon"]
```

### Systemd Service

```ini
# /etc/systemd/system/reddit-scraper.service
[Unit]
Description=Reddit Scraper Daemon
After=network.target

[Service]
Type=simple
User=reddit-scraper
WorkingDirectory=/path/to/reddit-content-analysis
ExecStart=/usr/bin/python3 -m src.reddit.scheduler daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

### Monitoring

- Use Flower for Celery task monitoring
- Set up log rotation for scraper logs
- Monitor MongoDB performance and disk usage
- Set up alerts for failed scraping tasks

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub with detailed information
