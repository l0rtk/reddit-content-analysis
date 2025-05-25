import praw
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from .models import (
    SubredditConfig, RedditPost, RedditComment, RateLimit, 
    DatabaseManager
)

class RedditAPIManager:
    """Manages Reddit API connections with rate limiting and multiple credentials"""
    
    def __init__(self, config: SubredditConfig):
        self.config = config
        self.credential_id = self._generate_credential_id()
        self.reddit = None
        self._initialize_reddit_client()
    
    def _generate_credential_id(self) -> str:
        """Generate unique identifier for API credentials"""
        credential_string = f"{self.config.client_id}:{self.config.username}"
        return hashlib.md5(credential_string.encode()).hexdigest()
    
    def _initialize_reddit_client(self):
        """Initialize Reddit client with credentials"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                username=self.config.username,
                password=self.config.password,
                user_agent=self.config.user_agent
            )
            print(f"Reddit client initialized for {self.config.name} as {self.reddit.user.me()}")
        except Exception as e:
            print(f"Failed to initialize Reddit client for {self.config.name}: {e}")
            raise
    
    def check_rate_limit(self, min_remaining: int = 50) -> Optional[RateLimit]:
        """
        Check and manage Reddit API rate limits
        
        Args:
            min_remaining: Minimum requests to keep in reserve
            
        Returns:
            RateLimit object with current status
        """
        try:
            # Get current rate limit from Reddit API
            limits = self.reddit.auth.limits
            
            if not limits or any(v is None for v in [limits.get('remaining'), limits.get('used'), limits.get('reset_timestamp')]):
                print(f"Rate limit info not available for {self.config.name}, adding precautionary delay...")
                time.sleep(2)
                return None
            
            rate_limit = RateLimit(
                credential_id=self.credential_id,
                subreddit=self.config.name,
                remaining=limits['remaining'],
                used=limits['used'],
                reset_timestamp=limits['reset_timestamp']
            )
            
            # Save rate limit to database
            DatabaseManager.update_rate_limit(rate_limit)
            
            time_until_reset = rate_limit.reset_timestamp - time.time()
            
            print(f"Rate limit for {self.config.name} - Remaining: {rate_limit.remaining}, "
                  f"Used: {rate_limit.used}, Reset in: {time_until_reset:.1f}s")
            
            # If running low on requests, wait for reset
            if rate_limit.remaining <= min_remaining:
                if time_until_reset > 0:
                    print(f"Rate limit low for {self.config.name} ({rate_limit.remaining} remaining). "
                          f"Waiting {time_until_reset:.1f} seconds for reset...")
                    time.sleep(time_until_reset + 10)  # Add 10 seconds buffer
                    print(f"Rate limit reset for {self.config.name}. Continuing...")
                else:
                    print(f"Rate limit reset time has passed for {self.config.name}. Continuing...")
            
            return rate_limit
            
        except Exception as e:
            print(f"Error checking rate limit for {self.config.name}: {e}")
            time.sleep(2)  # Precautionary delay
            return None
    
    def safe_api_call(self, func, *args, **kwargs):
        """Wrapper for API calls that checks rate limits"""
        self.check_rate_limit()
        return func(*args, **kwargs)
    
    def extract_post_data(self, submission) -> RedditPost:
        """Extract comprehensive post data from Reddit submission"""
        return RedditPost(
            id=submission.id,
            subreddit=str(submission.subreddit),
            title=submission.title,
            body=submission.selftext or "",
            score=submission.score,
            upvote_ratio=getattr(submission, 'upvote_ratio', 0.0),
            num_comments=submission.num_comments,
            created_utc=submission.created_utc,
            url=submission.url,
            author=str(submission.author) if submission.author else "[deleted]",
            permalink=submission.permalink,
            is_self=submission.is_self,
            is_video=submission.is_video,
            over_18=submission.over_18,
            spoiler=submission.spoiler,
            stickied=submission.stickied,
            locked=submission.locked,
            archived=submission.archived,
            gilded=getattr(submission, 'gilded', 0),
            distinguished=submission.distinguished,
            link_flair_text=submission.link_flair_text,
            post_hint=getattr(submission, 'post_hint', None),
            thumbnail=getattr(submission, 'thumbnail', None),
            domain=getattr(submission, 'domain', None)
        )
    
    def extract_comment_data(self, comment, post_id: str, depth: int = 0) -> Optional[RedditComment]:
        """Extract comment data with parent-child relationships"""
        if not hasattr(comment, 'body') or comment.body in ['[deleted]', '[removed]']:
            return None
        
        # Determine parent ID
        parent_id = None
        if hasattr(comment, 'parent_id') and comment.parent_id:
            parent_id = comment.parent_id.split('_')[1] if '_' in comment.parent_id else comment.parent_id
            # If parent is the post itself, set parent_id to None (top-level comment)
            if parent_id == post_id:
                parent_id = None
        
        return RedditComment(
            id=comment.id,
            post_id=post_id,
            subreddit=str(comment.subreddit),
            parent_id=parent_id,
            body=comment.body,
            author=str(comment.author) if comment.author else "[deleted]",
            score=comment.score,
            created_utc=comment.created_utc,
            edited=bool(comment.edited),
            is_submitter=comment.is_submitter,
            stickied=comment.stickied,
            gilded=getattr(comment, 'gilded', 0),
            distinguished=comment.distinguished,
            depth=depth,
            permalink=comment.permalink
        )
    
    def scrape_comments_recursive(self, comment_forest, post_id: str, max_comments: int, 
                                 current_count: int = 0, depth: int = 0) -> Tuple[List[RedditComment], int]:
        """
        Recursively scrape comments maintaining parent-child relationships
        
        Args:
            comment_forest: Reddit comment forest
            post_id: ID of the parent post
            max_comments: Maximum number of comments to scrape
            current_count: Current number of comments scraped
            depth: Current nesting depth
            
        Returns:
            Tuple of (comments_list, total_count)
        """
        comments = []
        
        for comment in comment_forest:
            if current_count >= max_comments:
                break
            
            # Check rate limit every 100 comments
            if current_count % 100 == 0 and current_count > 0:
                self.check_rate_limit()
            
            # Extract comment data
            comment_data = self.extract_comment_data(comment, post_id, depth)
            if comment_data:
                comments.append(comment_data)
                current_count += 1
                
                # Recursively process replies
                if hasattr(comment, 'replies') and comment.replies and current_count < max_comments:
                    reply_comments, current_count = self.scrape_comments_recursive(
                        comment.replies, post_id, max_comments, current_count, depth + 1
                    )
                    comments.extend(reply_comments)
        
        return comments, current_count
    
    def scrape_subreddit_posts(self, time_filter: str = "day", limit: int = None, 
                              progress_callback=None) -> List[RedditPost]:
        """
        Scrape posts from the configured subreddit
        
        Args:
            time_filter: Time filter for posts (hour, day, week, month, year, all)
            limit: Number of posts to scrape (uses config default if None)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of RedditPost objects
        """
        if limit is None:
            limit = self.config.max_posts_per_scrape
        
        print(f"Scraping {limit} posts from r/{self.config.name} with time filter '{time_filter}'")
        
        # Initial rate limit check
        self.check_rate_limit()
        
        subreddit = self.reddit.subreddit(self.config.name)
        posts = []
        
        # Get submissions
        submissions = self.safe_api_call(subreddit.top, time_filter=time_filter, limit=limit)
        
        for i, submission in enumerate(submissions, 1):
            print(f"Processing post {i}/{limit}: {submission.title[:50]}...")
            
            if progress_callback:
                progress_callback(i, limit, f"Processing post {i}/{limit}: {submission.title[:50]}...")
            
            # Check rate limit before processing each post
            self.check_rate_limit()
            
            # Extract post data
            post_data = self.extract_post_data(submission)
            posts.append(post_data)
            
            # Save post to database
            DatabaseManager.save_post(post_data)
            
            # Scrape comments if enabled
            if self.config.scrape_comments:
                self.scrape_post_comments(submission, post_data.id)
            
            # Small delay between posts
            time.sleep(0.5)
        
        # Update last scraped timestamp
        self.config.last_scraped = datetime.utcnow()
        DatabaseManager.save_subreddit_config(self.config)
        
        return posts
    
    def scrape_post_comments(self, submission, post_id: str) -> List[RedditComment]:
        """
        Scrape all comments for a specific post
        
        Args:
            submission: Reddit submission object
            post_id: ID of the post
            
        Returns:
            List of RedditComment objects
        """
        print(f"  Scraping comments for post {post_id}...")
        
        # Check rate limit before expanding comments
        self.check_rate_limit()
        
        # Expand all comment trees (this might take time for large posts)
        submission.comments.replace_more(limit=None)
        
        # Recursively scrape comments
        comments, total_count = self.scrape_comments_recursive(
            submission.comments, post_id, self.config.max_comments_per_post
        )
        
        # Save comments to database
        saved_count = 0
        for comment in comments:
            if DatabaseManager.save_comment(comment):
                saved_count += 1
        
        print(f"  Scraped and saved {saved_count}/{total_count} comments for post {post_id}")
        return comments
    
    def scrape_new_posts(self, limit: int = None) -> List[RedditPost]:
        """Scrape newest posts from subreddit"""
        if limit is None:
            limit = min(self.config.max_posts_per_scrape, 100)  # Limit new posts
        
        print(f"Scraping {limit} new posts from r/{self.config.name}")
        
        self.check_rate_limit()
        subreddit = self.reddit.subreddit(self.config.name)
        posts = []
        
        submissions = self.safe_api_call(subreddit.new, limit=limit)
        
        for i, submission in enumerate(submissions, 1):
            print(f"Processing new post {i}/{limit}: {submission.title[:50]}...")
            
            self.check_rate_limit()
            post_data = self.extract_post_data(submission)
            posts.append(post_data)
            
            # Save post to database
            DatabaseManager.save_post(post_data)
            
            # Scrape comments if enabled
            if self.config.scrape_comments:
                self.scrape_post_comments(submission, post_data.id)
            
            time.sleep(0.5)
        
        return posts

class RedditScrapingOrchestrator:
    """Orchestrates scraping across multiple subreddits with different credentials"""
    
    @staticmethod
    def scrape_all_active_subreddits(progress_callback=None):
        """Scrape all active subreddits using their respective credentials"""
        active_configs = DatabaseManager.get_active_subreddits()
        
        if not active_configs:
            print("No active subreddit configurations found")
            return
        
        total_subreddits = len(active_configs)
        results = {}
        
        for i, config in enumerate(active_configs, 1):
            print(f"\n{'='*60}")
            print(f"Scraping subreddit {i}/{total_subreddits}: r/{config.name}")
            print(f"{'='*60}")
            
            try:
                # Check if it's time to scrape this subreddit
                if config.last_scraped:
                    time_since_last = datetime.utcnow() - config.last_scraped
                    if time_since_last < timedelta(hours=config.scraping_interval_hours):
                        print(f"Skipping r/{config.name} - scraped {time_since_last} ago, "
                              f"interval is {config.scraping_interval_hours} hours")
                        continue
                
                # Create API manager for this subreddit
                api_manager = RedditAPIManager(config)
                
                # Scrape posts
                posts = api_manager.scrape_subreddit_posts(
                    time_filter="day",  # Focus on daily content for continuous scraping
                    progress_callback=progress_callback
                )
                
                results[config.name] = {
                    "success": True,
                    "posts_scraped": len(posts),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                print(f"Successfully scraped {len(posts)} posts from r/{config.name}")
                
            except Exception as e:
                print(f"Error scraping r/{config.name}: {e}")
                results[config.name] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return results
    
    @staticmethod
    def scrape_subreddit_by_name(subreddit_name: str, time_filter: str = "day", 
                                limit: int = None, progress_callback=None):
        """Scrape a specific subreddit by name"""
        config = DatabaseManager.get_subreddit_config(subreddit_name)
        
        if not config:
            raise ValueError(f"No configuration found for subreddit: {subreddit_name}")
        
        if not config.active:
            raise ValueError(f"Subreddit {subreddit_name} is not active")
        
        api_manager = RedditAPIManager(config)
        return api_manager.scrape_subreddit_posts(time_filter, limit, progress_callback) 