import logging
from pathlib import Path

import requests
import yaml
from mastodon import Mastodon

from tootify.source import ReferencedPostMissing

logger = logging.getLogger(__name__)


class Tootifier:
    def __init__(self, config: Path) -> None:
        self._status_path = config
        self._sources = {}
        self._read_status()

    def _read_status(self) -> None:
        self._status = yaml.load(self._status_path.open("r"), yaml.SafeLoader) or {}
        if "instagram" in self._status:
            from tootify.instagram import IGSource

            self._sources["instagram"] = IGSource(self._status["instagram"])
        if "twitter" in self._status:
            from tootify.twitter import TwitterSource

            self._sources["twitter"] = TwitterSource(self._status["twitter"])
        if "feed" in self._status:
            from tootify.feed import FeedSource

            self._sources["feed"] = FeedSource(self._status["feed"])
        if "mastodon" not in self._status:
            logger.warning("No mastodon credentials found. Run with --login.")

    def _write_status(self, dry_run: bool = False) -> None:
        for source in self._sources:
            self._status[source] = self._sources[source].config
        if not dry_run:
            yaml.dump(self._status, self._status_path.open("w"), yaml.dumper.SafeDumper)
        else:
            logger.info("Dry run: Skip updating config.")
            logger.debug(self._status)

    def login(self, instance: str, username: str, password: str, /, dry_run: bool = False):
        base_url = f"https://{instance}"
        client_id, client_secret = Mastodon.create_app("tootifier", api_base_url=base_url)
        logger.debug(f'Created mastodon app "tootifier".')
        if "mastodon" not in self._status:
            logger.debug(f"Create new config section.")
            self._status["mastodon"] = {}
        self._status["mastodon"]["client_id"] = client_id
        self._status["mastodon"]["client_secret"] = client_secret
        self._status["mastodon"]["instance"] = instance

        self._mastodon_api = Mastodon(
            client_id=self._status["mastodon"]["client_id"],
            client_secret=self._status["mastodon"]["client_secret"],
            api_base_url=f"https://{self._status['mastodon']['instance']}",
        )
        access_token = self._mastodon_api.log_in(username, password)
        r = self._mastodon_api.account_verify_credentials()
        if not r.get("error"):
            self._status["mastodon"]["access_token"] = access_token
        else:
            logger.critical(f"Failed to login at {base_url}: {r.get('error')}")
        self._write_status(dry_run)

    def connect(self):
        logger.debug("connect to Mastodon")
        self._mastodon_api = Mastodon(
            client_id=self._status["mastodon"].get("client_id", None),
            client_secret=self._status["mastodon"].get("client_secret", None),
            access_token=self._status["mastodon"]["access_token"],
            api_base_url=f"https://{self._status['mastodon']['instance']}",
        )
        check = self._mastodon_api.account_verify_credentials()
        if check.get("error"):
            logger.error(check.get("error connecting to Mastodon"))
        else:
            username = str(check["username"])
            logger.info(f"connected on @{username}@{self._status['mastodon']['instance']}")

        for source in self._sources:
            logger.debug(f"connect to {source}")
            self._sources[source].connect()

    def _toot_media(self, media):
        result = []
        for media in media:
            response = requests.get(media.media_url)
            if response.ok:
                result.append(
                    self._mastodon_api.media_post(
                        response.content, mime_type=response.headers["content-type"], description=media.description
                    )
                )
        return result

    def toot(self, dry_run: bool = False, skip: bool = False):
        skip = skip or dry_run

        try:
            for source in self._sources.values():
                for toot in source:
                    if skip:
                        logger.info(f"Skip tooting {toot.reference}")
                    else:
                        try:
                            in_reply_to_id = toot.in_reply_to_id
                            logger.debug(f"Toot media for {toot.reference}")
                            media_ids = self._toot_media(toot.media)
                            logger.debug(f"Toot {toot.reference}")
                            status = self._mastodon_api.status_post(
                                toot.status,
                                in_reply_to_id=in_reply_to_id,
                                media_ids=media_ids,
                            )
                            toot.id = status["id"]
                        except ReferencedPostMissing:
                            logger.error("Skip toot, as referenced post could not be found.")
        finally:
            # Update config in any case, not to toot anything multiple times
            self._write_status(dry_run)
