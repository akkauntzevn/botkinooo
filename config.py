"""
Central configuration. Everything sensitive is loaded from environment
variables / a local .env file — nothing is ever hardcoded.
"""
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv
import os

load_dotenv()


def _env_list(name: str) -> List[int]:
    raw = os.getenv(name, "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = field(default_factory=lambda: _env_list("ADMIN_IDS"))

    # Database: for high load, point DB_DSN at Postgres, e.g.
    # postgresql://user:pass@host:5432/moviebot
    # Leaving it empty falls back to local SQLite (good for dev / low load).
    DB_DSN: str = os.getenv("DB_DSN", "")
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "moviebot.sqlite3")

    # Throttling: max N updates per this many seconds, per user.
    THROTTLE_RATE: float = float(os.getenv("THROTTLE_RATE", "0.7"))

    # Deep-link prefix used in /start payloads, e.g. /start kino_105
    DEEPLINK_PREFIX: str = os.getenv("DEEPLINK_PREFIX", "kino_")

    # Userbot (Pyrogram) creds for the competitor-monitoring script
    API_ID: int = int(os.getenv("API_ID", "0") or 0)
    API_HASH: str = os.getenv("API_HASH", "")
    USERBOT_SESSION: str = os.getenv("USERBOT_SESSION", "userbot")


config = Config()

if not config.BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing — set it in your .env file")
