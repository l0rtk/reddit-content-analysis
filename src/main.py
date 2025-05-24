from fastapi import FastAPI
import uvicorn
from src.reddit.fetch_subreddit_data import fetch_subreddit_data

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/fetch-subreddit-data")
async def fetch_subreddit_data_endpoint(subreddit: str, time_filter: str = "month", limit: int = 10):
    print(subreddit, time_filter, limit)
    data = fetch_subreddit_data(subreddit, time_filter, limit)
    return data


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)