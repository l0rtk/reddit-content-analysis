from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
import tiktoken

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["techbro"]
collection = db["reddit_posts"]


def count_tokens(text, model="gpt-4"):
    """
    Count the number of tokens in a text string for a given model.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # If model not found, use cl100k_base (GPT-4 encoding)
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def create_analysis_prompt(posts_data):
    """
    Create a well-formatted prompt for LLM analysis of Reddit posts and comments.
    """
    prompt = """You are an expert social media analyst. Please analyze the following Reddit posts and comments from the r/europe subreddit to identify key problems, issues, concerns, and trends being discussed.

ANALYSIS INSTRUCTIONS:
1. Identify the main problems or issues mentioned in posts and comments
2. Categorize these problems (e.g., political, economic, social, environmental, etc.)
3. Note the sentiment and urgency level of discussions
4. Highlight any recurring themes or patterns
5. Summarize the most significant concerns raised by the community

FORMAT YOUR RESPONSE AS:
- **Main Problems Identified:** (numbered list)
- **Problem Categories:** (with examples)
- **Sentiment Analysis:** (overall tone and urgency)
- **Recurring Themes:** (patterns you notice)
- **Key Concerns Summary:** (most important issues)

REDDIT DATA TO ANALYZE:

"""

    post_count = 0
    for post in posts_data:
        post_count += 1
        prompt += f"\n=== POST #{post_count} ===\n"
        prompt += f"**Title:** {post.get('title', 'No title')}\n"
        
        # Handle post body
        body = post.get('body', '') or post.get('selftext', '')
        if body and body.strip() and body != '[deleted]' and body != '[removed]':
            prompt += f"**Content:** {body}\n"
        
        prompt += f"**Subreddit:** r/{post.get('subreddit', 'unknown')}\n"
        prompt += f"**Score:** {post.get('score', 'N/A')}\n"
        
        # Add comments if they exist
        comments = post.get('comments', [])
        if comments:
            prompt += f"**Comments ({len(comments)}):**\n"
            for i, comment in enumerate(comments[:10], 1):  # Limit to first 10 comments
                comment_body = comment.get('body', '')
                if comment_body and comment_body.strip() and comment_body not in ['[deleted]', '[removed]']:
                    prompt += f"  {i}. {comment_body}\n"
        
        prompt += "\n" + "-" * 80 + "\n"
    
    prompt += f"\n\nTOTAL POSTS ANALYZED: {post_count}\n"
    prompt += "\nPlease provide your comprehensive analysis based on the above data."
    
    return prompt


def main():
    """
    Main function to run the analysis.
    """
    print("Fetching posts from r/europe...")
    posts = list(collection.find({"subreddit": "europe"}))
    
    if not posts:
        print("No posts found in the database for r/europe")
        return
    
    print(f"Found {len(posts)} posts")
    
    # Save raw data to JSON
    posts_json = json.dumps(posts, default=str, indent=2)
    with open("posts.json", "w", encoding='utf-8') as f:
        f.write(posts_json)
    print("Raw data saved to posts.json")
    
    # Create LLM analysis prompt
    print("Creating LLM analysis prompt...")
    analysis_prompt = create_analysis_prompt(posts)
    
    # Save prompt to file
    with open("analysis_prompt.txt", "w", encoding='utf-8') as f:
        f.write(analysis_prompt)
    
    # Calculate token count
    token_count = count_tokens(analysis_prompt)
    
    print(f"\n{'='*60}")
    print(f"PROMPT STATISTICS:")
    print(f"{'='*60}")
    print(f"Total characters: {len(analysis_prompt):,}")
    print(f"Estimated tokens (GPT-4): {token_count:,}")
    print(f"Estimated cost (GPT-4 input): ${(token_count * 0.03 / 1000):.4f}")
    print(f"Estimated cost (GPT-4o input): ${(token_count * 0.005 / 1000):.4f}")
    print(f"Prompt saved to: analysis_prompt.txt")
    print(f"{'='*60}")
    
    # Show preview of prompt
    print(f"\nPROMPT PREVIEW (first 500 characters):")
    print("-" * 50)
    print(analysis_prompt[:500] + "..." if len(analysis_prompt) > 500 else analysis_prompt)
    print("-" * 50)


if __name__ == "__main__":
    main()