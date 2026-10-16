from app.config import get_settings
from app.connectors.base import Connector
from app.connectors.telegram import TelegramConnector

_connectors: dict[str, Connector] | None = None


def get_connectors() -> dict[str, Connector]:
    """All known connectors, keyed by network name.

    To add X/Twitter later: write an XConnector(Connector) and add it here.
    """
    global _connectors
    if _connectors is None:
        settings = get_settings()
        _connectors = {c.name: c for c in [TelegramConnector(settings)]}
    return _connectors


def get_connector(name: str) -> Connector:
    return get_connectors()[name]


async def close_connectors() -> None:
    global _connectors
    if _connectors:
        for connector in _connectors.values():
            await connector.close()
    _connectors = None
