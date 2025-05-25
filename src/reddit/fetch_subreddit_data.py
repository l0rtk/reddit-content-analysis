import praw
from datetime import datetime
from dotenv import load_dotenv
import pymongo
import os


load_dotenv()

client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
db = client["techbro"]
collection = db["reddit_posts"]


print(os.getenv("R_CLIENT_ID"))
print(os.getenv("R_CLIENT_SECRET"))
print(os.getenv("R_USER_AGENT"))
reddit = praw.Reddit(
    client_id=os.getenv("R_CLIENT_ID"),
    client_secret=os.getenv("R_CLIENT_SECRET"),
    user_agent=os.getenv("R_USER_AGENT")
)


def get_comment_data(comment):
    if not hasattr(comment, 'body'):
        return None

    comment_data = {
        "body": comment.body,
        "author": str(comment.author),
        "score": comment.score,
        "date": comment.created_utc,
        "id": comment.id,
        "replies": []
    }
    if hasattr(comment, 'replies') and comment.replies:
        comment.replies.replace_more(limit=None)
        for reply in comment.replies.list():
            reply_data = get_comment_data(reply)
            if reply_data:
                comment_data["replies"].append(reply_data)
    return comment_data

def fetch_subreddit_data_logic(subreddit_name: str, time_filter: str, limit: int):
    subreddit = reddit.subreddit(subreddit_name)
    posts_data = []
    print('hereeee')
    for submission in subreddit.top(time_filter=time_filter, limit=limit):
            print('here')
            print(submission)
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
            submission.comments.replace_more(limit=None)
            for top_level_comment in submission.comments.list():
                comment_details = get_comment_data(top_level_comment)
                if comment_details:
                    post_info["comments"].append(comment_details)
            posts_data.append(post_info)
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