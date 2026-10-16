from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.connectors.base import OutgoingMedia, OutgoingPost
from app.connectors.telegram import CAPTION_LIMIT, TelegramConnector
from app.models import MediaKind


def make_connector(channel="@mychannel"):
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(message_id=10)
    bot.send_photo.return_value = SimpleNamespace(message_id=11)
    bot.send_media_group.return_value = [SimpleNamespace(message_id=12), SimpleNamespace(message_id=13)]
    settings = Settings(telegram_bot_token="t", telegram_channel_id=channel)
    return TelegramConnector(settings, bot=bot), bot


async def test_text_post():
    connector, bot = make_connector()
    result = await connector.publish(OutgoingPost(body="Salom!"))
    bot.send_message.assert_awaited_once_with("@mychannel", "Salom!")
    assert result.external_ids == ["10"]
    assert result.url == "https://t.me/mychannel/10"


async def test_photo_with_caption(tmp_path: Path):
    connector, bot = make_connector()
    photo = OutgoingMedia(MediaKind.photo, tmp_path / "a.jpg")
    result = await connector.publish(OutgoingPost(body="Caption", media=[photo]))
    assert bot.send_photo.await_args.kwargs["caption"] == "Caption"
    bot.send_message.assert_not_awaited()
    assert result.external_ids == ["11"]


async def test_long_text_with_photo_goes_as_separate_message(tmp_path: Path):
    connector, bot = make_connector()
    body = "x" * (CAPTION_LIMIT + 1)
    photo = OutgoingMedia(MediaKind.photo, tmp_path / "a.jpg")
    result = await connector.publish(OutgoingPost(body=body, media=[photo]))
    assert bot.send_photo.await_args.kwargs["caption"] is None
    bot.send_message.assert_awaited_once_with("@mychannel", body)
    assert result.external_ids == ["11", "10"]


async def test_album(tmp_path: Path):
    connector, bot = make_connector(channel="-100123")
    media = [OutgoingMedia(MediaKind.photo, tmp_path / "a.jpg"), OutgoingMedia(MediaKind.video, tmp_path / "b.mp4")]
    result = await connector.publish(OutgoingPost(body="Album", media=media))
    group = bot.send_media_group.await_args.args[1]
    assert [g.caption for g in group] == ["Album", None]
    assert result.external_ids == ["12", "13"]
    assert result.url is None  # private channel ids have no public link


async def test_too_many_media_rejected(tmp_path: Path):
    connector, _ = make_connector()
    media = [OutgoingMedia(MediaKind.photo, tmp_path / f"{i}.jpg") for i in range(11)]
    with pytest.raises(ValueError):
        await connector.publish(OutgoingPost(body="", media=media))


async def test_check_reports_missing_admin_rights():
    connector, bot = make_connector()
    bot.get_me.return_value = SimpleNamespace(id=1, username="mybot")
    bot.get_chat.return_value = SimpleNamespace(title="My Channel")
    bot.get_chat_member.return_value = SimpleNamespace(status="member")
    status = await connector.check()
    assert status.configured and not status.ok
    assert status.account == "@mybot → My Channel"
