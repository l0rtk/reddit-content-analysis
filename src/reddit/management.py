#!/usr/bin/env python3
"""
Reddit Scraping Management Script

This script provides easy-to-use functions for managing the Reddit scraping system.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from .models import DatabaseManager, SubredditConfig
from .reddit_manager import RedditAPIManager, RedditScrapingOrchestrator
from .new_tasks import (
    scrape_all_subreddits_task,
    scrape_specific_subreddit_task,
    scrape_new_posts_task,
    setup_subreddit_config_task,
    initialize_database_task
)

class RedditScrapingManager:
    """High-level management interface for Reddit scraping system"""
    
    @staticmethod
    def initialize_system():
        """Initialize the database and create necessary indexes"""
        print("Initializing Reddit scraping system...")
        try:
            DatabaseManager.create_indexes()
            print("✅ Database indexes created successfully")
            return True
        except Exception as e:
            print(f"❌ Error initializing system: {e}")
            return False
    
    @staticmethod
    def add_subreddit(name: str, client_id: str, client_secret: str, username: str, 
                     password: str, user_agent: str, **kwargs) -> bool:
        """
        Add a new subreddit configuration
        
        Args:
            name: Subreddit name (without r/)
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            username: Reddit username
            password: Reddit password
            user_agent: Reddit API user agent
            **kwargs: Additional configuration options
        
        Returns:
            bool: Success status
        """
        print(f"Adding configuration for r/{name}...")
        
        try:
            # Create configuration
            config = SubredditConfig(
                name=name,
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=password,
                user_agent=user_agent,
                **kwargs
            )
            
            # Test the configuration
            print(f"Testing Reddit API connection for r/{name}...")
            api_manager = RedditAPIManager(config)
            api_manager.check_rate_limit()
            
            # Save configuration
            success = DatabaseManager.save_subreddit_config(config)
            if success:
                print(f"✅ Successfully added r/{name} configuration")
                return True
            else:
                print(f"❌ Failed to save configuration for r/{name}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding r/{name}: {e}")
            return False
    
    @staticmethod
    def list_subreddits() -> List[Dict[str, Any]]:
        """List all configured subreddits"""
        configs = DatabaseManager.get_active_subreddits()
        
        if not configs:
            print("No subreddit configurations found")
            return []
        
        print(f"\n📋 Found {len(configs)} configured subreddits:")
        print("-" * 80)
        
        subreddit_info = []
        for config in configs:
            last_scraped = config.last_scraped.strftime("%Y-%m-%d %H:%M:%S") if config.last_scraped else "Never"
            
            info = {
                "name": config.name,
                "active": config.active,
                "last_scraped": last_scraped,
                "interval_hours": config.scraping_interval_hours,
                "max_posts": config.max_posts_per_scrape,
                "scrape_comments": config.scrape_comments
            }
            
            subreddit_info.append(info)
            
            print(f"📍 r/{config.name}")
            print(f"   Active: {'✅' if config.active else '❌'}")
            print(f"   Last scraped: {last_scraped}")
            print(f"   Interval: {config.scraping_interval_hours} hours")
            print(f"   Max posts: {config.max_posts_per_scrape}")
            print(f"   Scrape comments: {'✅' if config.scrape_comments else '❌'}")
            print()
        
        return subreddit_info
    
    @staticmethod
    def scrape_subreddit(name: str, time_filter: str = "day", limit: int = None) -> bool:
        """
        Scrape a specific subreddit
        
        Args:
            name: Subreddit name
            time_filter: Time filter (hour, day, week, month, year, all)
            limit: Number of posts to scrape
        
        Returns:
            bool: Success status
        """
        print(f"Starting scrape for r/{name}...")
        
        try:
            config = DatabaseManager.get_subreddit_config(name)
            if not config:
                print(f"❌ No configuration found for r/{name}")
                return False
            
            if not config.active:
                print(f"❌ r/{name} is not active")
                return False
            
            api_manager = RedditAPIManager(config)
            posts = api_manager.scrape_subreddit_posts(time_filter, limit)
            
            print(f"✅ Successfully scraped {len(posts)} posts from r/{name}")
            return True
            
        except Exception as e:
            print(f"❌ Error scraping r/{name}: {e}")
            return False
    
    @staticmethod
    def scrape_all_subreddits() -> Dict[str, Any]:
        """Scrape all active subreddits"""
        print("Starting scrape for all active subreddits...")
        
        try:
            results = RedditScrapingOrchestrator.scrape_all_active_subreddits()
            
            if results:
                successful = sum(1 for r in results.values() if r.get("success", False))
                total = len(results)
                total_posts = sum(r.get("posts_scraped", 0) for r in results.values() if r.get("success", False))
                
                print(f"✅ Completed scraping {successful}/{total} subreddits")
                print(f"📊 Total posts scraped: {total_posts}")
                
                # Show detailed results
                for subreddit, result in results.items():
                    if result.get("success"):
                        print(f"   ✅ r/{subreddit}: {result.get('posts_scraped', 0)} posts")
                    else:
                        print(f"   ❌ r/{subreddit}: {result.get('error', 'Unknown error')}")
            else:
                print("❌ No active subreddits found")
            
            return results or {}
            
        except Exception as e:
            print(f"❌ Error scraping subreddits: {e}")
            return {}
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get system statistics"""
        print("📊 System Statistics")
        print("-" * 40)
        
        try:
            # Get collection counts
            from .models import subreddits_collection, posts_collection, comments_collection, rate_limits_collection
            
            stats = {
                "subreddits": subreddits_collection.count_documents({}),
                "active_subreddits": subreddits_collection.count_documents({"active": True}),
                "total_posts": posts_collection.count_documents({}),
                "total_comments": comments_collection.count_documents({}),
                "rate_limit_records": rate_limits_collection.count_documents({})
            }
            
            print(f"Configured subreddits: {stats['subreddits']}")
            print(f"Active subreddits: {stats['active_subreddits']}")
            print(f"Total posts: {stats['total_posts']:,}")
            print(f"Total comments: {stats['total_comments']:,}")
            print(f"Rate limit records: {stats['rate_limit_records']}")
            
            # Get recent activity
            recent_posts = posts_collection.count_documents({
                "scraped_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            recent_comments = comments_collection.count_documents({
                "scraped_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            stats.update({
                "posts_today": recent_posts,
                "comments_today": recent_comments
            })
            
            print(f"Posts scraped today: {recent_posts:,}")
            print(f"Comments scraped today: {recent_comments:,}")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {}
    
    @staticmethod
    def activate_subreddit(name: str) -> bool:
        """Activate a subreddit for scraping"""
        try:
            config = DatabaseManager.get_subreddit_config(name)
            if not config:
                print(f"❌ No configuration found for r/{name}")
                return False
            
            config.active = True
            success = DatabaseManager.save_subreddit_config(config)
            
            if success:
                print(f"✅ Activated r/{name}")
                return True
            else:
                print(f"❌ Failed to activate r/{name}")
                return False
                
        except Exception as e:
            print(f"❌ Error activating r/{name}: {e}")
            return False
    
    @staticmethod
    def deactivate_subreddit(name: str) -> bool:
        """Deactivate a subreddit from scraping"""
        try:
            config = DatabaseManager.get_subreddit_config(name)
            if not config:
                print(f"❌ No configuration found for r/{name}")
                return False
            
            config.active = False
            success = DatabaseManager.save_subreddit_config(config)
            
            if success:
                print(f"✅ Deactivated r/{name}")
                return True
            else:
                print(f"❌ Failed to deactivate r/{name}")
                return False
                
        except Exception as e:
            print(f"❌ Error deactivating r/{name}: {e}")
            return False
    
    @staticmethod
    def get_comment_tree(post_id: str) -> Dict[str, Any]:
        """Get hierarchical comment tree for a post"""
        try:
            tree = DatabaseManager.get_comment_tree(post_id)
            
            if tree['total_comments'] == 0:
                print(f"No comments found for post {post_id}")
            else:
                print(f"📝 Comment tree for post {post_id}")
                print(f"Total comments: {tree['total_comments']}")
                print(f"Root comments: {len(tree['root_comments'])}")
            
            return tree
            
        except Exception as e:
            print(f"❌ Error getting comment tree: {e}")
            return {}

def main():
    """Command-line interface for the management script"""
    if len(sys.argv) < 2:
        print("Reddit Scraping Management Tool")
        print("Usage: python -m src.reddit.management <command> [args...]")
        print("\nCommands:")
        print("  init                     - Initialize the system")
        print("  list                     - List all subreddits")
        print("  add <name> <credentials> - Add subreddit configuration")
        print("  scrape <name>            - Scrape specific subreddit")
        print("  scrape-all               - Scrape all active subreddits")
        print("  activate <name>          - Activate subreddit")
        print("  deactivate <name>        - Deactivate subreddit")
        print("  stats                    - Show system statistics")
        return
    
    command = sys.argv[1].lower()
    manager = RedditScrapingManager()
    
    if command == "init":
        manager.initialize_system()
    
    elif command == "list":
        manager.list_subreddits()
    
    elif command == "scrape-all":
        manager.scrape_all_subreddits()
    
    elif command == "stats":
        manager.get_stats()
    
    elif command == "scrape" and len(sys.argv) >= 3:
        subreddit_name = sys.argv[2]
        manager.scrape_subreddit(subreddit_name)
    
    elif command == "activate" and len(sys.argv) >= 3:
        subreddit_name = sys.argv[2]
        manager.activate_subreddit(subreddit_name)
    
    elif command == "deactivate" and len(sys.argv) >= 3:
        subreddit_name = sys.argv[2]
        manager.deactivate_subreddit(subreddit_name)
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'python -m src.reddit.management' for help")

if __name__ == "__main__":
    main() 