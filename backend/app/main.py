import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.connectors.registry import close_connectors
from app.db import init_db
from app.scheduler import create_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    await init_db()

    scheduler = create_scheduler(settings)
    if settings.scheduler_enabled:
        scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await close_connectors()


app = FastAPI(title="Social Network Organizer", lifespan=lifespan)
app.include_router(router)
