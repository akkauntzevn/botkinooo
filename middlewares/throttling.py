"""
Simple, dependency-light throttling middleware.

Blocks a user from triggering more than one handled update per
`rate` seconds. This is process-local (an in-memory TTL cache) which
is fine for a single-instance bot; if you horizontally scale the bot
behind a load balancer, back this with Redis instead (swap the
`_seen` dict for a Redis `SET key NX EX rate`).
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import config


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = None) -> None:
        self.rate = rate or config.THROTTLE_RATE
        self._last_seen: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is not None:
            now = time.monotonic()
            last = self._last_seen.get(user.id, 0.0)
            if now - last < self.rate:
                # Silently drop; for callbacks, ack so the button doesn't
                # look stuck. No handler is called -> no DB/API load.
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Juda tez! Biroz kuting...", show_alert=False)
                return None
            self._last_seen[user.id] = now

        return await handler(event, data)
