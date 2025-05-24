import praw
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel # For request body if we need it later, good practice

# Initialize FastAPI app
app = FastAPI()

# PRAW Authentication (consider moving credentials to environment variables for production)
reddit = praw.Reddit(
    client_id="0STz-aj6UQnhcWIaEViQ1A",
    client_secret="BvDg-ZF4GX_G0x0oqVQGl5rbnRJq9Q",
    user_agent="techbro_api by /u/Techbro994" # Changed user agent for API
)

# --- Core Reddit fetching logic (adapted from main.py) ---
def get_comment_data(comment):
    if not hasattr(comment, 'body'):
        return None

    comment_data = {
        "body": comment.body,
        "author": str(comment.author),
        "score": comment.score,
        "date": comment.created_utc,
        "replies": []
    }
    if hasattr(comment, 'replies') and comment.replies:
        comment.replies.replace_more(limit=None)
        for reply in comment.replies.list():
            reply_data = get_comment_data(reply)
            if reply_data:
                comment_data["replies"].append(reply_data)
    return comment_data

def fetch_subreddit_data_logic(subreddit_name: str, time_filter: str = "month", limit: int = 10):
    try:
        subreddit = reddit.subreddit(subreddit_name)
        # Check if subreddit exists by trying to access an attribute
        # (PRAW can sometimes return a Subreddit object even if it doesn't exist, until you try to access data)
        subreddit.display_name 
    except Exception as e: # Broad exception to catch PRAW issues like 404 for non-existent subreddit
        print(f"Error accessing subreddit {subreddit_name}: {e}")
        raise HTTPException(status_code=404, detail=f"Subreddit '{subreddit_name}' not found or access issue.")

    posts_data = []
    try:
        for submission in subreddit.top(time_filter=time_filter, limit=limit):
            post_info = {
                "title": submission.title,
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
            print(f"Processed post: {submission.title} from r/{subreddit_name}")
        return posts_data
    except Exception as e:
        print(f"Error fetching posts from r/{subreddit_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching posts from subreddit: {e}")

# --- FastAPI Endpoint ---
@app.get("/fetch-subreddit-data/")
async def get_subreddit_posts(subreddit_name: str, time_filter: str = "month", limit: int = 10):
    """
    Fetches top posts from a given subreddit for a specified time filter and limit.
    Includes all threaded comments with their author, score, body, and creation date.
    """
    if not subreddit_name:
        raise HTTPException(status_code=400, detail="Subreddit name cannot be empty.")
    if limit <= 0 or limit > 100: # Example: sensible limit
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100.")
    
    valid_time_filters = ["all", "year", "month", "week", "day", "hour"]
    if time_filter not in valid_time_filters:
        raise HTTPException(status_code=400, detail=f"Invalid time_filter. Must be one of: {valid_time_filters}")

    print(f"Received request for r/{subreddit_name}, time_filter='{time_filter}', limit={limit}")
    data = fetch_subreddit_data_logic(subreddit_name, time_filter, limit)
    if not data: # If no posts were found (e.g., very new/empty subreddit but valid)
        print(f"No posts found for r/{subreddit_name} with current filters.")
        # Return empty list, not an error, if the subreddit is valid but has no matching posts
    return {"subreddit": subreddit_name, "time_filter": time_filter, "limit": limit, "posts": data}

# --- Instructions to run (can be in a README.md or here for now) ---
# To run this FastAPI server:
# 1. Make sure you have praw, fastapi, and uvicorn installed:
#    pip install praw fastapi "uvicorn[standard]"
#    (or pip install -r requirements.txt if requirements.txt is created)
# 2. Save this code as api.py (or your chosen filename).
# 3. Run the server using Uvicorn from your terminal:
#    uvicorn api:app --reload
#
# You can then access the API at:
# http://127.0.0.1:8000/fetch-subreddit-data/?subreddit_name=python&time_filter=week&limit=5
# And the interactive API docs (Swagger UI) at:
# http://127.0.0.1:8000/docs 