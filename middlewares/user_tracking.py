from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from database import Database


class UserTrackingMiddleware(BaseMiddleware):
    """Upserts the user row and blocks banned users before any handler runs."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        if user is not None:
            if await self.db.is_banned(user.id):
                return None
            await self.db.upsert_user(user.id, user.username, user.first_name)

        return await handler(event, data)
