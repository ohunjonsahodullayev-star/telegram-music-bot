"""
Telegram Musiqa Aniqlovchi Botning asosiy ishga tushirish fayli (main entrypoint).
Dispatcher, Bot obyektlari, handler routerlari va Render.com uchun Health Check veb-serverini o'z ichiga oladi.
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import Config, setup_logging
from handlers import music_router, start_router

logger = logging.getLogger(__name__)


async def handle_health_check(request: web.Request) -> web.Response:
    """Render.com yoki bulutli serverlar uchun Health Check javobi."""
    return web.Response(text="Bot 24/7 faol ishlamoqda! 🚀", status=200)


async def start_health_check_server(port: int = 8080) -> None:
    """Render Web Service talab qiladigan minimal HTTP serverni orqa fonda ishga tushirish."""
    try:
        app = web.Application()
        app.router.add_get("/", handle_health_check)
        app.router.add_get("/health", handle_health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info("Health Check veb-serveri %d-portda ishga tushdi.", port)
    except Exception as err:
        logger.warning("Veb-serverni ishga tushirishda ogohlantirish: %s", err)


async def main() -> None:
    """Botni ishga tushiruvchi asosiy asinxron funksiya."""
    # 1. Konfiguratsiyani yuklash
    try:
        config = Config.load()
    except ValueError as err:
        print(f"XATOLIK: {err}", file=sys.stderr)
        sys.exit(1)

    # 2. Loggingni sozlash
    setup_logging(config.log_level)
    logger.info("Bot konfiguratsiyasi muvaffaqiyatli yuklandi.")

    # 3. Render.com / Bulutli serverlar uchun port ochish
    port = int(os.getenv("PORT", "8080"))
    await start_health_check_server(port)

    # 4. Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp["config"] = config

    # 5. Routerlarni ro'yxatdan o'tkazish
    dp.include_router(start_router)
    dp.include_router(music_router)

    # 6. Pollingni ishga tushirish
    try:
        logger.info("Eski kutilayotgan xabarlar tozalanmoqda...")
        await bot.delete_webhook(drop_pending_updates=True)

        bot_user = await bot.get_me()
        logger.info("Bot muvaffaqiyatli ishga tushdi: @%s (%s)", bot_user.username, bot_user.first_name)
        logger.info("Polling boshlanmoqda...")

        await dp.start_polling(bot)
    except Exception as exc:
        logger.critical("Bot ishlashida jiddiy xatolik: %s", exc, exc_info=True)
    finally:
        logger.info("Bot sessiyasi yopilmoqda...")
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
