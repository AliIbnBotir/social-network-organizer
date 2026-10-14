"""Background scheduler (APScheduler, running inside the app process).

The database is the source of truth for what is scheduled: a single
recurring job looks for posts that are due. That way scheduled posts survive
restarts without a separate job store, and nothing needs its own server.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import Settings
from app.db import SessionLocal
from app.models import Post, PostStatus

log = logging.getLogger(__name__)

DISPATCH_JOB_ID = "dispatch_due_posts"


async def dispatch_due_posts() -> int:
    """Find scheduled posts whose time has come.

    Step 1 only finds and logs them; publishing is wired in with the
    scheduling queue (step 3).
    """
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        due = (
            await session.scalars(
                select(Post.id).where(Post.status == PostStatus.scheduled, Post.scheduled_at <= now)
            )
        ).all()
    if due:
        log.info("Posts due for publishing: %s", list(due))
    return len(due)


def create_scheduler(settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        dispatch_due_posts,
        "interval",
        seconds=settings.scheduler_poll_seconds,
        id=DISPATCH_JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
