"""
Telegram Musiqa Aniqlovchi Botning asosiy ishga tushirish fayli (main entrypoint).
Dispatcher, Bot obyektlari, handler routerlari, Health Check veb-serveri va 24/7 Keep-Alive tizimini o'z ichiga oladi.
"""

import asyncio
import logging
import os
import sys

import aiohttp
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


async def keep_alive_ping_loop(service_url: str, interval_seconds: int = 600) -> None:
    """
    Render.com bepul tarifida server 15 daqiqada uxlab qolmasligi uchun
    har 10 daqiqada o'ziga avtomatik ping yuborib turuvchi fon vazifasi.
    """
    if not service_url:
        return
    logger.info("Keep-Alive ping xizmati faollashdi: %s (Har %d soniyada)", service_url, interval_seconds)
    await asyncio.sleep(60)  # Ishga tushgandan 1 daqiqa o'tib boshlaydi

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(service_url, timeout=30) as resp:
                    logger.info("Keep-Alive ping yuborildi (Status: %s)", resp.status)
        except Exception as exc:
            logger.warning("Keep-Alive ping xatosi: %s", exc)
        await asyncio.sleep(interval_seconds)


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

    # 4. Server uxlab qolmasligi uchun Keep-Alive self-ping ishga tushirish
    service_url = (
        os.getenv("RENDER_EXTERNAL_URL")
        or os.getenv("SERVICE_URL")
        or "https://telegram-music-bot-4ht5.onrender.com"
    )
    asyncio.create_task(keep_alive_ping_loop(service_url, interval_seconds=600))

    # 5. Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["config"] = config

    # 6. Routerlarni ro'yxatdan o'tkazish
    dp.include_router(start_router)
    dp.include_router(music_router)

    # 7. Uzluksiz Pollingni ishga tushirish (avtomatik qayta ulanish bilan)
    logger.info("Eski kutilayotgan xabarlar tozalanmoqda...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as webhook_err:
        logger.warning("Webhook tozalashda ogohlantirish: %s", webhook_err)

    bot_user = await bot.get_me()
    logger.info("Bot muvaffaqiyatli ishga tushdi: @%s (%s)", bot_user.username, bot_user.first_name)
    logger.info("Polling boshlanmoqda...")

    while True:
        try:
            await dp.start_polling(bot)
        except Exception as exc:
            logger.error("Polling uzildi: %s. 3 soniyadan so'ng qayta ulanadi...", exc, exc_info=True)
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
