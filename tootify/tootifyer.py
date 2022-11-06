import logging
from typing import TextIO, Any
from unittest import result
import yaml
import urllib
import re
from collections import defaultdict
from pathlib import Path
from tweepy import Client
from mastodon import Mastodon

logger = logging.getLogger(__name__)


class Tootifyer:
    def __init__(self, config: Path) -> None:
        self._status_path = config
        self._read_status()

    def _read_status(self) -> None:
        self._status = yaml.load(self._status_path.open("r"), yaml.SafeLoader)

    def _write_status(self) -> None:
        yaml.dump(self._status, self._status_path.open("w"), yaml.dumper.SafeDumper)

    def _get_new_tweets(self):
        result = self._twitter_client.get_users_tweets(
            id=self._twitter_user_id,
            exclude=["retweets", "replies"],
            tweet_fields=["conversation_id", "referenced_tweets"],
            since_id=self._status["twitter"].get("last_id", None),
        )
        return result.data

    def _get_conversations(self, tweets):
        conversations = defaultdict(list)
        for tweet in tweets:
            conversations[tweet.conversation_id].append(tweet)
        return dict(conversations)

    def _expand_urls(text: str):
        # Find twitter short urls
        urls = re.findall("https://t.co/([0-9a-zA-Z]+)", text)
        for url in urls:
            try:
                res = urllib.request.urlopen(url)
                expanded_url = res.geturl()
                text = text.replace(url, expanded_url)
            except:
                pass
        return text

    def connect(self):
        logger.debug("connect to Mastodon")
        self._mastodon_api = Mastodon(
            client_id=self._status["mastodon"]["client_id"],
            client_secret=self._status["mastodon"]["client_secret"],
            access_token=self._status["mastodon"]["access_token"],
            api_base_url=f"https://{self._status['mastodon']['instance']}",
        )
        check = self._mastodon_api.account_verify_credentials()
        if check.get("error"):
            logger.error(check.get("error connecting to Mastodon"))
        else:
            username = str(check["username"])
            logger.info(f"connected on @{username}@{self._status['mastodon']['instance']}")
        logger.debug("connect to twitter")
        self._twitter_client = Client(bearer_token=self._status["twitter"]["bearer_token"])
        self._twitter_user_id = self._twitter_client.get_user(username=self._status["twitter"]["username"]).data.id

    def toot_new_tweets(self, dry_run: bool = False):
        tweets = self._get_new_tweets()
        if tweets:
            conversations = self._get_conversations(tweets)

            last_id = self._status["twitter"].get("last_id", None)

            for conversation in conversations.values():
                references = {}
                for tweet in sorted(conversation, key=lambda tweet: tweet.id):
                    if tweet.id == tweet.conversation_id:
                        if dry_run:
                            logger.info(f"Skip tweet {tweet.id}")
                        else:
                            logger.debug(f"Toot tweet {tweet.id}")
                            toot = self._mastodon_api.toot(self._expand_urls(tweet.text))
                    else:
                        replied_to = (
                            [ref.id for ref in tweet.referenced_tweets or [] if ref.type == "replied_to"] or [None]
                        )[0]
                        if replied_to in references:
                            if dry_run:
                                logger.info(f"Skip reply {tweet.id} to {replied_to}")
                            else:
                                logger.debug(f"Toot reply {tweet.id} to {replied_to}")
                                toot = self._mastodon_api.status_post(
                                    self._expand_urls(tweet.text), in_reply_to_id=references[replied_to]
                                )
                        else:
                            logger.error(f"Skip {tweet.id}. Did not find referenced tweet {replied_to}")
                    if not dry_run:
                        references[tweet.id] = toot["id"]
                    last_id = max(last_id, tweet.id) if last_id else tweet.id
            self._status["twitter"]["last_id"] = last_id
        else:
            logger.warning("No new tweets.")
        self._write_status()
