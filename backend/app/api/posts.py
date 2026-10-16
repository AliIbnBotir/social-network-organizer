"""Posts: write drafts, attach media, publish."""

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_login
from app.config import get_settings
from app.db import get_session
from app.models import MediaAttachment, MediaKind, Post, PostStatus, PublicationStatus
from app.publishing import NotPublishable, publish_post

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])
Session = Annotated[AsyncSession, Depends(get_session)]

# Telegram's limit for files sent by a bot.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_MEDIA_PER_POST = 10
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
# Posts in these states can still be changed.
EDITABLE = {PostStatus.draft, PostStatus.failed}


class PostIn(BaseModel):
    body: str = ""
    language: str = Field("uz", max_length=8)
    targets: list[str] = ["telegram"]


class PostUpdate(BaseModel):
    body: str | None = None
    language: str | None = Field(None, max_length=8)
    targets: list[str] | None = None


class MediaOut(BaseModel):
    id: int
    kind: MediaKind
    url: str


class PublicationOut(BaseModel):
    network: str
    status: PublicationStatus
    url: str | None
    error: str | None
    published_at: datetime | None


class PostOut(BaseModel):
    id: int
    body: str
    language: str
    status: PostStatus
    targets: list[str]
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    media: list[MediaOut]
    publications: list[PublicationOut]


def utc(value: datetime | None) -> datetime | None:
    """SQLite drops the timezone on the way back; every stored time is UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def to_out(post: Post) -> PostOut:
    return PostOut(
        id=post.id,
        body=post.body,
        language=post.language,
        status=post.status,
        targets=post.targets,
        scheduled_at=utc(post.scheduled_at),
        created_at=utc(post.created_at),
        updated_at=utc(post.updated_at),
        media=[MediaOut(id=m.id, kind=m.kind, url=f"/api/media/{m.id}") for m in post.media],
        publications=[
            PublicationOut(
                network=p.network, status=p.status, url=p.url, error=p.error, published_at=utc(p.published_at)
            )
            for p in post.publications
        ],
    )


async def load_post(session: AsyncSession, post_id: int) -> Post:
    post = await session.scalar(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media), selectinload(Post.publications))
        .execution_options(populate_existing=True)
    )
    if post is None:
        raise HTTPException(404, "Post not found.")
    return post


def ensure_editable(post: Post) -> None:
    if post.status not in EDITABLE:
        raise HTTPException(409, f"This post is {post.status.value} and can't be changed.")


@router.get("/posts")
async def list_posts(session: Session, status: PostStatus | None = None) -> list[PostOut]:
    query = (
        select(Post)
        .options(selectinload(Post.media), selectinload(Post.publications))
        .order_by(Post.updated_at.desc(), Post.id.desc())
    )
    if status is not None:
        query = query.where(Post.status == status)
    return [to_out(p) for p in await session.scalars(query)]


@router.post("/posts", status_code=201)
async def create_post(data: PostIn, session: Session) -> PostOut:
    post = Post(body=data.body, language=data.language, targets=data.targets)
    session.add(post)
    await session.commit()
    return to_out(await load_post(session, post.id))


@router.get("/posts/{post_id}")
async def get_post(post_id: int, session: Session) -> PostOut:
    return to_out(await load_post(session, post_id))


@router.patch("/posts/{post_id}")
async def update_post(post_id: int, data: PostUpdate, session: Session) -> PostOut:
    post = await load_post(session, post_id)
    ensure_editable(post)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(post, field, value)
    await session.commit()
    return to_out(await load_post(session, post_id))


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(post_id: int, session: Session) -> None:
    """Delete the post here. Anything already sent stays on the network."""
    post = await load_post(session, post_id)
    if post.status == PostStatus.publishing:
        raise HTTPException(409, "This post is being published right now.")
    await session.delete(post)
    await session.commit()
    shutil.rmtree(get_settings().media_dir / str(post_id), ignore_errors=True)


@router.post("/posts/{post_id}/media", status_code=201)
async def upload_media(post_id: int, file: UploadFile, session: Session) -> PostOut:
    post = await load_post(session, post_id)
    ensure_editable(post)
    if len(post.media) >= MAX_MEDIA_PER_POST:
        raise HTTPException(400, f"A post can have at most {MAX_MEDIA_PER_POST} images or videos.")

    content_type = file.content_type or ""
    if content_type in PHOTO_TYPES:
        kind = MediaKind.photo
    elif content_type.startswith("video/"):
        kind = MediaKind.video
    else:
        kind = MediaKind.document

    relative = Path(str(post_id)) / f"{uuid.uuid4().hex}{Path(file.filename or '').suffix.lower()[:10]}"
    target = get_settings().media_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with target.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                target.unlink()
                raise HTTPException(413, "Files can be at most 50 MB.")
            out.write(chunk)

    post.media.append(MediaAttachment(kind=kind, file_path=relative.as_posix(), position=len(post.media)))
    await session.commit()
    return to_out(await load_post(session, post_id))


@router.delete("/posts/{post_id}/media/{media_id}")
async def delete_media(post_id: int, media_id: int, session: Session) -> PostOut:
    post = await load_post(session, post_id)
    ensure_editable(post)
    media = next((m for m in post.media if m.id == media_id), None)
    if media is None:
        raise HTTPException(404, "Media not found.")
    post.media.remove(media)
    for position, remaining in enumerate(post.media):
        remaining.position = position
    await session.commit()
    (get_settings().media_dir / media.file_path).unlink(missing_ok=True)
    return to_out(await load_post(session, post_id))


@router.get("/media/{media_id}")
async def get_media(media_id: int, session: Session) -> FileResponse:
    media = await session.get(MediaAttachment, media_id)
    path = get_settings().media_dir / media.file_path if media else None
    if path is None or not path.is_file():
        raise HTTPException(404, "Media not found.")
    return FileResponse(path)


@router.post("/posts/{post_id}/publish")
async def publish(post_id: int, session: Session) -> PostOut:
    post = await load_post(session, post_id)
    try:
        await publish_post(session, post)
    except NotPublishable as exc:
        raise HTTPException(409, str(exc)) from exc
    return to_out(await load_post(session, post_id))
