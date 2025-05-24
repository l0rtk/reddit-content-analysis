from src.celery_app import celery_app
from src.reddit.fetch_subreddit_data import fetch_and_save_subreddit_data


@celery_app.task(bind=True, name="fetch_subreddit_data_task")
def fetch_subreddit_data_task(self, subreddit: str, time_filter: str = "month", limit: int = 10):
    """
    Celery task to fetch and save subreddit data asynchronously.
    
    Args:
        subreddit: Name of the subreddit to fetch data from
        time_filter: Time filter for posts (hour, day, week, month, year, all)
        limit: Number of posts to fetch
    
    Returns:
        Dict containing the fetch results and metadata
    """
    try:
        # Update task state to indicate processing has started
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": limit,
                "status": f"Starting to fetch data from r/{subreddit}..."
            }
        )
        
        # Fetch and save the data
        result = fetch_and_save_subreddit_data(subreddit, time_filter, limit)
        
        # Update final state
        self.update_state(
            state="SUCCESS",
            meta={
                "current": result.get("total_posts", 0),
                "total": limit,
                "status": "Data fetching completed successfully",
                "result": result
            }
        )
        
        return result
        
    except Exception as exc:
        # Update state on failure
        self.update_state(
            state="FAILURE",
            meta={
                "current": 0,
                "total": limit,
                "status": f"Error occurred: {str(exc)}",
                "error": str(exc)
            }
        )
        # Re-raise the exception to mark task as failed
        raise exc 