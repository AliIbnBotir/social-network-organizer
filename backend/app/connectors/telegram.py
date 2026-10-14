"""Telegram channel connector, using the official Bot API through aiogram.

The bot must be an admin of the channel with the "Post messages" right.
"""

from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaDocument, InputMediaPhoto, InputMediaVideo, Message

from app.config import Settings
from app.connectors.base import Connector, ConnectorStatus, OutgoingMedia, OutgoingPost, PublishResult
from app.models import MediaKind

# Bot API limits.
TEXT_LIMIT = 4096
CAPTION_LIMIT = 1024
MEDIA_GROUP_MAX = 10


class TelegramConnector(Connector):
    name = "telegram"

    def __init__(self, settings: Settings, bot: Bot | None = None):
        self._token = settings.telegram_bot_token
        self._channel = settings.telegram_channel_id
        self._bot = bot

    def is_configured(self) -> bool:
        return bool(self._token and self._channel)

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(self._token)
        return self._bot

    async def check(self) -> ConnectorStatus:
        if not self.is_configured():
            return ConnectorStatus(
                network=self.name,
                configured=False,
                ok=False,
                detail="Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID.",
            )
        try:
            me = await self.bot.get_me()
            chat = await self.bot.get_chat(self._channel)
            member = await self.bot.get_chat_member(self._channel, me.id)
        except Exception as exc:  # network errors, bad token, unknown chat
            return ConnectorStatus(network=self.name, configured=True, ok=False, detail=str(exc))

        account = f"@{me.username} → {chat.title or self._channel}"
        if member.status == "creator" or (
            member.status == "administrator" and getattr(member, "can_post_messages", False)
        ):
            return ConnectorStatus(
                network=self.name, configured=True, ok=True, detail="Ready to post.", account=account
            )
        return ConnectorStatus(
            network=self.name,
            configured=True,
            ok=False,
            detail="The bot is not an admin with the 'Post messages' right in this channel.",
            account=account,
        )

    async def publish(self, post: OutgoingPost) -> PublishResult:
        if len(post.media) > MEDIA_GROUP_MAX:
            raise ValueError(f"Telegram allows at most {MEDIA_GROUP_MAX} media items per post.")
        if len(post.body) > TEXT_LIMIT:
            raise ValueError(f"Telegram messages are limited to {TEXT_LIMIT} characters.")

        # Captions are shorter than messages; a long text goes as its own message after the media.
        caption = post.body if len(post.body) <= CAPTION_LIMIT else None
        messages: list[Message] = []

        if not post.media:
            messages.append(await self.bot.send_message(self._channel, post.body))
        elif len(post.media) == 1:
            messages.append(await self._send_single(post.media[0], caption))
        else:
            group = [_input_media(m, caption if i == 0 else None) for i, m in enumerate(post.media)]
            messages.extend(await self.bot.send_media_group(self._channel, group))

        if post.media and caption is None and post.body:
            messages.append(await self.bot.send_message(self._channel, post.body))

        ids = [str(m.message_id) for m in messages]
        return PublishResult(external_ids=ids, url=self._message_url(ids[0]))

    async def _send_single(self, media: OutgoingMedia, caption: str | None) -> Message:
        file = FSInputFile(media.path)
        if media.kind == MediaKind.photo:
            return await self.bot.send_photo(self._channel, file, caption=caption)
        if media.kind == MediaKind.video:
            return await self.bot.send_video(self._channel, file, caption=caption)
        return await self.bot.send_document(self._channel, file, caption=caption)

    def _message_url(self, message_id: str) -> str | None:
        # Public channels have a username; private ones only have a numeric id.
        if self._channel.startswith("@"):
            return f"https://t.me/{self._channel[1:]}/{message_id}"
        return None

    async def close(self) -> None:
        if self._bot is not None:
            await self._bot.session.close()


def _input_media(media: OutgoingMedia, caption: str | None):
    file = FSInputFile(media.path)
    if media.kind == MediaKind.photo:
        return InputMediaPhoto(media=file, caption=caption)
    if media.kind == MediaKind.video:
        return InputMediaVideo(media=file, caption=caption)
    return InputMediaDocument(media=file, caption=caption)
