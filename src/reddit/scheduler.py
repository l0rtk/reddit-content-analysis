#!/usr/bin/env python3
"""
Reddit Scraping Scheduler

This module provides scheduling functionality for continuous Reddit scraping.
"""

import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any
from .models import DatabaseManager
from .reddit_manager import RedditScrapingOrchestrator
from .new_tasks import scrape_all_subreddits_task, scrape_specific_subreddit_task
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddit_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedditScrapingScheduler:
    """Scheduler for continuous Reddit scraping operations"""
    
    def __init__(self, use_celery: bool = True):
        """
        Initialize the scheduler
        
        Args:
            use_celery: Whether to use Celery for task execution (recommended for production)
        """
        self.use_celery = use_celery
        self.running = False
        self.stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "last_run": None,
            "next_run": None
        }
    
    def schedule_continuous_scraping(self, interval_hours: int = 6):
        """
        Schedule continuous scraping of all active subreddits
        
        Args:
            interval_hours: Hours between scraping runs
        """
        logger.info(f"Scheduling continuous scraping every {interval_hours} hours")
        
        # Schedule the job
        schedule.every(interval_hours).hours.do(self._run_scheduled_scraping)
        
        # Update next run time
        self.stats["next_run"] = datetime.now() + timedelta(hours=interval_hours)
        
        logger.info(f"Next scraping run scheduled for: {self.stats['next_run']}")
    
    def schedule_subreddit_specific(self, subreddit_name: str, interval_hours: int = 24):
        """
        Schedule scraping for a specific subreddit
        
        Args:
            subreddit_name: Name of the subreddit to scrape
            interval_hours: Hours between scraping runs
        """
        logger.info(f"Scheduling r/{subreddit_name} scraping every {interval_hours} hours")
        
        def scrape_specific():
            self._run_subreddit_scraping(subreddit_name)
        
        schedule.every(interval_hours).hours.do(scrape_specific)
    
    def schedule_new_posts_monitoring(self, interval_minutes: int = 30):
        """
        Schedule frequent monitoring for new posts across all subreddits
        
        Args:
            interval_minutes: Minutes between new post checks
        """
        logger.info(f"Scheduling new posts monitoring every {interval_minutes} minutes")
        
        schedule.every(interval_minutes).minutes.do(self._run_new_posts_monitoring)
    
    def _run_scheduled_scraping(self):
        """Execute scheduled scraping of all active subreddits"""
        logger.info("Starting scheduled scraping of all active subreddits")
        
        self.stats["total_runs"] += 1
        self.stats["last_run"] = datetime.now()
        
        try:
            if self.use_celery:
                # Use Celery task
                task = scrape_all_subreddits_task.delay()
                logger.info(f"Celery task started: {task.id}")
                
                # Wait for task completion (with timeout)
                result = task.get(timeout=3600)  # 1 hour timeout
                logger.info(f"Scraping completed: {result}")
                
            else:
                # Direct execution
                results = RedditScrapingOrchestrator.scrape_all_active_subreddits()
                
                if results:
                    successful = sum(1 for r in results.values() if r.get("success", False))
                    total = len(results)
                    total_posts = sum(r.get("posts_scraped", 0) for r in results.values() if r.get("success", False))
                    
                    logger.info(f"Scraping completed: {successful}/{total} subreddits, {total_posts} posts")
                else:
                    logger.warning("No active subreddits found for scraping")
            
            self.stats["successful_runs"] += 1
            
        except Exception as e:
            logger.error(f"Error during scheduled scraping: {e}")
            self.stats["failed_runs"] += 1
    
    def _run_subreddit_scraping(self, subreddit_name: str):
        """Execute scraping for a specific subreddit"""
        logger.info(f"Starting scheduled scraping for r/{subreddit_name}")
        
        try:
            if self.use_celery:
                # Use Celery task
                task = scrape_specific_subreddit_task.delay(subreddit_name, "day", None)
                result = task.get(timeout=1800)  # 30 minutes timeout
                logger.info(f"r/{subreddit_name} scraping completed: {result}")
                
            else:
                # Direct execution
                config = DatabaseManager.get_subreddit_config(subreddit_name)
                if config and config.active:
                    from .reddit_manager import RedditAPIManager
                    api_manager = RedditAPIManager(config)
                    posts = api_manager.scrape_subreddit_posts("day")
                    logger.info(f"r/{subreddit_name} scraping completed: {len(posts)} posts")
                else:
                    logger.warning(f"r/{subreddit_name} not found or not active")
            
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit_name}: {e}")
    
    def _run_new_posts_monitoring(self):
        """Monitor for new posts across all active subreddits"""
        logger.info("Starting new posts monitoring")
        
        try:
            active_configs = DatabaseManager.get_active_subreddits()
            
            for config in active_configs:
                try:
                    if self.use_celery:
                        # Use Celery task for new posts
                        from .new_tasks import scrape_new_posts_task
                        task = scrape_new_posts_task.delay(config.name, 25)  # Limit to 25 new posts
                        # Don't wait for completion to avoid blocking
                        logger.info(f"New posts monitoring task started for r/{config.name}: {task.id}")
                    else:
                        # Direct execution
                        from .reddit_manager import RedditAPIManager
                        api_manager = RedditAPIManager(config)
                        posts = api_manager.scrape_new_posts(25)
                        logger.info(f"New posts monitoring for r/{config.name}: {len(posts)} posts")
                        
                except Exception as e:
                    logger.error(f"Error monitoring new posts for r/{config.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during new posts monitoring: {e}")
    
    def start_scheduler(self):
        """Start the scheduler and run continuously"""
        logger.info("Starting Reddit scraping scheduler")
        self.running = True
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            self.running = False
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        logger.info("Stopping Reddit scraping scheduler")
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return {
            **self.stats,
            "running": self.running,
            "scheduled_jobs": len(schedule.jobs),
            "next_scheduled_run": str(schedule.next_run()) if schedule.jobs else None
        }
    
    def clear_schedule(self):
        """Clear all scheduled jobs"""
        schedule.clear()
        logger.info("All scheduled jobs cleared")

class RedditScrapingDaemon:
    """Daemon process for continuous Reddit scraping"""
    
    def __init__(self, config_file: str = None):
        """
        Initialize the daemon
        
        Args:
            config_file: Optional configuration file path
        """
        self.scheduler = RedditScrapingScheduler(use_celery=True)
        self.config = self._load_config(config_file)
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load daemon configuration"""
        default_config = {
            "continuous_scraping_interval": 6,  # hours
            "new_posts_monitoring_interval": 30,  # minutes
            "enable_continuous_scraping": True,
            "enable_new_posts_monitoring": True,
            "log_level": "INFO"
        }
        
        if config_file:
            try:
                import json
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Could not load config file {config_file}: {e}")
        
        return default_config
    
    def setup_schedules(self):
        """Setup all scheduled tasks based on configuration"""
        logger.info("Setting up scheduled tasks")
        
        if self.config.get("enable_continuous_scraping", True):
            interval = self.config.get("continuous_scraping_interval", 6)
            self.scheduler.schedule_continuous_scraping(interval)
        
        if self.config.get("enable_new_posts_monitoring", True):
            interval = self.config.get("new_posts_monitoring_interval", 30)
            self.scheduler.schedule_new_posts_monitoring(interval)
        
        # Schedule individual subreddits based on their configurations
        active_configs = DatabaseManager.get_active_subreddits()
        for config in active_configs:
            if config.scraping_interval_hours != 6:  # If different from default
                self.scheduler.schedule_subreddit_specific(
                    config.name, 
                    config.scraping_interval_hours
                )
    
    def run(self):
        """Run the daemon"""
        logger.info("Starting Reddit scraping daemon")
        
        try:
            # Initialize database if needed
            DatabaseManager.create_indexes()
            
            # Setup schedules
            self.setup_schedules()
            
            # Start scheduler
            self.scheduler.start_scheduler()
            
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            raise

def main():
    """Main entry point for the scheduler"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        # Run as daemon
        daemon = RedditScrapingDaemon()
        daemon.run()
    else:
        # Interactive mode
        print("Reddit Scraping Scheduler")
        print("1. Start continuous scraping (every 6 hours)")
        print("2. Start new posts monitoring (every 30 minutes)")
        print("3. Custom schedule")
        print("4. Run daemon mode")
        
        choice = input("Select option (1-4): ").strip()
        
        scheduler = RedditScrapingScheduler(use_celery=False)
        
        if choice == "1":
            scheduler.schedule_continuous_scraping(6)
            scheduler.start_scheduler()
        elif choice == "2":
            scheduler.schedule_new_posts_monitoring(30)
            scheduler.start_scheduler()
        elif choice == "3":
            hours = int(input("Enter scraping interval in hours: "))
            scheduler.schedule_continuous_scraping(hours)
            scheduler.start_scheduler()
        elif choice == "4":
            daemon = RedditScrapingDaemon()
            daemon.run()
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main() 