from __future__ import annotations

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from database import Database
from keyboards import sponsors_keyboard
from services.subscription import check_missing_subscriptions

router = Router(name="user")


def _extract_code(payload: str | None) -> str | None:
    """/start kino_105 -> '105'. Returns None if there's no valid deep-link payload."""
    if not payload:
        return None
    prefix = config.DEEPLINK_PREFIX
    if payload.startswith(prefix):
        code = payload[len(prefix):].strip()
        return code or None
    return None


async def _deliver_movie(bot: Bot, db: Database, chat_id: int, code: str) -> None:
    movie = await db.get_movie_by_code(code)
    if not movie:
        # Xatolik xabari rasmdagidek o'zgartirildi
        await bot.send_message(chat_id, "❌ Kino kodini noto'g'ri yubordingiz!")
        return

    # Ko'rishlar sonini shu yerda bittaga oshirib olamiz
    await db.increment_views(code)
    
    title = movie.get("title", "Noma'lum")
    views_count = movie.get("views", 0) + 1  # Foydalanuvchining hozirgi ko'rishi ham hisobga olinadi
    file_type = movie["file_type"]
    file_id = movie["file_id"]

    bot_info = await bot.get_me()
    
    # Rasmdagidek chiroyli matn shakllantiriladi
    caption = (
        f"🔎 <b>Kino kodi:</b> {code}\n\n"
        f"🎬 <b>Nomi:</b> {title}\n\n"
        f"🤖 <b>Botimiz:</b> @{bot_info.username}\n\n"
        f"👁 <b>Ko'rishlar:</b> {views_count} ta"
    )
    
    # Ulashish tugmasi uchun tayyor ssilka yasaladi
    deep_link = f"{config.DEEPLINK_PREFIX}{code}"
    share_text = "Sizga ushbu kinoni ko'rishni maslahat beraman!"
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_info.username}?start={deep_link}&text={share_text}"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↗️ Ulashish", url=share_url)]
    ])

    # Faylni tugma va chiroyli matn bilan yuborish
    if file_type == "video":
        await bot.send_video(chat_id, video=file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
    elif file_type == "document":
        await bot.send_document(chat_id, document=file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
    elif file_type == "animation":
        await bot.send_animation(chat_id, animation=file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
    else:
        await bot.send_video(chat_id, video=file_id, caption=caption, reply_markup=markup, parse_mode="HTML")


@router.message(CommandStart(deep_link=True))
async def start_with_deeplink(message: Message, command: CommandObject, bot: Bot, db: Database):
    code = _extract_code(command.args)
    if code is None:
        await start_plain(message)
        return

    missing = await check_missing_subscriptions(bot, db, message.from_user.id)
    if missing:
        await message.answer(
            "🔒 Kinoni ko'rish uchun quyidagi kanallarga a'zo bo'ling, "
            "so'ng \"Tekshirish\" tugmasini bosing:",
            reply_markup=sponsors_keyboard(missing, pending_code=code),
        )
        return

    await _deliver_movie(bot, db, message.chat.id, code)


@router.message(CommandStart())
async def start_plain(message: Message):
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        "Kino kodini yuboring (masalan: 105) yoki TikTok'dagi havola orqali kirdingiz bo'lsa, "
        "kino avtomatik ochiladi."
    )


@router.message(F.text.regexp(r"^\d{1,10}$"))
async def get_movie_by_plain_code(message: Message, bot: Bot, db: Database):
    """Lets users just type a numeric code instead of using a deep link."""
    code = message.text.strip()
    missing = await check_missing_subscriptions(bot, db, message.from_user.id)
    if missing:
        await message.answer(
            "🔒 Avval quyidagi kanallarga a'zo bo'ling:",
            reply_markup=sponsors_keyboard(missing, pending_code=code),
        )
        return
    await _deliver_movie(bot, db, message.chat.id, code)


@router.callback_query(F.data.startswith("checksub:"))
async def recheck_subscription(callback: CallbackQuery, bot: Bot, db: Database):
    code = callback.data.split(":", 1)[1]
    code = None if code == "-" else code

    missing = await check_missing_subscriptions(bot, db, callback.from_user.id)
    if missing:
        await callback.answer("❗️ Hali barcha kanallarga a'zo bo'lmagansiz.", show_alert=True)
        return

    await callback.answer("✅ Rahmat!")
    if callback.message:
        await callback.message.delete()
    if code:
        await _deliver_movie(bot, db, callback.message.chat.id, code)
    else:
        await bot.send_message(callback.from_user.id, "✅ Obuna tasdiqlandi! Endi kino kodini yuboring.")