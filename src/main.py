from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from src.reddit.tasks import fetch_subreddit_data_task
from src.celery_app import celery_app
import redis

app = FastAPI(title="Reddit Content Analysis API", version="1.0.0")

# Redis client for checking if task IDs exist
redis_client = redis.Redis.from_url("redis://localhost:6379/0")

# Pydantic models for request/response
class FetchRequest(BaseModel):
    subreddit: str
    time_filter: str = "month"
    limit: int = 10

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

@app.get("/")
async def root():
    return {"message": "Reddit Content Analysis API", "status": "running"}

@app.post("/fetch-subreddit-data", response_model=TaskResponse)
async def fetch_subreddit_data_endpoint(request: FetchRequest):
    """
    Queue a task to fetch subreddit data asynchronously.
    Returns a task ID that can be used to check status and get results.
    """
    try:
        # Queue the Celery task
        task = fetch_subreddit_data_task.delay(
            subreddit=request.subreddit,
            time_filter=request.time_filter,
            limit=request.limit
        )
        
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Task queued successfully. Fetching {request.limit} posts from r/{request.subreddit}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")

def task_exists_in_redis(task_id: str) -> bool:
    """Check if a task ID exists in Redis backend."""
    try:
        # Check if task result exists in Redis
        result_key = f"celery-task-meta-{task_id}"
        return redis_client.exists(result_key) > 0
    except:
        return False

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check the status of a queued task.
    """
    try:
        task_result = celery_app.AsyncResult(task_id)
        
        # Handle revoked tasks
        if task_result.state == "REVOKED":
            return {
                "task_id": task_id,
                "state": task_result.state,
                "status": "Task was cancelled/revoked",
                "progress": {"current": 0, "total": 0}
            }
        
        # Check if task actually exists
        if task_result.state == "PENDING":
            # For PENDING state, we need to distinguish between:
            # 1. Actually pending task (exists in queue/Redis)
            # 2. Non-existent task ID
            
            if not task_exists_in_redis(task_id):
                # Also check if it might be in the queue
                active_tasks = celery_app.control.inspect().active()
                scheduled_tasks = celery_app.control.inspect().scheduled()
                reserved_tasks = celery_app.control.inspect().reserved()
                
                task_found = False
                if active_tasks:
                    for worker_tasks in active_tasks.values():
                        if any(task.get('id') == task_id for task in worker_tasks):
                            task_found = True
                            break
                
                if not task_found and scheduled_tasks:
                    for worker_tasks in scheduled_tasks.values():
                        if any(task.get('id') == task_id for task in worker_tasks):
                            task_found = True
                            break
                            
                if not task_found and reserved_tasks:
                    for worker_tasks in reserved_tasks.values():
                        if any(task.get('id') == task_id for task in worker_tasks):
                            task_found = True
                            break
                
                if not task_found:
                    raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
            
            return {
                "task_id": task_id,
                "state": task_result.state,
                "status": "Task is pending in queue...",
                "progress": {"current": 0, "total": 0}
            }
        elif task_result.state == "PROGRESS":
            # Safely handle task info
            info = task_result.info or {}
            return {
                "task_id": task_id,
                "state": task_result.state,
                "status": info.get("status", "Processing..."),
                "progress": {
                    "current": info.get("current", 0),
                    "total": info.get("total", 0)
                }
            }
        elif task_result.state == "SUCCESS":
            return {
                "task_id": task_id,
                "state": task_result.state,
                "status": "Task completed successfully",
                "result": task_result.result
            }
        else:  # FAILURE or other states
            # Safely handle task info for failed tasks
            info = task_result.info or {}
            if hasattr(info, 'get'):
                status = info.get("status", "Task failed")
                error = info.get("error", str(info))
            else:
                status = "Task failed"
                error = str(info)
            
            return {
                "task_id": task_id,
                "state": task_result.state,
                "status": status,
                "error": error
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@app.get("/task-result/{task_id}")
async def get_task_result(task_id: str):
    """
    Get the result of a completed task.
    """
    try:
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.state == "PENDING":
            if not task_exists_in_redis(task_id):
                raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
            raise HTTPException(status_code=202, detail="Task is still pending")
        elif task_result.state == "PROGRESS":
            raise HTTPException(status_code=202, detail="Task is still in progress")
        elif task_result.state == "SUCCESS":
            return {
                "task_id": task_id,
                "state": task_result.state,
                "result": task_result.result
            }
        else:  # FAILURE
            raise HTTPException(
                status_code=500, 
                detail=f"Task failed: {task_result.info.get('error', str(task_result.info))}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task result: {str(e)}")

@app.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a queued or running task.
    """
    try:
        # Check if task exists first
        task_result = celery_app.AsyncResult(task_id)
        if task_result.state == "PENDING" and not task_exists_in_redis(task_id):
            raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
            
        celery_app.control.revoke(task_id, terminate=True)
        return {"task_id": task_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

@app.get("/worker-status")
async def get_worker_status():
    """
    Get the status of Celery workers.
    """
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        if not stats:
            return {
                "workers_online": 0,
                "status": "No workers found. Make sure Celery worker is running.",
                "active_tasks": 0
            }
        
        active_task_count = sum(len(tasks) for tasks in (active or {}).values())
        
        return {
            "workers_online": len(stats),
            "workers": list(stats.keys()),
            "active_tasks": active_task_count,
            "status": "Workers are running normally"
        }
    except Exception as e:
        return {
            "workers_online": 0,
            "status": f"Error checking workers: {str(e)}",
            "active_tasks": 0
        }

@app.get("/tasks")
async def get_all_tasks():
    """
    Get information about all tasks (active, scheduled, reserved, and recent results).
    """
    try:
        inspect = celery_app.control.inspect()
        
        # Get active, scheduled, and reserved tasks
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}
        reserved_tasks = inspect.reserved() or {}
        
        # Collect all task information
        all_tasks = []
        
        # Process active tasks
        for worker, tasks in active_tasks.items():
            for task in tasks:
                all_tasks.append({
                    "task_id": task.get("id"),
                    "name": task.get("name"),
                    "state": "ACTIVE",
                    "worker": worker,
                    "args": task.get("args", []),
                    "kwargs": task.get("kwargs", {}),
                    "time_start": task.get("time_start")
                })
        
        # Process scheduled tasks
        for worker, tasks in scheduled_tasks.items():
            for task in tasks:
                all_tasks.append({
                    "task_id": task.get("id"),
                    "name": task.get("name"),
                    "state": "SCHEDULED",
                    "worker": worker,
                    "args": task.get("args", []),
                    "kwargs": task.get("kwargs", {}),
                    "eta": task.get("eta")
                })
        
        # Process reserved tasks
        for worker, tasks in reserved_tasks.items():
            for task in tasks:
                all_tasks.append({
                    "task_id": task.get("id"),
                    "name": task.get("name"),
                    "state": "RESERVED",
                    "worker": worker,
                    "args": task.get("args", []),
                    "kwargs": task.get("kwargs", {})
                })
        
        # Get recent task results from Redis
        try:
            redis_keys = redis_client.keys("celery-task-meta-*")
            for key in redis_keys[:50]:  # Limit to 50 recent results
                task_id = key.decode().replace("celery-task-meta-", "")
                task_result = celery_app.AsyncResult(task_id)
                
                # Skip if already in active/scheduled/reserved
                if any(t["task_id"] == task_id for t in all_tasks):
                    continue
                
                all_tasks.append({
                    "task_id": task_id,
                    "name": "fetch_subreddit_data_task",  # Our main task
                    "state": task_result.state,
                    "worker": "completed",
                    "result_available": task_result.state in ["SUCCESS", "FAILURE"]
                })
        except Exception as e:
            print(f"Error getting Redis task results: {e}")
        
        return {
            "total_tasks": len(all_tasks),
            "active_count": len([t for t in all_tasks if t["state"] == "ACTIVE"]),
            "scheduled_count": len([t for t in all_tasks if t["state"] == "SCHEDULED"]),
            "reserved_count": len([t for t in all_tasks if t["state"] == "RESERVED"]),
            "completed_count": len([t for t in all_tasks if t["state"] in ["SUCCESS", "FAILURE"]]),
            "tasks": all_tasks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)