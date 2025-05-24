#!/usr/bin/env python3
import praw
import json
import sys
from datetime import datetime

# PRAW Authentication (same as api.py)
reddit = praw.Reddit(
    client_id="0STz-aj6UQnhcWIaEViQ1A",
    client_secret="BvDg-ZF4GX_G0x0oqVQGl5rbnRJq9Q",
    user_agent="techbro_cli by /u/Techbro994"
)

# --- Core Reddit fetching logic (from api.py) ---
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

def fetch_subreddit_data_logic(subreddit_name: str, time_filter: str = "month", limit: int = 10):
    try:
        subreddit = reddit.subreddit(subreddit_name)
        # Check if subreddit exists
        subreddit.display_name 
    except Exception as e:
        print(f"Error accessing subreddit {subreddit_name}: {e}")
        sys.exit(1)

    posts_data = []
    try:
        print(f"Fetching top {limit} posts from r/{subreddit_name} (time_filter: {time_filter})...")
        for i, submission in enumerate(subreddit.top(time_filter=time_filter, limit=limit), 1):
            print(f"Processing post {i}/{limit}: {submission.title}")
            post_info = {
                "id": submission.id,
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
        return posts_data
    except Exception as e:
        print(f"Error fetching posts from r/{subreddit_name}: {e}")
        sys.exit(1)

def main(subreddit: str, time_filter: str, limit: int, output_filename: str):

    # Fetch data
    data = fetch_subreddit_data_logic(subreddit, time_filter, limit)
    
    # Prepare output structure
    output_data = {
        "metadata": {
            "subreddit": subreddit,
            "time_filter": time_filter,
            "limit": limit,
            "fetch_timestamp": datetime.now().isoformat(),
            "total_posts": len(data)
        },
        "posts": data
    }
    
    # Save to JSON file
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(data)} posts to {output_filename}")
    except Exception as e:
        print(f"Error saving to file {output_filename}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main("programming", 'month', 2, "test.json") 