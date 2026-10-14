import os
import tempfile

# Configure before the app is imported: throwaway database, no real Telegram.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["MEDIA_DIR"] = f"{_tmp}/media"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHANNEL_ID"] = ""
os.environ["SCHEDULER_ENABLED"] = "false"
