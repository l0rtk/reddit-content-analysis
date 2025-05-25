from src.celery_app import celery_app
from .reddit_manager import RedditScrapingOrchestrator, RedditAPIManager
from .models import DatabaseManager, SubredditConfig
from datetime import datetime
import traceback

@celery_app.task(bind=True, name="scrape_all_subreddits")
def scrape_all_subreddits_task(self):
    """
    Celery task to scrape all active subreddits
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "Starting to scrape all active subreddits...",
                "current": 0,
                "total": 0
            }
        )
        
        # Get active subreddits count for progress tracking
        active_configs = DatabaseManager.get_active_subreddits()
        total_subreddits = len(active_configs)
        
        if total_subreddits == 0:
            return {
                "status": "No active subreddits found",
                "total_subreddits": 0,
                "results": {}
            }
        
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Found {total_subreddits} active subreddits to scrape",
                "current": 0,
                "total": total_subreddits
            }
        )
        
        # Define progress callback
        current_subreddit = [0]  # Use list to allow modification in nested function
        
        def progress_callback(current_post, total_posts, status):
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": f"Subreddit {current_subreddit[0]}/{total_subreddits}: {status}",
                    "current": current_subreddit[0],
                    "total": total_subreddits,
                    "post_progress": {
                        "current": current_post,
                        "total": total_posts
                    }
                }
            )
        
        # Scrape all subreddits
        results = {}
        for i, config in enumerate(active_configs, 1):
            current_subreddit[0] = i
            
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": f"Starting scrape for r/{config.name} ({i}/{total_subreddits})",
                    "current": i,
                    "total": total_subreddits
                }
            )
            
            try:
                api_manager = RedditAPIManager(config)
                posts = api_manager.scrape_subreddit_posts(
                    time_filter="day",
                    progress_callback=progress_callback
                )
                
                results[config.name] = {
                    "success": True,
                    "posts_scraped": len(posts),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                results[config.name] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        # Final state update
        successful_scrapes = sum(1 for r in results.values() if r.get("success", False))
        total_posts = sum(r.get("posts_scraped", 0) for r in results.values() if r.get("success", False))
        
        self.update_state(
            state="SUCCESS",
            meta={
                "status": f"Completed scraping {successful_scrapes}/{total_subreddits} subreddits",
                "current": total_subreddits,
                "total": total_subreddits,
                "total_posts_scraped": total_posts,
                "results": results
            }
        )
        
        return {
            "status": "Completed",
            "total_subreddits": total_subreddits,
            "successful_scrapes": successful_scrapes,
            "total_posts_scraped": total_posts,
            "results": results
        }
        
    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Error occurred: {str(exc)}",
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
        )
        raise exc

@celery_app.task(bind=True, name="scrape_specific_subreddit")
def scrape_specific_subreddit_task(self, subreddit_name: str, time_filter: str = "day", limit: int = None):
    """
    Celery task to scrape a specific subreddit
    
    Args:
        subreddit_name: Name of the subreddit to scrape
        time_filter: Time filter for posts (hour, day, week, month, year, all)
        limit: Number of posts to scrape
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Starting to scrape r/{subreddit_name}...",
                "current": 0,
                "total": limit or 100
            }
        )
        
        # Get subreddit configuration
        config = DatabaseManager.get_subreddit_config(subreddit_name)
        if not config:
            raise ValueError(f"No configuration found for subreddit: {subreddit_name}")
        
        if not config.active:
            raise ValueError(f"Subreddit {subreddit_name} is not active")
        
        # Define progress callback
        def progress_callback(current, total, status):
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": status,
                    "current": current,
                    "total": total
                }
            )
        
        # Scrape the subreddit
        api_manager = RedditAPIManager(config)
        posts = api_manager.scrape_subreddit_posts(time_filter, limit, progress_callback)
        
        # Final state update
        self.update_state(
            state="SUCCESS",
            meta={
                "status": f"Successfully scraped {len(posts)} posts from r/{subreddit_name}",
                "current": len(posts),
                "total": limit or len(posts),
                "posts_scraped": len(posts)
            }
        )
        
        return {
            "subreddit": subreddit_name,
            "time_filter": time_filter,
            "limit": limit,
            "posts_scraped": len(posts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Error scraping r/{subreddit_name}: {str(exc)}",
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
        )
        raise exc

@celery_app.task(bind=True, name="scrape_new_posts")
def scrape_new_posts_task(self, subreddit_name: str, limit: int = 50):
    """
    Celery task to scrape newest posts from a subreddit
    
    Args:
        subreddit_name: Name of the subreddit to scrape
        limit: Number of new posts to scrape
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Starting to scrape new posts from r/{subreddit_name}...",
                "current": 0,
                "total": limit
            }
        )
        
        # Get subreddit configuration
        config = DatabaseManager.get_subreddit_config(subreddit_name)
        if not config:
            raise ValueError(f"No configuration found for subreddit: {subreddit_name}")
        
        if not config.active:
            raise ValueError(f"Subreddit {subreddit_name} is not active")
        
        # Scrape new posts
        api_manager = RedditAPIManager(config)
        posts = api_manager.scrape_new_posts(limit)
        
        # Final state update
        self.update_state(
            state="SUCCESS",
            meta={
                "status": f"Successfully scraped {len(posts)} new posts from r/{subreddit_name}",
                "current": len(posts),
                "total": limit,
                "posts_scraped": len(posts)
            }
        )
        
        return {
            "subreddit": subreddit_name,
            "posts_scraped": len(posts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Error scraping new posts from r/{subreddit_name}: {str(exc)}",
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
        )
        raise exc

@celery_app.task(bind=True, name="setup_subreddit_config")
def setup_subreddit_config_task(self, subreddit_name: str, client_id: str, client_secret: str,
                                username: str, password: str, user_agent: str,
                                scraping_interval_hours: int = 24, max_posts_per_scrape: int = 100,
                                scrape_comments: bool = True, max_comments_per_post: int = 500):
    """
    Celery task to setup or update subreddit configuration
    
    Args:
        subreddit_name: Name of the subreddit
        client_id: Reddit API client ID
        client_secret: Reddit API client secret
        username: Reddit username
        password: Reddit password
        user_agent: Reddit API user agent
        scraping_interval_hours: Hours between scraping sessions
        max_posts_per_scrape: Maximum posts to scrape per session
        scrape_comments: Whether to scrape comments
        max_comments_per_post: Maximum comments per post
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Setting up configuration for r/{subreddit_name}...",
                "current": 1,
                "total": 3
            }
        )
        
        # Create configuration
        config = SubredditConfig(
            name=subreddit_name,
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
            scraping_interval_hours=scraping_interval_hours,
            max_posts_per_scrape=max_posts_per_scrape,
            scrape_comments=scrape_comments,
            max_comments_per_post=max_comments_per_post
        )
        
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Testing Reddit API connection for r/{subreddit_name}...",
                "current": 2,
                "total": 3
            }
        )
        
        # Test the configuration by creating an API manager
        try:
            api_manager = RedditAPIManager(config)
            # Test API connection
            api_manager.check_rate_limit()
        except Exception as e:
            raise ValueError(f"Failed to connect to Reddit API: {str(e)}")
        
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Saving configuration for r/{subreddit_name}...",
                "current": 3,
                "total": 3
            }
        )
        
        # Save configuration to database
        success = DatabaseManager.save_subreddit_config(config)
        if not success:
            raise ValueError("Failed to save configuration to database")
        
        self.update_state(
            state="SUCCESS",
            meta={
                "status": f"Successfully configured r/{subreddit_name}",
                "current": 3,
                "total": 3
            }
        )
        
        return {
            "subreddit": subreddit_name,
            "status": "Configuration saved successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Error configuring r/{subreddit_name}: {str(exc)}",
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
        )
        raise exc

@celery_app.task(bind=True, name="initialize_database")
def initialize_database_task(self):
    """
    Celery task to initialize database indexes
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "Creating database indexes...",
                "current": 1,
                "total": 1
            }
        )
        
        DatabaseManager.create_indexes()
        
        self.update_state(
            state="SUCCESS",
            meta={
                "status": "Database indexes created successfully",
                "current": 1,
                "total": 1
            }
        )
        
        return {
            "status": "Database initialized successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Error initializing database: {str(exc)}",
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
        )
        raise exc 