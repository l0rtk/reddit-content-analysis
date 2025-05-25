# Reddit Content Analysis

This is a Reddit data fetcher that runs in the background so your API doesn't get stuck waiting for Reddit to respond. It uses Celery to handle the heavy lifting and stores everything in MongoDB.

## What it does

Fetches Reddit posts and comments from any subreddit you want. The API queues up the work and you can check on progress or get results when it's done. No more waiting around for Reddit's API to finish.

## Quick start with Docker

This is the easiest way to get everything running. You just need Docker and your Reddit API credentials.

First, copy your Reddit API credentials:

```bash
cp .env-example .env
```

Edit the .env file with your Reddit API stuff:

```env
R_CLIENT_ID=your_reddit_client_id
R_CLIENT_SECRET=your_reddit_client_secret
R_USERNAME=your_reddit_username
R_PASSWORD=your_reddit_password
R_USER_AGENT=your_user_agent
```

Then start everything:

```bash
docker-compose up -d
```

That's it. The API will be running at http://localhost:8000 and everything else (Redis, MongoDB, Celery worker) is handled automatically.

To see what's happening:

```bash
docker-compose logs -f
```

To stop everything:

```bash
docker-compose down
```

## Manual setup (if you don't want Docker)

You'll need Redis running for the task queue, MongoDB for storing data, and Reddit API credentials. The whole thing is built with FastAPI and Celery.

First install everything:

```bash
pip install -r requirements.txt
```

Get Redis running. On Ubuntu that's:

```bash
sudo apt install redis-server
sudo systemctl start redis-server
```

On Mac with Homebrew:

```bash
brew install redis
brew services start redis
```

Make a .env file with your Reddit API stuff:

```env
R_CLIENT_ID=your_reddit_client_id
R_CLIENT_SECRET=your_reddit_client_secret
R_USERNAME=your_reddit_username
R_PASSWORD=your_reddit_password
R_USER_AGENT=your_user_agent
MONGODB_URI=mongodb://localhost:27017
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

Start the worker in one terminal:

```bash
python start_celery.py
```

Start the API in another terminal:

```bash
python src/main.py
```

## How to use it

Queue up a job by posting to /fetch-subreddit-data:

```bash
curl -X POST "http://localhost:8000/fetch-subreddit-data" \
     -H "Content-Type: application/json" \
     -d '{"subreddit": "programming", "time_filter": "month", "limit": 10}'
```

You'll get back a task ID. Use that to check on progress:

```bash
curl "http://localhost:8000/task-status/your-task-id"
```

When it's done you can get the full results:

```bash
curl "http://localhost:8000/task-result/your-task-id"
```

## Rate limiting

The fetcher watches Reddit's rate limits and will wait if you're getting close to the limit. It only fetches top-level comments to keep things fast and avoid hitting document size limits in MongoDB.

## API endpoints

- POST /fetch-subreddit-data - Queue a new fetch job
- GET /task-status/{task_id} - Check how a job is doing
- GET /task-result/{task_id} - Get results when done
- DELETE /task/{task_id} - Cancel a job
- GET /worker-status - See if workers are running

The API docs are at http://localhost:8000/docs when you're running it.

## What gets stored

Each Reddit post becomes a document in MongoDB with the title, score, author, comments, and metadata about when it was fetched. Comments include the text, author, score, and timestamp.

## Troubleshooting

If you're using Docker and something's not working, check the logs:

```bash
docker-compose logs api
docker-compose logs worker
```

If tasks aren't running, make sure Redis is up and the Celery worker is started. If you're getting rate limited, the fetcher will wait automatically but you might want to reduce the number of posts you're fetching at once.

## Scaling

Want more workers? Just scale them up:

```bash
docker-compose up -d --scale worker=3
```

This will give you 3 worker containers processing jobs in parallel.
