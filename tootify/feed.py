from datetime import datetime
import logging
import re
from typing import List

import dateparser
import feedparser

from tootify.source import Media, Source, Toot

logger = logging.getLogger(__name__)


class FeedSource(Source):
    def connect(self):
        pass

    def get_new_posts(self) -> List[Toot]:
        result = []
        for feed in self.config["feeds"]:
            parser = feedparser.parse(feed["url"])
            last_update = feed.get("last_update", None) and datetime.fromisoformat(
                feed.get("last_update", None)
            ).replace(tzinfo=None)
            last_update_new = last_update
            for entry in parser.entries:
                if not re.search(feed.get("pattern", ".*"), entry["description"]):
                    logger.info(f'Did not match: {feed.get("pattern", ".*")}')
                    continue
                published_parsed = dateparser.parse(entry["published"]).replace(tzinfo=None)
                if last_update is None or published_parsed > last_update:
                    last_update_new = (
                        max(filter(None, (last_update_new, published_parsed)))
                        if last_update_new
                        else published_parsed
                    )
                    if entry["id"] in self.config["status"]["references"]:
                        logger.warning(f'Skip {entry["id"]} because entry has been redated.')
                        continue
                    result.append(
                        Toot(
                            source=self,
                            reference=entry["id"],
                            status=self.config["template"].format(
                                title=entry["title"],
                                description=entry["description"],
                                link=entry["link"],
                            ),
                        )
                    )
            feed["last_update"] = last_update_new and last_update_new.isoformat()
        return result
