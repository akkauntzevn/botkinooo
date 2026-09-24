"""
"Homiylik" — dynamic mandatory subscription.

check_missing_subscriptions() hits Telegram's getChatMember once per
active sponsor channel and returns the ones the user is NOT a member
of. Handlers use this before releasing a movie's file_id.
"""
from __future__ import annotations

from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database import Database

NOT_MEMBER_STATUSES = {"left", "kicked"}


async def check_missing_subscriptions(bot: Bot, db: Database, user_id: int) -> List[dict]:
    sponsors = await db.list_active_sponsors()
    missing: List[dict] = []

    for sponsor in sponsors:
        chat_id = sponsor["chat_id"]
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in NOT_MEMBER_STATUSES:
                missing.append(sponsor)
        except TelegramForbiddenError:
            # Bot was kicked / lost admin rights in that sponsor channel —
            # don't hard-block real users because of an admin misconfig.
            continue
        except TelegramBadRequest:
            # e.g. user has never interacted with that chat, or chat_id is
            # stale — treat as "not a member" so the button still shows.
            missing.append(sponsor)

    return missing
