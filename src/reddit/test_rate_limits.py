
import praw
import time
import os
from dotenv import load_dotenv

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("R_CLIENT_ID"),
    client_secret=os.getenv("R_CLIENT_SECRET"),
    username=os.getenv("R_USERNAME"),
    password=os.getenv("R_PASSWORD"),
    user_agent=os.getenv("R_USER_AGENT")
)

print("Logged in as:", reddit.user.me())

rate_limit = reddit.auth.limits
print("Rate limit info:", rate_limit)
print("Remaining:", rate_limit['remaining'])
print("Used:", rate_limit['used'])
print("Reset in (seconds):", rate_limit['reset_timestamp'] - time.time())
