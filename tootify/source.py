import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReferencedPostMissing(ValueError):
    pass

class ReferenceAlreadyExists(ValueError):
    pass


class Media:
    def __init__(self, media_url: str, description: Optional[str] = None) -> None:
        self.media_url = media_url
        self.description = description

    def __repr__(self) -> str:
        return f"Media({repr(self.media_url)}, {repr(self.description)})"


class Toot:
    def __init__(
        self,
        source: "Source",
        reference: str,
        status: str,
        reply_to: Optional[str] = None,
        media: List[Media] = [],
    ) -> None:
        self.source = source
        self.reference = reference
        self.status = status
        self.reply_to = reply_to
        self.media = media

    def __repr__(self) -> str:
        return f"Toot({repr(self.source)}, {repr(self.reference)}, {repr(self.status)}, {repr(self.in_reply_to_id)}, {repr(self.media)})"

    @property
    def in_reply_to_id(self):
        if self.reply_to:
            if self.reply_to in self.source.config["status"]["references"]:
                return self.source.config["status"]["references"][self.reply_to]
            else:
                raise ReferencedPostMissing(f"Did not find referenced post {self.reply_to}")
        else:
            logger.debug(f"Not a reply")

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        if self.reference in self.source.config["status"]["references"]:
            raise ReferenceAlreadyExists(f"Reference {self.reference} already exists.")
        self._id = id
        self.source.config["status"]["references"][self.reference] = id


class Source(ABC):
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        if not "status" in self.config:
            self.config["status"] = {"references": {}}
        self._new_posts = []

    @property
    def config(self):
        return self._config

    def __iter__(self):
        self._new_posts = iter(self.get_new_posts())
        return self

    def __next__(self):
        return next(self._new_posts)

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def get_new_posts(self) -> List[Toot]:
        pass
