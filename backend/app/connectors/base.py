"""The contract every social network connector implements.

Telegram is the first connector. X/Twitter (and others) plug in later by
adding a class here and registering it in registry.py; the rest of the app
only talks to this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.models import MediaKind


@dataclass
class OutgoingMedia:
    kind: MediaKind
    path: Path


@dataclass
class OutgoingPost:
    body: str
    media: list[OutgoingMedia] = field(default_factory=list)


@dataclass
class PublishResult:
    external_ids: list[str]
    url: str | None = None


@dataclass
class ConnectorStatus:
    network: str
    configured: bool
    ok: bool
    detail: str
    account: str | None = None


class Connector(ABC):
    #: Stable key stored in Publication.network and Post.targets.
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the credentials this connector needs are present."""

    @abstractmethod
    async def check(self) -> ConnectorStatus:
        """Verify credentials and permissions without posting anything."""

    @abstractmethod
    async def publish(self, post: OutgoingPost) -> PublishResult:
        """Send a post to the network."""

    async def close(self) -> None:
        """Release network resources. Optional."""
