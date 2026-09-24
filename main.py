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
