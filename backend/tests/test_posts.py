import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.connectors import registry
from app.connectors.base import Connector, ConnectorStatus, OutgoingPost, PublishResult
from app.main import app


class FakeConnector(Connector):
    name = "telegram"

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[OutgoingPost] = []

    def is_configured(self) -> bool:
        return True

    async def check(self) -> ConnectorStatus:
        return ConnectorStatus(network=self.name, configured=True, ok=True, detail="Ready to post.")

    async def publish(self, post: OutgoingPost) -> PublishResult:
        if self.fail:
            raise RuntimeError("Telegram is down")
        self.sent.append(post)
        return PublishResult(external_ids=["42"], url="https://t.me/mychannel/42")


@pytest.fixture
def fake():
    connector = FakeConnector()
    registry._connectors = {"telegram": connector}
    yield connector
    registry._connectors = None


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_draft_lifecycle(client):
    post = client.post("/api/posts", json={"body": "Salom", "language": "uz"}).json()
    assert post["status"] == "draft"
    assert post["targets"] == ["telegram"]

    updated = client.patch(f"/api/posts/{post['id']}", json={"body": "Salom dunyo"}).json()
    assert updated["body"] == "Salom dunyo"
    assert updated["language"] == "uz"

    assert any(p["id"] == post["id"] for p in client.get("/api/posts?status=draft").json())

    assert client.delete(f"/api/posts/{post['id']}").status_code == 204
    assert client.get(f"/api/posts/{post['id']}").status_code == 404


def test_media_upload_and_remove(client):
    post_id = client.post("/api/posts", json={"body": "Rasm"}).json()["id"]

    post = client.post(
        f"/api/posts/{post_id}/media", files={"file": ("a.jpg", b"jpegdata", "image/jpeg")}
    ).json()
    assert [m["kind"] for m in post["media"]] == ["photo"]
    media_url = post["media"][0]["url"]
    assert client.get(media_url).content == b"jpegdata"

    post = client.post(
        f"/api/posts/{post_id}/media", files={"file": ("b.mp4", b"mp4data", "video/mp4")}
    ).json()
    assert [m["kind"] for m in post["media"]] == ["photo", "video"]

    post = client.delete(f"/api/posts/{post_id}/media/{post['media'][0]['id']}").json()
    assert [m["kind"] for m in post["media"]] == ["video"]
    assert client.get(media_url).status_code == 404


def test_publish_sends_once(client, fake):
    post_id = client.post("/api/posts", json={"body": "Hello"}).json()["id"]
    client.post(f"/api/posts/{post_id}/media", files={"file": ("a.png", b"png", "image/png")})

    post = client.post(f"/api/posts/{post_id}/publish").json()
    assert post["status"] == "published"
    assert post["publications"][0]["status"] == "sent"
    assert post["publications"][0]["url"] == "https://t.me/mychannel/42"
    assert fake.sent[0].body == "Hello"
    assert fake.sent[0].media[0].path.read_bytes() == b"png"

    # Published posts can't be sent again or edited.
    assert client.post(f"/api/posts/{post_id}/publish").status_code == 409
    assert client.patch(f"/api/posts/{post_id}", json={"body": "x"}).status_code == 409
    assert len(fake.sent) == 1


def test_failed_publish_can_be_retried(client, fake):
    fake.fail = True
    post_id = client.post("/api/posts", json={"body": "Hello"}).json()["id"]

    post = client.post(f"/api/posts/{post_id}/publish").json()
    assert post["status"] == "failed"
    assert post["publications"][0]["error"] == "Telegram is down"

    fake.fail = False
    post = client.post(f"/api/posts/{post_id}/publish").json()
    assert post["status"] == "published"
    assert post["publications"][0]["error"] is None
    assert len(post["publications"]) == 1


def test_empty_post_is_not_published(client, fake):
    post_id = client.post("/api/posts", json={"body": "  "}).json()["id"]
    assert client.post(f"/api/posts/{post_id}/publish").status_code == 409
    assert fake.sent == []


def test_password_login(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "dashboard_password", "secret")

    assert client.get("/api/auth").json() == {"auth_enabled": True, "logged_in": False}
    assert client.get("/api/posts").status_code == 401
    assert client.get("/api/connectors").status_code == 401
    assert client.get("/api/health").status_code == 200

    assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"password": "secret"}).status_code == 200
    assert client.get("/api/auth").json()["logged_in"] is True
    assert client.get("/api/posts").status_code == 200

    client.post("/api/logout")
    assert client.get("/api/posts").status_code == 401

    # Changing the password logs everyone out.
    client.post("/api/login", json={"password": "secret"})
    monkeypatch.setattr(get_settings(), "dashboard_password", "new")
    assert client.get("/api/posts").status_code == 401
