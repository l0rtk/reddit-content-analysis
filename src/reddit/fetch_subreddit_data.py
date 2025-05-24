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

def fetch_subreddit_data_logic(subreddit_name: str, time_filter: str, limit: int):
    subreddit = reddit.subreddit(subreddit_name)
    posts_data = []
    for submission in subreddit.top(time_filter=time_filter, limit=limit):
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


def fetch_subreddit_data(subreddit: str, time_filter: str = "month", limit: int = 10):

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
    
    return output_data

if __name__ == "__main__":
    fetch_subreddit_data("programming", 'month', 2) 