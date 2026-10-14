from datetime import datetime, timedelta, timezone

from app.db import SessionLocal, init_db
from app.models import Post, PostStatus
from app.scheduler import dispatch_due_posts


async def test_dispatch_finds_only_due_scheduled_posts():
    await init_db()
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        session.add_all(
            [
                Post(body="due", status=PostStatus.scheduled, scheduled_at=now - timedelta(minutes=1)),
                Post(body="later", status=PostStatus.scheduled, scheduled_at=now + timedelta(hours=1)),
                Post(body="draft", status=PostStatus.draft),
            ]
        )
        await session.commit()

    assert await dispatch_due_posts() == 1
