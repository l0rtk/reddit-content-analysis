from reddit.fetch_subreddit_data import fetch_subreddit_data
from pprint import pprint

data = fetch_subreddit_data("programming", 'day', 2)

pprint(data)