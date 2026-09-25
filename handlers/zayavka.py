from aiogram import Router, Bot
from aiogram.types import ChatJoinRequest
from database import db

router = Router()

@router.chat_join_request()
async def auto_save_new_member(request: ChatJoinRequest, bot: Bot):
    user = request.from_user
    
    # Zayavka tashlagan odamni darhol bazaga yozamiz
    await db.upsert_user(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    try:
        await bot.send_message(
            chat_id=user.id,
            text="✅ Kanalga ruxsat so'rovingiz qabul qilindi!\n\nKino ko'rish uchun uning kodini yuboring."
        )
    except Exception:
        pass
