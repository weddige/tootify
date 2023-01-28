from datetime import datetime
import logging
import re
from typing import List

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
            )
            last_update_new = last_update
            for entry in parser.entries:
                if last_update is None or (published_parsed := datetime(*entry["published_parsed"][:6])) > last_update:
                    last_update_new = (
                        max(last_update_new, published_parsed)
                        if last_update_new
                        else published_parsed
                    )
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
            feed["last_update"] = last_update_new.isoformat()
        return result
