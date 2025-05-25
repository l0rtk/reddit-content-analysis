from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
db = client["techbro"]

# Collections
subreddits_collection = db["subreddits"]
posts_collection = db["posts"]
comments_collection = db["comments"]
rate_limits_collection = db["rate_limits"]

@dataclass
class SubredditConfig:
    """Configuration for a subreddit including API credentials"""
    name: str
    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str
    active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    last_scraped: datetime = None
    scraping_interval_hours: int = 24
    max_posts_per_scrape: int = 100
    scrape_comments: bool = True
    max_comments_per_post: int = 500
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return asdict(self)

@dataclass
class RedditPost:
    """Reddit post data model"""
    id: str
    subreddit: str
    title: str
    body: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    url: str
    author: str
    permalink: str
    is_self: bool
    is_video: bool
    over_18: bool
    spoiler: bool
    stickied: bool
    locked: bool
    archived: bool
    gilded: int
    distinguished: Optional[str]
    link_flair_text: Optional[str]
    post_hint: Optional[str]
    thumbnail: Optional[str]
    domain: Optional[str]
    scraped_at: datetime = None
    
    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow()
    
    def to_dict(self):
        return asdict(self)

@dataclass
class RedditComment:
    """Reddit comment data model with parent-child relationships"""
    id: str
    post_id: str
    subreddit: str
    parent_id: Optional[str]  # None for top-level comments
    body: str
    author: str
    score: int
    created_utc: float
    edited: bool
    is_submitter: bool
    stickied: bool
    gilded: int
    distinguished: Optional[str]
    depth: int  # Comment nesting level (0 for top-level)
    permalink: str
    scraped_at: datetime = None
    
    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow()
    
    def to_dict(self):
        return asdict(self)

@dataclass
class RateLimit:
    """Rate limit tracking for API credentials"""
    credential_id: str  # Unique identifier for API credentials
    subreddit: str
    remaining: int
    used: int
    reset_timestamp: float
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()
    
    def to_dict(self):
        return asdict(self)

class DatabaseManager:
    """Database operations manager"""
    
    @staticmethod
    def create_indexes():
        """Create necessary indexes for optimal performance"""
        # Subreddits indexes
        subreddits_collection.create_index("name", unique=True)
        subreddits_collection.create_index("active")
        
        # Posts indexes
        posts_collection.create_index("id", unique=True)
        posts_collection.create_index("subreddit")
        posts_collection.create_index("created_utc")
        posts_collection.create_index("scraped_at")
        posts_collection.create_index([("subreddit", 1), ("created_utc", -1)])
        
        # Comments indexes
        comments_collection.create_index("id", unique=True)
        comments_collection.create_index("post_id")
        comments_collection.create_index("parent_id")
        comments_collection.create_index("subreddit")
        comments_collection.create_index("created_utc")
        comments_collection.create_index([("post_id", 1), ("parent_id", 1)])
        comments_collection.create_index([("subreddit", 1), ("created_utc", -1)])
        
        # Rate limits indexes
        rate_limits_collection.create_index("credential_id", unique=True)
        rate_limits_collection.create_index("subreddit")
        rate_limits_collection.create_index("last_updated")
    
    @staticmethod
    def save_subreddit_config(config: SubredditConfig) -> bool:
        """Save or update subreddit configuration"""
        try:
            result = subreddits_collection.update_one(
                {"name": config.name},
                {"$set": config.to_dict()},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving subreddit config: {e}")
            return False
    
    @staticmethod
    def get_subreddit_config(name: str) -> Optional[SubredditConfig]:
        """Get subreddit configuration by name"""
        try:
            doc = subreddits_collection.find_one({"name": name})
            if doc:
                # Remove MongoDB _id field
                doc.pop('_id', None)
                return SubredditConfig(**doc)
            return None
        except Exception as e:
            print(f"Error getting subreddit config: {e}")
            return None
    
    @staticmethod
    def get_active_subreddits() -> List[SubredditConfig]:
        """Get all active subreddit configurations"""
        try:
            docs = subreddits_collection.find({"active": True})
            configs = []
            for doc in docs:
                doc.pop('_id', None)
                configs.append(SubredditConfig(**doc))
            return configs
        except Exception as e:
            print(f"Error getting active subreddits: {e}")
            return []
    
    @staticmethod
    def save_post(post: RedditPost) -> bool:
        """Save or update a Reddit post"""
        try:
            result = posts_collection.update_one(
                {"id": post.id},
                {"$set": post.to_dict()},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving post {post.id}: {e}")
            return False
    
    @staticmethod
    def save_comment(comment: RedditComment) -> bool:
        """Save or update a Reddit comment"""
        try:
            result = comments_collection.update_one(
                {"id": comment.id},
                {"$set": comment.to_dict()},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving comment {comment.id}: {e}")
            return False
    
    @staticmethod
    def update_rate_limit(rate_limit: RateLimit) -> bool:
        """Update rate limit information"""
        try:
            result = rate_limits_collection.update_one(
                {"credential_id": rate_limit.credential_id},
                {"$set": rate_limit.to_dict()},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating rate limit: {e}")
            return False
    
    @staticmethod
    def get_rate_limit(credential_id: str) -> Optional[RateLimit]:
        """Get rate limit information for credentials"""
        try:
            doc = rate_limits_collection.find_one({"credential_id": credential_id})
            if doc:
                doc.pop('_id', None)
                return RateLimit(**doc)
            return None
        except Exception as e:
            print(f"Error getting rate limit: {e}")
            return None
    
    @staticmethod
    def get_post_comments(post_id: str) -> List[RedditComment]:
        """Get all comments for a specific post"""
        try:
            docs = comments_collection.find({"post_id": post_id}).sort("created_utc", 1)
            comments = []
            for doc in docs:
                doc.pop('_id', None)
                comments.append(RedditComment(**doc))
            return comments
        except Exception as e:
            print(f"Error getting comments for post {post_id}: {e}")
            return []
    
    @staticmethod
    def get_comment_tree(post_id: str) -> Dict[str, Any]:
        """Build a hierarchical comment tree for a post"""
        comments = DatabaseManager.get_post_comments(post_id)
        
        # Create a dictionary to store comments by ID
        comment_dict = {comment.id: comment.to_dict() for comment in comments}
        
        # Add children list to each comment
        for comment in comment_dict.values():
            comment['children'] = []
        
        # Build the tree structure
        root_comments = []
        for comment in comments:
            if comment.parent_id is None:
                # Top-level comment
                root_comments.append(comment_dict[comment.id])
            else:
                # Child comment - add to parent's children list
                if comment.parent_id in comment_dict:
                    comment_dict[comment.parent_id]['children'].append(comment_dict[comment.id])
        
        return {
            'post_id': post_id,
            'total_comments': len(comments),
            'root_comments': root_comments
        }

# Initialize database indexes when module is imported
if __name__ == "__main__":
    DatabaseManager.create_indexes()
    print("Database indexes created successfully!") 