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
            
            # Agar foydalanuvchi kanalda bo'lmasa yoki chiqib ketgan bo'lsa
            if member.status in NOT_MEMBER_STATUSES:
                # Zayafka (join request) tashlaganligini tekshiramiz
                is_requested = False
                if hasattr(db, "has_user_requested"):
                    is_requested = await db.has_user_requested(chat_id, user_id)
                
                # Agar zayafka ham tashlamagan bo'lsa, ro'yxatga qo'shamiz
                if not is_requested:
                    missing.append(sponsor)
                    
        except TelegramForbiddenError:
            # Bot was kicked / lost admin rights in that sponsor channel
            continue
        except TelegramBadRequest:
            # e.g. user has never interacted with that chat
            # Bu yerda ham zayafkani tekshirib ko'ramiz
            is_requested = False
            if hasattr(db, "has_user_requested"):
                is_requested = await db.has_user_requested(chat_id, user_id)
            
            if not is_requested:
                missing.append(sponsor)

    return missing
