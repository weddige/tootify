import datetime
import logging
import re

from instagram_basic_display.InstagramBasicDisplay import InstagramBasicDisplay

from tootify.source import Media, Source, Toot

logger = logging.getLogger(__name__)


class IGSource(Source):
    def _parse_timestamp(self, timestamp):
        return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")

    def _expand_handles(self, text: str):
        handles = re.findall("(?<=[^0-9a-zA-Z_])@[0-9a-zA-Z_]{1,15}(?=[^0-9a-zA-Z_@]|$)", text)
        familiar_accounts = self.config.get("familiar_accounts", {})
        for handle in handles:
            if handle[1:] in familiar_accounts:
                logger.debug(f"Found {handle} in familiar accounts: {familiar_accounts[handle[1:]]}")
                text = text.replace(handle, f"@{familiar_accounts[handle[1:]]}")
            else:
                text = text.replace(handle, f"{handle}@instagram.com")
        return text

    def _translate_hashtags(self, text: str) -> str:
        result = text
        for hashtag, replacement in self.config.get("common_hashtags", {}).items():
            result = re.sub(f"{re.escape(hashtag)}(?=[^0-9a-zA-Z_@]|$)", replacement, result)
        return result

    def tootify(self, post):
        media = []
        if post["media_type"] == "IMAGE":
            media = [Media(post["media_url"])]
        elif post["media_type"] == "CAROUSEL_ALBUM":
            media = [Media(media["media_url"]) for media in post["children"]["data"]]
        else:
            raise ValueError("Unknown media type")
        caption = self._translate_hashtags(self._expand_handles(post["caption"]))
        return Toot(source=self, reference=post["id"], status=caption, media=media)

    def connect(self):
        self._instagram_basic_display = InstagramBasicDisplay(
            app_id=self.config["app_id"], app_secret=self.config["app_secret"], redirect_url="https://example.com/"
        )
        self._instagram_basic_display.set_access_token(self.config["access_token"])
        self._user_profile = self._instagram_basic_display.get_user_profile()

    def get_new_posts(self):
        last_update = self.config.get("status", {}).get("last_update", None)
        new_posts = self._instagram_basic_display.get_user_media()["data"]
        if last_update:
            new_posts = [
                post
                for post in new_posts
                if self._parse_timestamp(post["timestamp"]) > self._parse_timestamp(last_update)
            ]
        if new_posts:
            self.config["status"]["last_update"] = max(
                new_posts, key=lambda post: self._parse_timestamp(post["timestamp"])
            )["timestamp"]
        return [self.tootify(post) for post in new_posts]
