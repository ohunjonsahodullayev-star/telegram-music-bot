"""
Start va Help komandalari uchun handlerlar.
Foydalanuvchilarga bot haqida ma'lumot va yo'riqnoma beradi.
"""

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

start_router = Router(name="start_router")


@start_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    /start komandasi uchun handler.
    Foydalanuvchini tabriklaydi va botdan foydalanish bo'yicha qisqacha ma'lumot beradi.
    """
    first_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>! 👋\n\n"
        f"🤖 <b>Instagram & YouTube Musiqa Aniqlovchi Botiga xush kelibsiz!</b>\n\n"
        f"Menga <b>Instagram</b> (Reel/Post) yoki <b>YouTube</b> (Video/Shorts) havolasini yuboring. "
        f"Men quyidagilarni bajaraman:\n"
        f"1. 📥 Videodan audioni (MP3 formatda) yuklab olaman\n"
        f"2. 🔍 <b>Shazam</b> orqali fondagi qo'shiq nomi va ijrochisini aniqlayman\n"
        f"3. 🎧 Sizga tayyor audio fayl va musiqa ma'lumotlarini taqdim etaman!\n\n"
        f"💡 <i>Sinab ko'rish uchun hoziroq biror video havolasini yuboring!</i>\n"
        f"Yordam olish uchun: /help"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)


@start_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    /help komandasi uchun handler.
    Qo'llab-quvvatlanadigan platformalar va qoidalar haqida batafsil ma'lumot beradi.
    """
    help_text = (
        "📖 <b>Botdan foydalanish qo'llanmasi</b>\n\n"
        "<b>Qo'llab-quvvatlanadigan platformalar:</b>\n"
        "• 📸 <b>Instagram:</b> Reels, Postlar, IGTV havolalari\n"
        "• 🎥 <b>YouTube:</b> Oddiy videolar, Shorts, qisqa <code>youtu.be</code> havolalari\n\n"
        "<b>Qanday ishlatiladi?</b>\n"
        "Shunchaki videoga havola (link) nusxasini oling va botga yuboring.\n\n"
        "<b>Muhim eslatmalar:</b>\n"
        "⚠️ Instagram'da faqat <b>ochiq (public)</b> akkauntlardagi videolardan audio yuklanadi.\n"
        "⚠️ Telegram cheklovi tufayli audio hajmi <b>50 MB</b> dan oshmasligi kerak.\n"
        "⚠️ Agar fonda musiqa juda shovqinli yoki qisqa bo'lsa, Shazam aniqlay olmasligi mumkin, "
        "lekin audio baribir sizga yetkaziladi."
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)
