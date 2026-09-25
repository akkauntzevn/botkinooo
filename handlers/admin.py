from __future__ import annotations
import asyncio
import re
from aiogram import Router, Bot, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database import Database
from filters.admin import IsAdmin

router = Router(name="admin")
router.message.filter(IsAdmin())  # Barcha buyruqlar faqat adminga ishlaydi


# ================= ADMIN PANEL TUGMALARI =================

def get_admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Homiylar ro'yxati", callback_data="admin_sponsors")],
        [
            InlineKeyboardButton(text="➕ Homiy qo'shish", callback_data="admin_add_sponsor"),
            InlineKeyboardButton(text="➖ Homiy o'chirish", callback_data="admin_del_sponsor")
        ],
        [InlineKeyboardButton(text="🎬 Kinolarni boshqarish", callback_data="admin_movie_help")]
    ])

@router.message(Command("admin", "panel"))
async def admin_panel_cmd(message: Message):
    await message.answer("👑 <b>Admin panelga xush kelibsiz!</b>\n\nNima qilamiz?", reply_markup=get_admin_panel_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(call: CallbackQuery, db: Database):
    action = call.data.split("_", 1)[1]
    
    if action == "stats":
        count = await db.user_count()
        await call.message.edit_text(f"👥 Jami foydalanuvchilar: {count}", reply_markup=get_admin_panel_kb())
        
    elif action == "sponsors":
        rows = await db.list_all_sponsors()
        if not rows:
            text = "🤷‍♂️ Hozircha homiy kanallar yo'q."
        else:
            lines = []
            for r in rows:
                status = "🟢" if r["is_active"] else "🔴"
                handle = f"@{r['username']}" if r["username"] else str(r["chat_id"])
                lines.append(f"{status} {r['title']} ({handle})")
            text = "<b>📢 Homiy kanallar ro'yxati:</b>\n\n" + "\n".join(lines)
        await call.message.edit_text(text, reply_markup=get_admin_panel_kb(), parse_mode="HTML")
        
    elif action == "add_sponsor":
        await call.answer("Homiy qo'shish", show_alert=False)
        await call.message.answer(
            "➕ <b>Homiy kanal qo'shish uchun:</b>\n\n"
            "Botni homiy kanalga admin qiling va quyidagi buyruqni yuboring (ustiga bossangiz nusxalaydi):\n\n"
            "<code>/addsponsor @kanal_username</code>",
            parse_mode="HTML"
        )
        
    elif action == "del_sponsor":
        await call.answer("Homiy o'chirish", show_alert=False)
        await call.message.answer(
            "➖ <b>Homiy kanalni o'chirish uchun:</b>\n\n"
            "Quyidagi buyruqni yuboring (ustiga bossangiz nusxalaydi):\n\n"
            "<code>/delsponsor @kanal_username</code>",
            parse_mode="HTML"
        )
        
    elif action == "movie_help":
        await call.answer("Kinolar bo'limi", show_alert=False)
        await call.message.answer(
            "🎬 <b>Kinolarni boshqarish:</b>\n\n"
            "<b>1. Kino qo'shish:</b> Videoni (yoki Baza kanaldagi videoni) botga tashlab, unga Reply (javob) qilib shunday yozing:\n"
            "<code>/setcode 1 | Kino nomi</code>\n\n"
            "<b>2. Kino o'chirish:</b>\n<code>/delmovie 1</code>\n\n"
            "<b>3. Bazadagi barcha kinolar ro'yxati:</b>\n<code>/movies</code>",
            parse_mode="HTML"
        )


# ================= KINOLARNI QABUL QILISH =================

@router.message(F.text.startswith("/setcode") | F.caption.startswith("/setcode"))
async def save_movie_file(message: Message, db: Database, bot: Bot):
    command_text = message.text if message.text else message.caption
    match = re.match(r"^/setcode\s+(\S+)\s*\|\s*(.+)$", command_text or "", re.DOTALL)
    
    if not match:
        await message.reply("❌ Format xato. Namuna:\n<code>/setcode 1 | Film nomi</code>", parse_mode="HTML")
        return

    code, title = match.group(1).strip(), match.group(2).strip()

    target_msg = message.reply_to_message if message.reply_to_message else message

    if target_msg.video:
        file_id, file_type = target_msg.video.file_id, "video"
    elif target_msg.animation:
        file_id, file_type = target_msg.animation.file_id, "animation"
    elif target_msg.document:
        file_id, file_type = target_msg.document.file_id, "document"
    else:
        await message.reply("❌ Xato! Buyruqni videoga javob (reply) qilib yozing.")
        return

    bot_info = await bot.get_me()
    clean_caption = f"🎬 {title}\n\n🤖 Bizning bot: @{bot_info.username}"

    try:
        await db.add_movie(
            code=code, title=title, file_id=file_id, 
            added_by=message.from_user.id, file_type=file_type, caption=clean_caption
        )
    except Exception as exc: 
        await message.reply(f"❌ Xatolik: {code} kodi allaqachon band yoki muammo yuz berdi.")
        return

    await message.reply(f"✅ Saqlandi!\nKod: <code>{code}</code>\nSarlavha: {title}", parse_mode="HTML")


@router.message(Command("delmovie"))
async def delete_movie(message: Message, command: CommandObject, db: Database):
    if not command.args:
        return
    ok = await db.delete_movie(command.args.strip())
    await message.reply("✅ O'chirildi." if ok else "❌ Bunday kod topilmadi.")

@router.message(Command("movies"))
async def list_movies(message: Message, db: Database):
    rows = await db.list_movies(limit=30)
    if not rows:
        await message.reply("Hozircha kinolar yo'q.")
        return
    text = "\n".join(f"• <code>{r['code']}</code> — {r['title']}" for r in rows)
    await message.reply(text, parse_mode="HTML")


# ================= BUYRUQLAR (Orqa fonda ishlash uchun) =================

@router.message(Command("addsponsor"))
async def add_sponsor(message: Message, command: CommandObject, bot: Bot, db: Database):
    if not command.args:
        return
    target = command.args.strip()
    try:
        chat = await bot.get_chat(target)
    except Exception:
        await message.reply("❌ Kanalni topolmadim. Bot kanalga admin qilinganligini tekshiring!")
        return

    username, invite_link = chat.username, None
    if username is None:
        try:
            invite_link = await bot.export_chat_invite_link(chat.id)
        except Exception:
            pass

    await db.add_sponsor(chat_id=chat.id, title=chat.title, username=username, invite_link=invite_link)
    await message.reply(f"✅ Homiy kanal qo'shildi: {chat.title}")

@router.message(Command("delsponsor"))
async def del_sponsor(message: Message, command: CommandObject, bot: Bot, db: Database):
    if not command.args:
        return
    target = command.args.strip()
    
    if target.startswith("@"):
        try:
            chat = await bot.get_chat(target)
            target_id = chat.id
        except Exception:
            await message.reply("❌ Bunday username bilan kanal topilmadi.")
            return
    else:
        try:
            target_id = int(target)
        except ValueError:
            return

    ok = await db.remove_sponsor(target_id)
    await message.reply("✅ Homiy kanal o'chirildi." if ok else "❌ Bu kanal homiylar ro'yxatida yo'q.")
    # ================= AVTOMATIK KANAL BAZASI =================

import asyncio

baza_lock = asyncio.Lock()

# O'z Baza kanalingiz ID raqamini shu yerga yozasiz (hozircha qanday topishni pastda o'rgataman)
BAZA_KANAL_ID = -1003960372964 

# 1. Kanal ID sini topish uchun yordamchi (Faqat bir marta ishlatamiz)
@router.channel_post(F.text.lower() == "id")
async def get_my_channel_id(message: Message):
    await message.edit_text(f"Bu kanalning ID raqami:\n\n<code>{message.chat.id}</code>", parse_mode="HTML")

# 2. Baza kanalga tashlangan videolarni 100% avtomat kodlash (hech qanday heshtegsiz!)
# 2. Baza kanalga tashlangan videolarni 100% avtomat kodlash (hech qanday heshtegsiz!)
@router.channel_post(F.chat.id == BAZA_KANAL_ID, F.video | F.document | F.animation)
# 2. Baza kanalga tashlangan videolarni 100% avtomat kodlash (Aqlli tozalash bilan)
@router.channel_post(F.chat.id == BAZA_KANAL_ID, F.video | F.document | F.animation)
async def auto_add_movie_from_baza(message: Message, db: Database, bot: Bot):
    import re
    async with baza_lock: 
        raw_caption = message.caption or ""
        
        # ------ AQLLI TOZALASH TIZIMI ------
        title = "Nomsiz kino"
        
        # 1-qadam: Agar eski matnda "Nomi: Isyonkor 3" degan joyi bo'lsa, faqat shuni kesib oladi
        match = re.search(r'(?:Nomi|nomi|Kino|kino):\s*([^\n]+)', raw_caption)
        if match:
            title = match.group(1).strip()
        else:
            # 2-qadam: Agar topolmasa, matndagi @, http, bot, kodi degan aralashmalari yo'q eng birinchi toza qatorni oladi
            lines = [line.strip() for line in raw_caption.split('\n') if line.strip()]
            clean_lines = [line for line in lines if not any(x in line.lower() for x in ['@', 'http', 'bot', 'kodi', 'ko\'rish', 'kanal'])]
            if clean_lines:
                title = clean_lines[0]
                
        # Ortiqcha emojilarni va ortiqcha probellarni tozalaymiz
        title = title.replace("🎬", "").replace("🔎", "").replace("🎞", "").strip()
        if len(title) > 60:
            title = title[:60] + "..."
        # -----------------------------------
        
        next_code = await db.get_next_movie_code()

        if message.video:
            file_id, file_type = message.video.file_id, "video"
        elif message.animation:
            file_id, file_type = message.animation.file_id, "animation"
        else:
            file_id, file_type = message.document.file_id, "document"
            
        bot_info = await bot.get_me()
        clean_caption = f"🎬 Nomi: {title}\n🤖 Bizning bot: @{bot_info.username}"

        await db.add_movie(
            code=next_code,
            title=title,
            file_id=file_id,
            added_by=0,
            file_type=file_type,
            caption=clean_caption
        )

        new_text = (
            f"🎬 <b>Nomi:</b> {title}\n"
            f"🔎 <b>Kino kodi:</b> <code>{next_code}</code>\n\n"
            f"🤖 <b>Botimiz:</b> @{bot_info.username}"
        )

        import asyncio
from aiogram import Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramRetryAfter
from database import db  # Baza yo'li to'g'riligini tekshiring

@router.message(Command("reklama"), IsAdmin())
async def send_broadcast(message: Message, bot: Bot):
    if not message.reply_to_message:
        await message.answer("❌ Yuborilishi kerak bo'lgan xabarga (rasm/video) javob (reply) qilib /reklama deb yozing.")
        return

    users = await db.get_all_user_ids()
    total = len(users)

    if total == 0:
        await message.answer("❌ Bazada foydalanuvchilar yo'q.")
        return

    status = await message.answer(f"⏳ **Reklama tarqatilmoqda...**\nJami: {total} kishi.")
    success, failed = 0, 0

    for user_id in users:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id
            )
            success += 1
            await asyncio.sleep(0.05)  # Spamdan himoya
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id
            )
            success += 1
        except Exception:
            failed += 1

    await status.edit_text(
        f"✅ **Tarqatish yakunlandi!**\n\n"
        f"📊 Jami: {total} ta\n"
        f"🟢 Muvaffaqiyatli: {success} ta\n"
        f"🔴 Botni bloklaganlar: {failed} ta"
    )
        
        await message.copy_to(chat_id=message.chat.id, caption=new_text, parse_mode="HTML")
        await message.delete()
        
        await asyncio.sleep(0.5)
