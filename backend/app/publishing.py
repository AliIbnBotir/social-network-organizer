"""Sending a post to its networks.

Used by "Publish now" today and by the scheduler once the queue lands, so a
post goes out the same way whichever triggered it.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.connectors import OutgoingMedia, OutgoingPost, get_connectors
from app.models import Post, PostStatus, Publication, PublicationStatus

log = logging.getLogger(__name__)


class NotPublishable(Exception):
    """The post can't be sent in its current state."""


def outgoing_post(post: Post) -> OutgoingPost:
    media_dir = get_settings().media_dir
    return OutgoingPost(
        body=post.body,
        media=[OutgoingMedia(kind=m.kind, path=media_dir / m.file_path) for m in post.media],
    )


async def publish_post(session: AsyncSession, post: Post) -> Post:
    """Send the post to every target network that hasn't received it yet.

    Networks that already succeeded are skipped, so publishing a failed post
    again only retries the networks that failed. Post and publications must
    already be loaded.
    """
    if post.status in (PostStatus.publishing, PostStatus.published):
        raise NotPublishable(f"This post is already {post.status.value}.")
    if not post.body.strip() and not post.media:
        raise NotPublishable("The post is empty.")
    if not post.targets:
        raise NotPublishable("Choose at least one network.")

    post.status = PostStatus.publishing
    await session.commit()

    by_network = {p.network: p for p in post.publications}
    connectors = get_connectors()
    outgoing = outgoing_post(post)

    for network in post.targets:
        publication = by_network.get(network)
        if publication is None:
            publication = Publication(network=network)
            post.publications.append(publication)
        if publication.status == PublicationStatus.sent:
            continue

        connector = connectors.get(network)
        try:
            if connector is None:
                raise RuntimeError(f"Unknown network '{network}'.")
            if not connector.is_configured():
                raise RuntimeError(f"{network.capitalize()} is not connected. Check the Connections page.")
            result = await connector.publish(outgoing)
        except Exception as exc:  # network errors, API errors, limits
            log.warning("Publishing post %s to %s failed: %s", post.id, network, exc)
            publication.status = PublicationStatus.failed
            publication.error = str(exc)
            continue

        publication.status = PublicationStatus.sent
        publication.external_ids = result.external_ids
        publication.url = result.url
        publication.error = None
        publication.published_at = datetime.now(timezone.utc)

    sent = {p.network for p in post.publications if p.status == PublicationStatus.sent}
    post.status = PostStatus.published if set(post.targets) <= sent else PostStatus.failed
    await session.commit()
    return post
