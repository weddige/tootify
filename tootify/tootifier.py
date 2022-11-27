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
import requests

logger = logging.getLogger(__name__)


class Tootifier:
    def __init__(self, config: Path) -> None:
        self._status_path = config
        self._read_status()

    def _read_status(self) -> None:
        self._status = yaml.load(self._status_path.open("r"), yaml.SafeLoader)
        if "status" not in self._status:
            logger.debug("Add status section")
            self._status["status"] = {
                "last_tweet": self._status["twitter"].get("last_id", None),  # Legacy
                "references": {},
            }

    def _write_status(self, dry_run: bool = False) -> None:
        if not dry_run:
            yaml.dump(self._status, self._status_path.open("w"), yaml.dumper.SafeDumper)
        else:
            logger.info("Dry run: Skip updating config.")

    def _get_new_tweets(self):
        logger.debug(f"Get tweets newer than {self._status['status'].get('last_tweet', None)}")
        result = self._twitter_client.get_users_tweets(
            id=self._twitter_user_id,
            exclude=["retweets", "replies"],
            tweet_fields=["conversation_id", "referenced_tweets", "attachments"],
            since_id=self._status["status"].get("last_tweet", None),
            expansions=["attachments.media_keys"],
            media_fields=["url", "alt_text", "variants"],
        )
        return result

    def _get_conversations(self, tweets):
        conversations = defaultdict(list)
        for tweet in tweets:
            conversations[tweet.conversation_id].append(tweet)
        return dict(conversations)

    def _expand_urls(self, text: str):
        # Find twitter short urls
        urls = re.findall("https://t.co/[0-9a-zA-Z]+", text)
        for url in urls:
            try:
                res = urllib.request.urlopen(url)
                expanded_url = res.geturl()
                text = text.replace(url, expanded_url)
            except:
                pass
        return text

    def _strip_self_referencing_urls(self, text: str, tweet_id):
        url = f"https://twitter.com/{self._status['twitter']['username']}/status/{tweet_id}/"
        logger.debug(f"Strip {url}([a-zA-Z0-9]+/)+")
        return re.sub(f"{url}([a-zA-Z0-9]+/)+[a-zA-Z0-9]*", "", text)

    def _expand_handles(self, text: str):
        # Find twitter short urls
        handles = re.findall("(?<=[^0-9a-zA-Z_])@[0-9a-zA-Z_]{1,15}(?=[^0-9a-zA-Z_@]|$)", text)
        for handle in handles:
            text = text.replace(handle, f"{handle}@twitter.com")
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

    def _toot_media(self, media):
        result = []
        for media in media:
            response = requests.get(media.url)
            if response.ok:
                result.append(
                    self._mastodon_api.media_post(
                        response.content, mime_type=response.headers["content-type"], description=media.alt_text
                    )
                )
        return result

    def toot_new_tweets(self, dry_run: bool = False, skip: bool = False):
        skip = skip or dry_run
        tweets = self._get_new_tweets()
        if tweets.data:
            conversations = self._get_conversations(tweets.data)
            included_media = tweets.includes.get("media", [])

            last_id = self._status["status"].get("last_tweet", None)
            references = self._status["status"].get("references", {})

            for conversation in conversations.values():
                for tweet in sorted(conversation, key=lambda tweet: tweet.id):
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
                    in_reply_to_id = None
                    if tweet.id != tweet.conversation_id:
                        replied_to = (
                            [ref.id for ref in tweet.referenced_tweets or [] if ref.type == "replied_to"] or [None]
                        )[0]
                        if replied_to in references:
                            logger.debug(f"Tweet {tweet.id} is a reply to {replied_to}")
                            in_reply_to_id = references[replied_to]
                        else:
                            logger.error(f"Skip {tweet.id}. Did not find referenced tweet {replied_to}")
                            continue
                    logger.debug(f"Clean text: {tweet.text}")
                    tweet_text = self._strip_self_referencing_urls(
                        self._expand_urls(self._expand_handles(tweet.text)), tweet_id=tweet.id
                    )
                    logger.debug(f"Cleaned text: {tweet_text}")
                    if skip:
                        logger.info(f"Skip tweet {tweet.id}")
                    else:
                        logger.debug(f"Download media")
                        media_ids = self._toot_media(media)
                        logger.debug(f"Toot")
                        toot = self._mastodon_api.status_post(
                            tweet_text,
                            in_reply_to_id=in_reply_to_id,
                            media_ids=media_ids,
                        )
                        references[tweet.id] = toot["id"]
                    last_id = max(last_id, tweet.id) if last_id else tweet.id
            if not "status" in self._status:
                self._status["status"] = {}
            self._status["status"]["last_tweet"] = last_id
            self._status["status"]["references"] = references
        else:
            logger.warning("No new tweets.")
        self._write_status(dry_run)
