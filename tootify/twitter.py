import logging
import re
import urllib
from collections import defaultdict
from typing import Any, TextIO

from tweepy import Client

logger = logging.getLogger(__name__)


from tootify.source import Media, Source, Toot


class TwitterSource(Source):
    def _expand_urls(self, text: str):
        # Find twitter short urls
        urls = re.findall("https://t.co/[0-9a-zA-Z]+", text)
        for url in urls:
            try:
                res = urllib.request.urlopen(url)
                expanded_url = res.geturl()
                text = text.replace(url, expanded_url)
            except:
                logger.error(f"Failed to expand {url}.")
        return text

    def _strip_self_referencing_urls(self, text: str, tweet_id):
        url = f"https://twitter.com/{self.config['username']}/status/{tweet_id}/"
        logger.debug(f"Strip {url}([a-zA-Z0-9]+/)+")
        return re.sub(f"{url}([a-zA-Z0-9]+/)+[a-zA-Z0-9]*", "", text)

    def _expand_handles(self, text: str):
        # Find twitter short urls
        handles = re.findall("(?<=[^0-9a-zA-Z_])@[0-9a-zA-Z_]{1,15}(?=[^0-9a-zA-Z_@]|$)", text)
        familiar_accounts = self.config.get("familiar_accounts", {})
        for handle in handles:
            if handle[1:] in familiar_accounts:
                logger.debug(f"Found {handle} in familiar accounts: {familiar_accounts[handle[1:]]}")
                text = text.replace(handle, f"@{familiar_accounts[handle[1:]]}")
            else:
                text = text.replace(handle, f"{handle}@twitter.com")
        return text

    def tootify(self, tweet, included_media):
        media = []
        if tweet.attachments:
            for media_key in tweet.attachments.get("media_keys", []):
                item = next((item for item in included_media if item.media_key == media_key), None)
                if item:
                    logger.debug(f"Found media {item.url}")
                    media.append(item)
                else:
                    logger.error(f"Could not find attachment with media_key {media_key}!")
                    continue

        replied_to = None
        if tweet.id != tweet.conversation_id:
            replied_to = ([ref.id for ref in tweet.referenced_tweets or [] if ref.type == "replied_to"] or [None])[0]

        logger.debug(f"Clean text: {tweet.text}")
        tweet_text = self._strip_self_referencing_urls(
            self._expand_urls(self._expand_handles(tweet.text)), tweet_id=tweet.id
        )
        return Toot(
            source=self,
            reference=tweet.id,
            status=tweet_text,
            reply_to=replied_to,
            media=[Media(media_item.url, media_item.alt_text) for media_item in media],
        )

    def connect(self):
        self._twitter_client = Client(bearer_token=self.config["bearer_token"])
        self._twitter_user_id = self._twitter_client.get_user(username=self.config["username"]).data.id

    def get_new_posts(self):
        logger.debug(f"Get tweets newer than {self.config['status'].get('last_tweet', None)}")
        new_tweets = self._twitter_client.get_users_tweets(
            id=self._twitter_user_id,
            exclude=["retweets", "replies"],
            tweet_fields=["conversation_id", "referenced_tweets", "attachments"],
            since_id=self.config["status"].get("last_tweet", None),
            expansions=["attachments.media_keys"],
            media_fields=["url", "alt_text", "variants"],
        )
        if new_tweets.data:
            self.config["status"]["last_tweet"] = max(tweet.id for tweet in new_tweets.data)
        included_media = new_tweets.includes.get("media", [])
        return [self.tootify(tweet, included_media) for tweet in sorted(new_tweets.data, key=lambda tweet: tweet.id)]
