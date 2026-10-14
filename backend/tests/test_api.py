from fastapi.testclient import TestClient

from app.main import app


def test_health_and_connectors():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok", "scheduler_running": False}

        connectors = client.get("/api/connectors").json()
        assert connectors == [
            {
                "network": "telegram",
                "configured": False,
                "ok": False,
                "detail": "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID.",
                "account": None,
            }
        ]
