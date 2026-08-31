"""
Telegram Musiqa Aniqlovchi Botning asosiy ishga tushirish fayli (main entrypoint).
Dispatcher, Bot obyektlari va handler routerlarini birlashtiradi va pollingni boshlaydi.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config, setup_logging
from handlers import music_router, start_router

logger = logging.getLogger(__name__)


async def main() -> None:
    """Botni ishga tushiruvchi asosiy asinxron funksiya."""
    # 1. Konfiguratsiyani yuklash
    try:
        config = Config.load()
    except ValueError as err:
        # BOT_TOKEN mavjud bo'lmasa, darhol to'xtaydi
        print(f"XATOLIK: {err}", file=sys.stderr)
        sys.exit(1)

    # 2. Loggingni sozlash
    setup_logging(config.log_level)
    logger.info("Bot konfiguratsiyasi muvaffaqiyatli yuklandi.")

    # 3. Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Konfiguratsiyani barcha handlerlar uchun workflow data sifatida uzatish
    dp["config"] = config

    # 4. Routerlarni ro'yxatdan o'tkazish
    dp.include_router(start_router)
    dp.include_router(music_router)

    # 5. Pollingni ishga tushirish
    try:
        logger.info("Eski kutilayotgan xabarlar (pending updates) tozalanmoqda...")
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
        logging.info("Bot foydalanuvchi tomonidan to'xtatildi.")
