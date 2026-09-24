"""
Async data layer.

Built on SQLAlchemy Core (not the ORM) so that:
  * every query is a bound-parameter statement -> SQL injection is
    structurally impossible, regardless of what a user/admin types.
  * the exact same code runs against SQLite (aiosqlite) for dev/low
    load, or PostgreSQL (asyncpg) for high load, just by changing
    DB_DSN in .env. No query in this file needs to change.

NEVER build a query with an f-string / .format() / string
concatenation of user input. Always use bindparam-style values, as
done everywhere below.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional, Sequence

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import config

metadata = MetaData()

movies = Table(
    "movies",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("code", String(64), unique=True, nullable=False, index=True),
    Column("title", String(255), nullable=False),
    Column("file_id", Text, nullable=False),
    Column("file_type", String(20), nullable=False, default="video"),
    Column("caption", Text, nullable=True),
    Column("added_by", BigInteger, nullable=True),
    Column("views", Integer, nullable=False, default=0),
    Column("created_at", DateTime, default=dt.datetime.utcnow),
)

sponsor_channels = Table(
    "sponsor_channels",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chat_id", BigInteger, unique=True, nullable=False),
    Column("title", String(255), nullable=True),
    Column("username", String(255), nullable=True),  # without @, may be None for private
    Column("invite_link", Text, nullable=True),       # required if channel has no public username
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, default=dt.datetime.utcnow),
)

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tg_id", BigInteger, unique=True, nullable=False, index=True),
    Column("username", String(255), nullable=True),
    Column("first_name", String(255), nullable=True),
    Column("is_banned", Boolean, nullable=False, default=False),
    Column("joined_at", DateTime, default=dt.datetime.utcnow),
)


def _resolve_dsn() -> str:
    """Return an async-driver DSN. Falls back to local SQLite file."""
    if config.DB_DSN:
        dsn = config.DB_DSN
        # normalize plain postgres:// URLs to the asyncpg driver
        if dsn.startswith("postgresql://") and "+asyncpg" not in dsn:
            dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        return dsn
    return f"sqlite+aiosqlite:///{config.SQLITE_PATH}"


class Database:
    def __init__(self) -> None:
        self.engine: AsyncEngine = create_async_engine(_resolve_dsn(), pool_pre_ping=True)

    async def init_models(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()

    # ---------- movies ----------

    async def add_movie(
        self,
        code: str,
        title: str,
        file_id: str,
        added_by: int,
        file_type: str = "video",
        caption: Optional[str] = None,
    ) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                insert(movies).values(
                    code=code,
                    title=title,
                    file_id=file_id,
                    file_type=file_type,
                    caption=caption,
                    added_by=added_by,
                )
            )

    async def get_movie_by_code(self, code: str) -> Optional[dict]:
        async with self.engine.connect() as conn:
            row = (
                await conn.execute(select(movies).where(movies.c.code == code))
            ).mappings().first()
            return dict(row) if row else None
    async def get_next_movie_code(self) -> str:
        async with self.engine.connect() as conn:
            # Barcha kodlarni olib, eng kattasini topamiz va 1 ni qo'shamiz
            rows = (await conn.execute(select(movies.c.code))).all()
            max_code = 0
            for row in rows:
                code_str = row[0]
                if code_str.isdigit():
                    max_code = max(max_code, int(code_str))
            return str(max_code + 1)       

    async def increment_views(self, code: str) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                update(movies)
                .where(movies.c.code == code)
                .values(views=movies.c.views + 1)
            )

    async def delete_movie(self, code: str) -> bool:
        async with self.engine.begin() as conn:
            result = await conn.execute(delete(movies).where(movies.c.code == code))
            return result.rowcount > 0

    async def list_movies(self, limit: int = 50, offset: int = 0) -> Sequence[dict]:
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(movies).order_by(movies.c.id.desc()).limit(limit).offset(offset)
                )
            ).mappings().all()
            return [dict(r) for r in rows]

    # ---------- sponsor channels ("Homiylik") ----------

    async def add_sponsor(
        self,
        chat_id: int,
        title: Optional[str],
        username: Optional[str],
        invite_link: Optional[str],
    ) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                insert(sponsor_channels)
                .values(
                    chat_id=chat_id,
                    title=title,
                    username=username,
                    invite_link=invite_link,
                    is_active=True,
                )
            )

    async def remove_sponsor(self, chat_id: int) -> bool:
        async with self.engine.begin() as conn:
            result = await conn.execute(
                delete(sponsor_channels).where(sponsor_channels.c.chat_id == chat_id)
            )
            return result.rowcount > 0

    async def set_sponsor_active(self, chat_id: int, active: bool) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                update(sponsor_channels)
                .where(sponsor_channels.c.chat_id == chat_id)
                .values(is_active=active)
            )

    async def list_active_sponsors(self) -> Sequence[dict]:
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(sponsor_channels).where(sponsor_channels.c.is_active.is_(True))
                )
            ).mappings().all()
            return [dict(r) for r in rows]

    async def list_all_sponsors(self) -> Sequence[dict]:
        async with self.engine.connect() as conn:
            rows = (await conn.execute(select(sponsor_channels))).mappings().all()
            return [dict(r) for r in rows]

    # ---------- users ----------

    async def upsert_user(self, tg_id: int, username: Optional[str], first_name: Optional[str]) -> None:
        async with self.engine.begin() as conn:
            existing = (
                await conn.execute(select(users.c.id).where(users.c.tg_id == tg_id))
            ).first()
            if existing:
                await conn.execute(
                    update(users)
                    .where(users.c.tg_id == tg_id)
                    .values(username=username, first_name=first_name)
                )
            else:
                await conn.execute(
                    insert(users).values(tg_id=tg_id, username=username, first_name=first_name)
                )

    async def is_banned(self, tg_id: int) -> bool:
        async with self.engine.connect() as conn:
            row = (
                await conn.execute(select(users.c.is_banned).where(users.c.tg_id == tg_id))
            ).first()
            return bool(row[0]) if row else False

    async def ban_user(self, tg_id: int, banned: bool = True) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(update(users).where(users.c.tg_id == tg_id).values(is_banned=banned))

    async def user_count(self) -> int:
        async with self.engine.connect() as conn:
            from sqlalchemy import func

            row = (await conn.execute(select(func.count()).select_from(users))).first()
            return row[0] if row else 0


db = Database()
