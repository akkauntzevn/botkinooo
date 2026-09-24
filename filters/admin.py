import os
from aiogram.filters import BaseFilter
from aiogram.types import Message

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        # .env fayldagi ADMIN_IDS ni o'qiydi va ro'yxatga aylantiradi
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if not admin_ids_str:
            return False
            
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]
        return message.from_user.id in admin_ids