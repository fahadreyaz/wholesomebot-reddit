import praw
import os
from dotenv import load_dotenv
import requests
import re
import collections
import time
import json

# Open the text file containing the words
with open('wholesomewords.txt', 'r') as f:
    # Initialize an empty set
    wholesome_set = set()

    # Read the file line by line
    for line in f:
        # Split the line into words and add them to the set
        words = line.strip().split()
        wholesome_set.update(words)

load_dotenv()

# Authenticate with Reddit API
reddit = praw.Reddit(
    client_id=os.environ['REDDIT_CLIENT_ID'],
    client_secret=os.environ['REDDIT_CLIENT_SECRET'],
    username=os.environ['REDDIT_USERNAME'],
    password=os.environ['REDDIT_PASSWORD'],
    user_agent=os.environ['REDDIT_USER_AGENT']
)

# Cache dictionary for API responses
cache = {}

# Subreddit and trigger phrase
subreddit_names = "flatapartmentcheck+IndianTeenagers+JEENEETards"
trigger_phrases = ['!wholesomenesscheck',
                   '!wholesomecheck', '!uwucheck', '!uwucheckself']

# Bot username
bot_username = 'wholesome-counter'

# Listen for comments in subreddits
comments_to_reply = []
for subreddit_name in subreddit_names:
    subreddit = reddit.subreddit(
        "flatapartmentcheck+IndianTeenagers+JEENEETards")
    for incoming_comment in subreddit.stream.comments(skip_existing=True):
        # Check if comment contains any of the trigger phrases
        if any(phrase in incoming_comment.body.lower() for phrase in trigger_phrases):
            # Check if trigger phrase is !uwucheckself and set username
            if '!uwucheckself' in incoming_comment.body.lower():
                user_name = incoming_comment.author.name
            else:
                # Get parent comment and author name
                if '[self]' in incoming_comment.body:
                    parent_comment = incoming_comment
                    user_name = incoming_comment.author.name
                else:
                    parent_comment = incoming_comment.parent()
                    user_name = incoming_comment.parent().author.name

            # Check if bot is being called
            if user_name.lower() == bot_username.lower():
                # Construct reply text without times_called
                reply_text = 'This is the Reddit wholesome counter bot. Leave a comment with a username to get their wholesome count!'
                # Add comment to list of comments to reply to
                comments_to_reply.append((incoming_comment, reply_text))

            else:
                # Get top 500 comments of user
                # Check if cached response exists for user
                # 604800 seconds = 1 week
                if user_name in cache and 'timestamp' in cache[user_name] and time.time() - cache[user_name]['timestamp'] <= 604800:
                    api_comments = cache[user_name]['response']
                else:
                    # Make API request for user comments
                    url = f'https://api.pushshift.io/reddit/comment/search?author={user_name}&size=250'
                    retries = 4
                    for i in range(retries):
                        try:
                            with requests.Session() as session:
                                response = session.get(url)
                                # Add a sleep of 7 seconds after each API request
                                time.sleep(7)
                            api_comments = response.json()['data']
                            break
                        # Add 3 retries
                        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                            if i == retries - 1:
                                print(
                                    f"Error occurred while making the API request: {e}")
                                api_comments = []
                            else:
                                print(
                                    f"Retrying API request. Attempt {i+1} of {retries}.")
                                time.sleep(10)

                    # Store response in cache
                    cache[user_name] = {
                        'response': api_comments,
                        'timestamp': time.time()
                    }

                # Initialize wholesome count
                wholesome_count = 0
                word_count = collections.Counter()

                # Analyze comments for wholesome words
                for comment in api_comments:
                    # Clean and tokenize comment
                    comment_text = re.sub(
                        r'[^\w\s]', '', comment['body']).lower()
                    comment_tokens = comment_text.split()

                    # Count wholesome occurrences
                    for token in comment_tokens:
                        if token in wholesome_set:
                            wholesome_count += 1
                            word_count[token] += 1

                # Construct table of wholesome words and counts
                table_rows = [
                    f"| {word} | {count} |" for word, count in word_count.items()
                ]
                table = "\n".join(table_rows)

                # Construct reply text with wholesome count and table
                if '!uwucheckself' in incoming_comment.body.lower():
                    reply_text = f'The number of wholesome occurrences in your recent 500 comments is {wholesome_count}.\n\n| Word | Count |\n| --- | --- |\n{table} |\n\nStay wholesome!  \n\nWanna do something even more wholesome? Leave a \u2B50 at the [GitHub repository](https://github.com/MeowthyVoyager/reddit-wholesome-counter).'
                else:
                    reply_text = f'The number of wholesome occurrences in the recent 500 comments of u/{user_name} is {wholesome_count}.\n\n| Word | Count |\n| --- | --- |\n{table} |\n\nStay wholesome!  \n\nWanna do something even more wholesome? Leave a \u2B50 at the [GitHub repository](https://github.com/MeowthyVoyager/reddit-wholesome-counter).'

                # Add comment to list of comments to reply to
                comments_to_reply.append((incoming_comment, reply_text))

                # Call reply() on the comment immediately
                incoming_comment.reply(reply_text)
