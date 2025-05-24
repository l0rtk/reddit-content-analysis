# Reddit Content Analysis API

An asynchronous Reddit content analysis API built with FastAPI, Celery, and Redis that allows you to fetch subreddit data without blocking the API.

## Features

- **Asynchronous Processing**: Queue Reddit data fetching tasks using Celery
- **Non-blocking API**: API remains responsive while processing tasks in the background
- **Task Management**: Check task status, get results, and cancel tasks
- **Progress Tracking**: Monitor task progress in real-time
- **Data Persistence**: Store fetched data in MongoDB
- **Error Handling**: Comprehensive error handling and reporting

## Architecture

- **FastAPI**: Web API framework
- **Celery**: Distributed task queue for background processing
- **Redis**: Message broker and result backend for Celery
- **MongoDB**: Database for storing Reddit data
- **PRAW**: Python Reddit API Wrapper for Reddit data fetching

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install and Start Redis

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**

```bash
brew install redis
brew services start redis
```

**Docker:**

```bash
docker run -d -p 6379:6379 redis:alpine
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
# Reddit API Configuration
R_CLIENT_ID=your_reddit_client_id
R_CLIENT_SECRET=your_reddit_client_secret
R_USER_AGENT=your_user_agent

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 4. Start the Services

**Terminal 1: Start the Celery Worker**

```bash
python start_celery.py
```

_Or manually:_

```bash
celery -A src.celery_app worker --loglevel=info --concurrency=2
```

**Terminal 2: Start the FastAPI Server**

```bash
python src/main.py
```

_Or:_

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Usage

### 1. Queue a Data Fetching Task

**POST** `/fetch-subreddit-data`

```json
{
  "subreddit": "programming",
  "time_filter": "month",
  "limit": 10
}
```

**Response:**

```json
{
  "task_id": "b5e8c8b2-1a2b-4c5d-8e9f-1a2b3c4d5e6f",
  "status": "queued",
  "message": "Task queued successfully. Fetching 10 posts from r/programming"
}
```

### 2. Check Task Status

**GET** `/task-status/{task_id}`

**Response (In Progress):**

```json
{
  "task_id": "b5e8c8b2-1a2b-4c5d-8e9f-1a2b3c4d5e6f",
  "state": "PROGRESS",
  "status": "Starting to fetch data from r/programming...",
  "progress": {
    "current": 3,
    "total": 10
  }
}
```

**Response (Completed):**

```json
{
  "task_id": "b5e8c8b2-1a2b-4c5d-8e9f-1a2b3c4d5e6f",
  "state": "SUCCESS",
  "status": "Task completed successfully",
  "result": {
    "subreddit": "programming",
    "time_filter": "month",
    "limit": 10,
    "total_posts": 10,
    "save_status": {
      "inserted": 8,
      "updated": 2,
      "failed": 0
    }
  }
}
```

### 3. Get Task Result

**GET** `/task-result/{task_id}`

Returns the complete result of a finished task.

### 4. Cancel a Task

**DELETE** `/task/{task_id}`

Cancels a queued or running task.

## Example Usage with curl

```bash
# 1. Queue a task
curl -X POST "http://localhost:8000/fetch-subreddit-data" \
     -H "Content-Type: application/json" \
     -d '{"subreddit": "programming", "time_filter": "month", "limit": 5}'

# 2. Check status (replace with actual task_id)
curl "http://localhost:8000/task-status/your-task-id-here"

# 3. Get result when completed
curl "http://localhost:8000/task-result/your-task-id-here"
```

## Example Usage with Python

```python
import requests
import time

# Queue a task
response = requests.post(
    "http://localhost:8000/fetch-subreddit-data",
    json={
        "subreddit": "programming",
        "time_filter": "month",
        "limit": 5
    }
)
task_data = response.json()
task_id = task_data["task_id"]

# Poll for completion
while True:
    status_response = requests.get(f"http://localhost:8000/task-status/{task_id}")
    status_data = status_response.json()

    print(f"Status: {status_data['state']} - {status_data['status']}")

    if status_data["state"] == "SUCCESS":
        result_response = requests.get(f"http://localhost:8000/task-result/{task_id}")
        result = result_response.json()
        print("Task completed:", result)
        break
    elif status_data["state"] == "FAILURE":
        print("Task failed:", status_data.get("error"))
        break

    time.sleep(2)  # Wait 2 seconds before checking again
```

## Monitoring

### Celery Monitoring with Flower

Install Flower for web-based monitoring:

```bash
pip install flower
flower -A src.celery_app --port=5555
```

Access the monitoring interface at: `http://localhost:5555`

### Redis Monitoring

```bash
redis-cli monitor
```

## API Documentation

Once the server is running, visit:

- **Interactive API docs**: `http://localhost:8000/docs`
- **ReDoc documentation**: `http://localhost:8000/redoc`

## Benefits of Async Architecture

1. **Non-blocking**: API responds immediately, queuing tasks for background processing
2. **Scalable**: Multiple workers can process tasks concurrently
3. **Reliable**: Failed tasks can be retried automatically
4. **Monitorable**: Real-time task status and progress tracking
5. **Cancellable**: Tasks can be cancelled if needed

## Troubleshooting

### Redis Connection Issues

```bash
# Check if Redis is running
redis-cli ping

# Should return: PONG
```

### Celery Worker Issues

```bash
# Check if worker is receiving tasks
celery -A src.celery_app inspect active

# Check worker status
celery -A src.celery_app inspect stats
```

### Task Not Processing

1. Ensure Redis is running
2. Ensure Celery worker is running
3. Check environment variables are set correctly
4. Check task logs for errors
