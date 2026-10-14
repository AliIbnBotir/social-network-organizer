"""Database models.

A Post is written once. Each network it goes to gets its own Publication,
so adding X/Twitter later means a new Publication row per post, not a new
post table. Stats are snapshots taken over time for one Publication.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PostStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    publishing = "publishing"
    published = "published"
    failed = "failed"


class MediaKind(str, enum.Enum):
    photo = "photo"
    video = "video"
    document = "document"


class PublicationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text, default="")
    # "uz" or "en"; free-form so more languages need no migration.
    language: Mapped[str] = mapped_column(String(8), default="uz")
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus), default=PostStatus.draft, index=True)
    # Networks this post should go to, e.g. ["telegram"]. Later: ["telegram", "x"].
    targets: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["telegram"])
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    media: Mapped[list["MediaAttachment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="MediaAttachment.position"
    )
    publications: Mapped[list["Publication"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class MediaAttachment(Base):
    __tablename__ = "media_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    kind: Mapped[MediaKind] = mapped_column(Enum(MediaKind))
    # Path relative to MEDIA_DIR.
    file_path: Mapped[str] = mapped_column(String(512))
    position: Mapped[int] = mapped_column(Integer, default=0)

    post: Mapped[Post] = relationship(back_populates="media")


class Publication(Base):
    """One post delivered (or attempted) to one network."""

    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    network: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus), default=PublicationStatus.pending
    )
    # The network's own id(s) for the post, e.g. Telegram message ids.
    external_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    url: Mapped[str | None] = mapped_column(String(512))
    error: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    post: Mapped[Post] = relationship(back_populates="publications")
    stats: Mapped[list["PostStat"]] = relationship(
        back_populates="publication", cascade="all, delete-orphan", order_by="PostStat.captured_at"
    )


class PostStat(Base):
    """A snapshot of a publication's performance at a point in time."""

    __tablename__ = "post_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), index=True
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    views: Mapped[int | None] = mapped_column(Integer)
    reactions: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    # Anything network-specific that doesn't fit the columns above.
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    publication: Mapped[Publication] = relationship(back_populates="stats")
