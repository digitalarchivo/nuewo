# The vast majority of this code was written by Mistral-large and 
# is therefore public domain in the United States.
# But just in case, this script is public domain as set out in the 
# Creative Commons Zero 1.0 Universal Public Domain Notice
# https://creativecommons.org/publicdomain/zero/1.0/

import argparse
import json
from datetime import datetime
import html

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate an HTML page with all tweets.")
    parser.add_argument("tweets_file", help="Path to the tweets.js file.")
    parser.add_argument("note_tweets_file", help="Path to the note-tweets.js file.")
    parser.add_argument("name", help="Your name.")
    parser.add_argument("twitter_username", help="Your Twitter username.")
    parser.add_argument("--media-folder", help="Path to the folder containing tweet media.")
    parser.add_argument("--exclude-retweets", action="store_true", help="Exclude retweets from the output.")
    return parser.parse_args()

def extract_json_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        start_index = content.find('[')
        json_data = content[start_index:]
        return json.loads(json_data)

def parse_tweet_time(tweet_time):
    tweet_datetime = datetime.strptime(tweet_time, '%a %b %d %H:%M:%S +0000 %Y')
    return tweet_datetime

def parse_note_tweet_time(note_tweet_time):
    note_tweet_datetime = datetime.strptime(note_tweet_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    return note_tweet_datetime

def convert_newlines_to_br(text):
    return text.replace('\n', '<br>')

def replace_urls(text, urls):
    for url in urls:
        if 'url' in url and 'expanded_url' in url:
            text = text.replace(url['url'], f'<a href="{url["expanded_url"]}" target="_blank">{url["display_url"]}</a>')
    return text

def filter_edited_tweets(tweets):
    tweet_map = {}
    for tweet in tweets:
        tweet_data = tweet['tweet']
        tweet_id = tweet_data['id_str']

        edit_ids = []
        if 'edit_info' in tweet_data:
            if 'initial' in tweet_data['edit_info']:
                edit_ids = tweet_data['edit_info']['initial']['editTweetIds']
            elif 'edit' in tweet_data['edit_info']:
                edit_ids = tweet_data['edit_info']['edit']['editControlInitial']['editTweetIds']

        if len(edit_ids) > 1:
            max_edit_id = max(edit_ids, key=int)
            if max_edit_id == tweet_id:
                tweet_map[tweet_id] = tweet
            else:
                continue
        else:
            tweet_map[tweet_id] = tweet

    return list(tweet_map.values())

def create_html(tweets, note_tweets, name, twitter_username, exclude_retweets, media_folder):
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{html.escape(name)}'s Tweets</title>
        <style>
            body {{
                width: 600px;
                margin: 0 auto;
                font-family: Helvetica, Arial, sans-serif;
            }}
            .tweet {{
                border: 1px solid #ccc;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 5px;
            }}
            .tweet-header {{
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .tweet-link {{
                text-decoration: none;
            }}
            .tweet-link:hover {{
                opacity: 50%;
            }}
            .tweet-time {{
                color: #555;
                margin-left: 10px;
            }}
            .tweet-stats {{
                color: #555;
                margin-top: 10px;
            }}
            .tweet-media {{
                max-width: 100%;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>{html.escape(name)}'s Tweets</h1>
    """

    tweets = filter_edited_tweets(tweets)
    tweets.sort(key=lambda tweet: parse_tweet_time(tweet['tweet']['created_at']))

    for tweet in tweets:
        tweet_data = tweet['tweet']
        tweet_text = tweet_data['full_text']

        if exclude_retweets and tweet_text.startswith("RT @"):
            continue

        tweet_time = parse_tweet_time(tweet_data['created_at']).strftime('%Y-%m-%d %H:%M UTC')
        tweet_timestamp = int(parse_tweet_time(tweet_data['created_at']).timestamp())
        tweet_id = tweet_data['id_str']
        tweet_url = f"https://twitter.com/{twitter_username}/status/{tweet_id}"

        if '…' in tweet_text:
            matching_note_tweet = next(
                (note for note in note_tweets if parse_note_tweet_time(note['noteTweet']['createdAt']) == parse_tweet_time(tweet_data['created_at'])),
                None
            )
            if matching_note_tweet:
                note_text = matching_note_tweet['noteTweet']['core']['text']
                mentions = tweet_data['entities'].get('user_mentions', [])
                mention_handles = ' '.join([f"@{mention['screen_name']}" for mention in mentions])
                note_urls = matching_note_tweet['noteTweet']['core'].get('urls', [])
                note_text = replace_urls(note_text, note_urls)
                tweet_text = f"{mention_handles} {note_text}"

        tweet_urls = tweet_data['entities'].get('urls', [])
        tweet_text = replace_urls(tweet_text, tweet_urls)
        tweet_text = convert_newlines_to_br(tweet_text)

        favorite_count = tweet_data['favorite_count']
        retweet_count = tweet_data['retweet_count']

        html_content += f"""
        <div class="tweet">
            <div class="tweet-header" id={tweet_timestamp}>
                <a class="tweet-link" href="#{tweet_timestamp}">🔗</a>
                {html.escape(name)}
                <span class="tweet-time">
                    <a href="{tweet_url}">{tweet_time}</a>
                </span>
            </div>
            <p>{tweet_text}</p>
        """

        # Add media content if available
        if media_folder and 'extended_entities' in tweet_data and 'media' in tweet_data['extended_entities']:
            for media in tweet_data['extended_entities']['media']:
                if media['type'] == 'photo':
                    media_id = media['media_url_https'].split('/')[-1]
                    media_url = f"{media_folder}/{tweet_data['id_str']}-{media_id}"
                    html_content += f'<img class="tweet-media" src="{media_url}" alt="Tweet media">'

        html_content += f"""
            <div class="tweet-stats">
                Likes: {favorite_count} | Retweets: {retweet_count}
            </div>
        </div>
        """

    html_content += """<p>Want your own single page Twitter archive? <a href="https://gist.github.com/JD-P/fc473872bbff4b48b5235cbe4aaeba1d">Modify this script</a>."""

    html_content += """<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><span property="dct:title">Twitter Archive</span> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://jdpressman.com/">John David Pressman</a> is marked with <a href="https://creativecommons.org/publicdomain/zero/1.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">CC0 1.0<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/zero.svg?ref=chooser-v1" alt=""></a></p>"""

    html_content += """
    </body>
    </html>
    """

    return html_content

def main():
    args = parse_arguments()
    tweets = extract_json_from_file(args.tweets_file)
    note_tweets = extract_json_from_file(args.note_tweets_file)
    html_content = create_html(tweets, note_tweets, args.name, args.twitter_username, args.exclude_retweets, args.media_folder)

    with open("tweets.html", "w", encoding='utf-8') as file:
        file.write(html_content)

    print("HTML file 'tweets.html' has been created.")

if __name__ == "__main__":
    main()
