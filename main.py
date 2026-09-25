import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database import db
from middlewares.throttling import ThrottlingMiddleware
from middlewares.user_tracking import UserTrackingMiddleware
from handlers import user as user_handlers
from handlers import admin as admin_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await db.init_models()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # `db` is injected into every handler's kwargs automatically because
    # aiogram passes workflow_data through; we also set it explicitly here
    # so handlers can just declare `db: Database` as a parameter.
    dp["db"] = db

    # Order matters: throttle first (cheapest check, drops spam before
    # touching the DB), then track/ban-check, then the real handlers.
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware(rate=0.3))
    dp.message.middleware(UserTrackingMiddleware(db))
    dp.callback_query.middleware(UserTrackingMiddleware(db))

    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    try:
        logger.info("Bot ishga tushdi (polling)...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("To'xtatildi.")
        import os
import os
import asyncio
from pyrogram import Client, filters, compose

API_ID = "36791344"
API_HASH = "09c64ddf1cf1b8c89c16985ce19ee3c4"
BOT_TOKEN = "8604371339:AAHNtM1q9yj9fQn_bVD2Y0PFzyxtvQ3nAiY"

# ... qolgan kodlar o'zgarishsiz qoladi ...


user = Client("my_account", api_id=API_ID, api_hash=API_HASH)
bot = Client("stealer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply("🔥 Bot ishga tushdi!\nKino tortish uchun: `/ol bot_nomi kino_id`")

@bot.on_message(filters.command("ol"))
async def get_movie(client, message):
    try:
        args = message.text.split()
        nishon_bot = args[1].replace("@", "")
        kino_id = int(args[2])
        
        msg = await user.get_messages(nishon_bot, kino_id)
        m = await message.reply("⏳ Railway xotirasiga tortilmoqda...")
        
        file_path = await msg.download()
        await m.edit("🚀 Baza botingizga yuborilmoqda...")
        
        await user.send_video(
            chat_id="Kinoteka24_bot",
            video=file_path,
            caption="🍿 Yangi kino tayyor!\nBizning bot: @Kinoteka24_bot"
        )
        os.remove(file_path)
        await m.edit("✅ Missiya bajarildi!")
    except Exception as e:
        await message.reply(f"❌ Xatolik: {e}")

async def main():
    await compose([user, bot])

asyncio.run(main())

