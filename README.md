# Telegram Movie Bot — Aiogram 3.x, Async, file_id-cached

## Structure
```
movie_bot/
├── config.py                 # env-driven config, fails fast if BOT_TOKEN missing
├── database.py                # SQLAlchemy Core async layer (SQLite or Postgres)
├── keyboards.py               # inline keyboard builders
├── main.py                    # entrypoint: wiring, middleware, polling
├── filters/
│   └── admin.py                # IsAdmin filter (checks ADMIN_IDS)
├── middlewares/
│   ├── throttling.py           # anti-spam rate limiting
│   └── user_tracking.py        # upserts users, enforces bans
├── services/
│   └── subscription.py         # "Homiylik" mandatory-subscription check
├── handlers/
│   ├── user.py                  # /start, deep links, movie delivery
│   └── admin.py                  # /addmovie, /addsponsor, /ban, /stats...
├── userbot/
│   └── monitor.py               # OPTIONAL Pyrogram script (see warnings inside)
├── requirements.txt
└── .env.example
```

## Setup
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN and ADMIN_IDS
python main.py
```

## How each feature works

**1. file_id caching** — `database.py`'s `movies` table stores only
`file_id` (a string), never the file bytes. `handlers/user.py`
sends with `bot.send_video(chat_id, video=file_id, ...)`, which
Telegram serves from its own CDN instantly — no re-upload, no hitting
your bot's upload bandwidth or the 20MB/50MB Bot-API upload ceilings
on repeat sends.

**2. Deep linking** — `CommandStart(deep_link=True)` in
`handlers/user.py` catches `/start kino_105`; `_extract_code()` strips
the `kino_` prefix (configurable via `DEEPLINK_PREFIX`) and looks the
movie up by that code.

**3. Dynamic mandatory subscription** — `sponsor_channels` table +
`/addsponsor` / `/delsponsor` / `/sponsors` admin commands.
`services/subscription.check_missing_subscriptions()` calls
`bot.get_chat_member()` for each active sponsor and returns the ones
the user hasn't joined; `keyboards.sponsors_keyboard()` renders a join
button per missing channel plus a "check again" button.
**Your bot must be an admin in every sponsor channel** — that's a
hard Telegram requirement for `getChatMember` to return accurate
results on channels the bot doesn't own.

**4. Security & anti-spam**
- *SQL injection*: `database.py` uses SQLAlchemy Core with bound
  parameters (`insert(...).values(...)`, `select(...).where(col == x)`)
  everywhere — there is no string-built SQL in this codebase, so raw
  user/admin input can never be interpreted as SQL.
- *Throttling*: `middlewares/throttling.py` drops repeat updates from
  the same user within `THROTTLE_RATE` seconds (default 0.7s), before
  they ever reach a handler or the DB. For multi-instance deployments,
  swap the in-memory dict for Redis (`SET key NX EX rate`).
- *Bans*: `middlewares/user_tracking.py` checks `is_banned` before any
  handler runs; `/ban` and `/unban` are admin-only.

**5. Userbot competitor monitor** — `userbot/monitor.py`, a
*separate* Pyrogram process. It listens on channels you list in
`SOURCE_CHANNELS`, strips captions, and writes new `file_id`s into the
same `movies` table the bot reads from. **Read the warnings in that
file before using it** — only monitor channels you're actually allowed
to re-publish from; this is a starting point, not a scraper aimed at
anyone else's content.

## Scaling notes
- Swap SQLite for Postgres for real concurrent load: set `DB_DSN` in
  `.env` to a `postgresql://...` URL — no application code changes
  needed, `database.py` already targets `asyncpg` automatically.
- Add an index-backed cache (e.g. Redis) in front of
  `get_movie_by_code` if you expect very hot/viral codes; the DB layer
  is already async so this is a drop-in addition inside that one
  function.
- Run behind a process manager (systemd / pm2 / Docker) with
  `bot.delete_webhook(drop_pending_updates=True)` + long polling as
  shipped, or switch `main.py` to a webhook (aiohttp `run_app`) once
  you have TLS in front of it.
