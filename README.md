# Social Network Organizer

Write a post once and publish it to your social networks, schedule posts, and
track how they perform. Telegram channels are supported first; X/Twitter and
others plug in later as additional connectors.

Posts can be text, images or video, in Uzbek or English.

## How it's built

| Part | Choice |
| --- | --- |
| Backend | Python, FastAPI (`backend/`) |
| Telegram | Official Bot API via aiogram. Your bot is an admin of your channel and posts there. |
| Database | SQLite by default through SQLAlchemy; switch to PostgreSQL by changing `DATABASE_URL` |
| Scheduling | APScheduler inside the backend; no extra server |
| Dashboard | React + Vite (`frontend/`) |
| Hosting | Docker Compose |

Data model: a **Post** (text + media) is written once. Each network it goes to
gets a **Publication**, and performance is stored as **PostStat** snapshots
for each publication. Every network implements the same `Connector` interface
(`backend/app/connectors/base.py`).

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Add the bot to your channel as an admin with the **Post messages** right.
3. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN` and
   `TELEGRAM_CHANNEL_ID` (`@yourchannel`, or the numeric `-100…` id for a
   private channel).

### Run with Docker

```bash
docker compose up --build
```

Open http://localhost:8080. The **Connections** panel shows whether the bot
can post to your channel.

### Run for development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env   # then fill it in
uvicorn app.main:app --reload
pytest

# Dashboard (in another terminal)
cd frontend
npm install
npm run dev               # http://localhost:5173, proxies /api to :8000
```

## Roadmap

1. App foundation (this)
2. Write drafts and post them to Telegram
3. Scheduling queue
4. Analytics
5. X/Twitter connector
