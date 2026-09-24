"""
CONCEPTUAL supplementary script — runs as a separate process from the
bot, using a personal Telegram account (userbot) via Pyrogram.

What it does:
  * Listens to new messages in a list of channels you already follow
    with your own account.
  * When a video/document/animation appears, it re-uses the SAME
    `Database` class as the main bot (so both write to the same table)
    and stores the file_id under an auto-generated numeric code.
  * Captions are stripped/replaced so you fully control what your own
    bot shows to your users, and forwards are re-sent as fresh
    messages rather than forwarded (no "Forwarded from" tag).

IMPORTANT — read before running this:
  * Only monitor channels you are legitimately a member of, and only
    republish content you have the rights to republish. Copyright and
    a channel's own terms of service still apply to a userbot exactly
    as they would to a human doing the same thing by hand — automating
    it does not change that.
  * A userbot session is tied to a real phone-number account. Getting
    it banned/limited is a real risk if used aggressively (join too
    many channels quickly, send too fast, etc.) — keep it read-only
    like this script does (no auto-joining, no auto-messaging humans).
  * This file is intentionally a *starting point*, not a turnkey
    scraper: fill in SOURCE_CHANNELS with channels you actually run or
    have explicit permission to re-publish from.

Install:  pip install pyrogram tgcrypto
Run:      python -m userbot.monitor
"""
from __future__ import annotations

import asyncio
import itertools
import logging

from pyrogram import Client, filters
from pyrogram.types import Message as PyroMessage

from config import config
from database import Database

logger = logging.getLogger("userbot")

# Fill with channel usernames (no @) or numeric ids you're allowed to re-publish from.
SOURCE_CHANNELS: list[str] = [
    # "some_public_movie_channel",
]

_code_counter = itertools.count(start=100000)  # avoid clashing with manually-added codes


async def _next_code(db: Database) -> str:
    # Simple monotonically increasing code; swap for whatever scheme
    # your main bot's /addmovie uses if you want them unified.
    for candidate in _code_counter:
        code = f"auto{candidate}"
        if not await db.get_movie_by_code(code):
            return code
    raise RuntimeError("unreachable")


async def run() -> None:
    if not config.API_ID or not config.API_HASH:
        raise RuntimeError("API_ID / API_HASH must be set in .env for the userbot script")

    db = Database()
    await db.init_models()

    app = Client(
        config.USERBOT_SESSION,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
    )

    @app.on_message(filters.chat(SOURCE_CHANNELS) & (filters.video | filters.document | filters.animation))
    async def on_new_media(client: Client, message: PyroMessage):
        if message.video:
            file_id, file_type = message.video.file_id, "video"
        elif message.animation:
            file_id, file_type = message.animation.file_id, "animation"
        else:
            file_id, file_type = message.document.file_id, "document"

        # Pyrogram's file_id format is compatible with Bot API file_ids
        # for the same file, so the aiogram bot can send it directly.
        title = "Yangi kino"  # caption intentionally stripped/replaced
        code = await _next_code(db)

        await db.add_movie(
            code=code,
            title=title,
            file_id=file_id,
            added_by=0,  # 0 marks "added by userbot monitor"
            file_type=file_type,
            caption=title,
        )
        logger.info("Saved new movie from monitored channel as code=%s", code)

    logger.info("Userbot monitor starting, watching: %s", SOURCE_CHANNELS)
    await app.start()
    await asyncio.Event().wait()  # run forever


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
