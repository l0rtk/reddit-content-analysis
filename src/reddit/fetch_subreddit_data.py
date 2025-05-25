import praw
from datetime import datetime
from dotenv import load_dotenv
import pymongo
import os
import time


load_dotenv()

client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
db = client["techbro"]
collection = db["reddit_posts"]


reddit = praw.Reddit(
    client_id=os.getenv("R_CLIENT_ID"),
    client_secret=os.getenv("R_CLIENT_SECRET"),
    username=os.getenv("R_USERNAME"),
    password=os.getenv("R_PASSWORD"),
    user_agent=os.getenv("R_USER_AGENT")
)


def check_rate_limit(min_remaining=50):
    """
    Check Reddit API rate limits and wait if necessary.
    
    Args:
        min_remaining (int): Minimum number of requests to keep in reserve
    
    Returns:
        dict: Rate limit information
    """
    try:
        rate_limit = reddit.auth.limits
        remaining = rate_limit.get('remaining')
        used = rate_limit.get('used')
        reset_time = rate_limit.get('reset_timestamp')
        
        # Handle None values
        if remaining is None or used is None or reset_time is None:
            print("Rate limit info not available, adding precautionary delay...")
            time.sleep(1)
            return None
            
        time_until_reset = reset_time - time.time()
        
        print(f"Rate limit - Remaining: {remaining}, Used: {used}, Reset in: {time_until_reset:.1f}s")
        
        # If we're running low on requests, wait for reset
        if remaining <= min_remaining:
            if time_until_reset > 0:
                print(f"Rate limit low ({remaining} remaining). Waiting {time_until_reset:.1f} seconds for reset...")
                time.sleep(time_until_reset + 5)  # Add 5 seconds buffer
                print("Rate limit reset. Continuing...")
            else:
                print("Rate limit reset time has passed. Continuing...")
        
        return {
            'remaining': remaining,
            'used': used,
            'reset_in_seconds': time_until_reset
        }
    except Exception as e:
        print(f"Error checking rate limit: {e}")
        # If we can't check rate limits, add a small delay as precaution
        time.sleep(1)
        return None


def safe_api_call(func, *args, **kwargs):
    """
    Wrapper for API calls that checks rate limits before making the call.
    
    Args:
        func: The function to call
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        The result of the function call
    """
    check_rate_limit()
    return func(*args, **kwargs)


def get_comment_data(comment):
    """
    Get comment data for top-level comments only (no replies).
    
    Args:
        comment: Reddit comment object
    """
    if not hasattr(comment, 'body'):
        return None

    comment_data = {
        "body": comment.body,
        "author": str(comment.author),
        "score": comment.score,
        "date": comment.created_utc,
        "id": comment.id
    }
    
    return comment_data

def fetch_subreddit_data_logic(subreddit_name: str, time_filter: str, limit: int):
    # Initial rate limit check
    print("Checking initial rate limits...")
    check_rate_limit()
    
    subreddit = reddit.subreddit(subreddit_name)
    posts_data = []
    print(f'Fetching top {limit} posts from r/{subreddit_name}')
    
    # Get submissions with rate limit awareness
    submissions = safe_api_call(subreddit.top, time_filter=time_filter, limit=limit)
    
    for i, submission in enumerate(submissions, 1):
        print(f'Processing post {i}/{limit}: {submission.title[:50]}...')
        
        # Check rate limit before processing each post
        check_rate_limit()
        
        post_info = {
            "id": submission.id,
            "title": submission.title,
            "body": submission.selftext,
            "score": submission.score,
            "date": submission.created_utc,
            "url": submission.url,
            "author": str(submission.author),
            "comments": []
        }
        
        # Check rate limit before expanding comments
        print(f"  Fetching top-level comments for post {i}...")
        check_rate_limit()
        submission.comments.replace_more(limit=0)  # Don't expand any "more comments"
        
        comment_count = 0
        max_comments = 200  # Increase limit since we're only getting top-level comments
        
        # Get only top-level comments (no replies)
        for top_level_comment in submission.comments:
            if comment_count >= max_comments:
                print(f"  Reached comment limit ({max_comments}) for post {i}")
                break
                
            # Check rate limit every 50 comments since we're not fetching replies
            if comment_count % 50 == 0 and comment_count > 0:
                check_rate_limit()
            
            comment_details = get_comment_data(top_level_comment)
            if comment_details:
                post_info["comments"].append(comment_details)
                comment_count += 1
        
        print(f"  Collected {comment_count} comments for post {i}")
        posts_data.append(post_info)
        
        # Small delay between posts to be respectful
        time.sleep(0.5)
    
    return posts_data


def fetch_and_save_subreddit_data(subreddit: str, time_filter: str = "month", limit: int = 10):
    try:
        print(f"Fetching data for {subreddit} with time filter {time_filter} and limit {limit}")
        data = fetch_subreddit_data_logic(subreddit, time_filter, limit)
        print(f"Fetched {len(data)} posts")
        
        # Track save status for each post
        save_status = {
            "updated": 0,
            "inserted": 0,
            "failed": 0,
            "errors": []
        }
        
        # Save or update each post as an independent document
        for post in data:
            try:
                # Create a complete document with metadata
                document = {
                    **post,  # Include all post data
                    "subreddit": subreddit,
                    "time_filter": time_filter,
                    "fetch_timestamp": datetime.now().isoformat(),
                    "fetch_limit": limit
                }
                
                # Try to update or insert the document
                result = collection.update_one(
                    {"id": post["id"]},  # Find by post ID
                    {"$set": document},  # Update with new data
                    upsert=True  # Insert if not found
                )
                
                if result.upserted_id:
                    save_status["inserted"] += 1
                elif result.modified_count > 0:
                    save_status["updated"] += 1
                else:
                    save_status["failed"] += 1
                    save_status["errors"].append(f"Failed to save/update post {post.get('id', 'unknown')}")
                    
            except Exception as e:
                save_status["failed"] += 1
                save_status["errors"].append(f"Error saving/updating post {post.get('id', 'unknown')}: {str(e)}")
        
        # Print save status
        print(f"Save status: {save_status['inserted']} inserted, {save_status['updated']} updated, {save_status['failed']} failed")
        if save_status["errors"]:
            print("Errors encountered:")
            for error in save_status["errors"]:
                print(f"- {error}")
        
        return {
            "subreddit": subreddit,
            "time_filter": time_filter,
            "limit": limit,
            "fetch_timestamp": datetime.now().isoformat(),
            "total_posts": len(data),
            "save_status": save_status
        }
        
    except Exception as e:
        print(f"Error in fetch_subreddit_data: {e}")
        return {
            "subreddit": subreddit,
            "time_filter": time_filter,
            "limit": limit,
            "fetch_timestamp": datetime.now().isoformat(),
            "total_posts": 0,
            "error": str(e),
            "save_status": {
                "updated": 0,
                "inserted": 0,
                "failed": 0,
                "errors": [str(e)]
            }
        }




if __name__ == "__main__":
    fetch_and_save_subreddit_data("programming", 'month', 2) 