"""
Musiqa, Video va Remix variantlarini qayta ishlash handleri.
Instagram va YouTube havolalarini qabul qiladi, video va audioni yuklaydi,
Shazam orqali aniqlaydi hamda Remix/SpeedUp/Slowed variantlarini taqdim etadi.
"""

import html
import logging
import os
import tempfile
import uuid
from typing import Dict, Optional, Tuple

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import Config
from services.downloader import (
    AudioSizeLimitError,
    DownloaderException,
    DownloaderTimeoutError,
    MediaResult,
    VideoUnavailableError,
    download_media,
    search_and_download_audio,
)
from services.recognizer import TrackInfo, recognize_music
from utils.validators import extract_valid_url

logger = logging.getLogger(__name__)
music_router = Router(name="music_router")

# Remix qidiruv so'rovlarini saqlash uchun kesh (CallbackData 64 baytdan oshmasligi uchun)
REMIX_CACHE: Dict[str, Tuple[str, str]] = {}


def _create_remix_keyboard(track_name: str) -> InlineKeyboardMarkup:
    """Remix va boshqa audio variantlar uchun Inline tugmalar klaviaturasini yaratadi."""
    key_remix = str(uuid.uuid4())[:8]
    key_speedup = str(uuid.uuid4())[:8]
    key_slowed = str(uuid.uuid4())[:8]
    key_cover = str(uuid.uuid4())[:8]

    REMIX_CACHE[key_remix] = (track_name, "remix")
    REMIX_CACHE[key_speedup] = (track_name, "speed up")
    REMIX_CACHE[key_slowed] = (track_name, "slowed reverb")
    REMIX_CACHE[key_cover] = (track_name, "cover acoustic")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎧 Remix", callback_data=f"rmx:{key_remix}"),
                InlineKeyboardButton(text="⚡ Speed Up", callback_data=f"rmx:{key_speedup}"),
            ],
            [
                InlineKeyboardButton(text="🌙 Slowed + Reverb", callback_data=f"rmx:{key_slowed}"),
                InlineKeyboardButton(text="🎸 Cover / Acoustic", callback_data=f"rmx:{key_cover}"),
            ],
        ]
    )
    return keyboard


@music_router.message(F.text)
async def handle_music_link(message: Message, config: Config) -> None:
    """
    Foydalanuvchidan kelgan matnli xabarni tekshiradi, video va audioni yuklab, Shazam qiladi.
    """
    text = message.text or ""
    url = extract_valid_url(text)

    if not url:
        if not text.startswith("/"):
            await message.answer(
                "❌ <b>Noto'g'ri havola yuborildi!</b>\n\n"
                "Iltimos, faqat <b>Instagram</b> (Reels, Post) yoki "
                "<b>YouTube</b> (Video, Shorts) havolasini yuboring.\n\n"
                "<i>Namuna:</i>\n"
                "• <code>https://www.instagram.com/reel/Cxxxxxx/</code>\n"
                "• <code>https://youtu.be/xxxxxxxxxxx</code>\n"
                "• <code>https://www.youtube.com/watch?v=xxxxxxxxxxx</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    status_msg = await message.answer("⏳ <i>Video va audio yuklab olinmoqda...</i>", parse_mode=ParseMode.HTML)
    tmpdir_obj: Optional[tempfile.TemporaryDirectory] = None

    try:
        tmpdir_obj = tempfile.TemporaryDirectory()
        tmpdir = tmpdir_obj.name

        # 1. Video va audioni yuklash
        await status_msg.edit_text("⏳ <i>Video yuklanmoqda va audio ajratilmoqda...</i>", parse_mode=ParseMode.HTML)

        media: MediaResult = await download_media(
            url=url,
            output_dir=tmpdir,
            timeout_seconds=config.download_timeout_seconds,
            max_size_mb=config.max_audio_size_mb,
        )

        if not media.audio_path:
            raise DownloaderException("Audioni ajratib bo'lmadi.")

        # 2. Shazam orqali musiqani aniqlash
        await status_msg.edit_text("🔍 <i>Qo'shiq Shazam orqali aniqlanmoqda...</i>", parse_mode=ParseMode.HTML)

        track_info: Optional[TrackInfo] = await recognize_music(
            audio_path=media.audio_path,
            timeout_seconds=config.recognition_timeout_seconds,
        )

        # 3. Agar video mavjud bo'lsa, avval videoni yuboramiz
        if media.video_path and os.path.exists(media.video_path):
            await status_msg.edit_text("🎬 <i>Video yuborilmoqda...</i>", parse_mode=ParseMode.HTML)
            video_caption = (
                f"🎬 <b>Yuklab olingan video</b>\n"
                f"🔗 <a href=\"{url}\">Asl havola</a>"
            )
            try:
                await message.answer_video(
                    video=FSInputFile(media.video_path),
                    caption=video_caption,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as vid_send_err:
                logger.warning("Video jo'natishda xatolik: %s", vid_send_err)

        # 4. Asl audio faylni jo'natish
        await status_msg.edit_text("🎧 <i>Audio fayl tayyorlanmoqda...</i>", parse_mode=ParseMode.HTML)

        if track_info:
            caption = (
                f"🎵 Nomi: <b>{html.escape(track_info.title)}</b>\n"
                f"👤 Ijrochi: <b>{html.escape(track_info.subtitle)}</b>\n\n"
                f"👇 <i>Qo'shiqning boshqa variantlarini yuklash uchun tugmalardan foydalaning:</i>"
            )
            title = track_info.title
            performer = track_info.subtitle
            search_base = f"{track_info.subtitle} {track_info.title}"
        else:
            title_name = media.title or "Audio Track"
            caption = (
                "⚠️ <i>Qo'shiq nomi Shazam orqali aniqlanmadi, lekin audio yuklab olindi.</i>\n\n"
                f"👇 <i>Ushbu video musiqasining boshqa variantlarini yuklash:</i>"
            )
            title = title_name
            performer = "Instagram / YouTube"
            search_base = title_name

        audio_file = FSInputFile(
            path=media.audio_path,
            filename=f"{title}.mp3",
        )

        # Remix tugmalari
        remix_keyboard = _create_remix_keyboard(search_base)

        await message.answer_audio(
            audio=audio_file,
            caption=caption,
            title=title,
            performer=performer,
            reply_markup=remix_keyboard,
            parse_mode=ParseMode.HTML,
        )

        # Status xabarini tozalash
        try:
            await status_msg.delete()
        except Exception:
            pass

    except VideoUnavailableError:
        await status_msg.edit_text(
            "❌ <b>Videoni yuklab bo'lmadi!</b>\n\n"
            "Video topilmadi, o'chirilgan yoki akkaunt yopiq (private) bo'lishi mumkin.",
            parse_mode=ParseMode.HTML,
        )

    except AudioSizeLimitError:
        await status_msg.edit_text(
            f"⚠️ <b>Fayl hajmi juda katta!</b>\n\n"
            f"Fayl hajmi {config.max_audio_size_mb} MB limitdan oshib ketdi.",
            parse_mode=ParseMode.HTML,
        )

    except DownloaderTimeoutError:
        await status_msg.edit_text(
            "⏳ <b>Vaqt tugadi (Timeout)!</b>\n\n"
            "Serverdan yuklab olish juda ko'p vaqt oldi. Iltimos, qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML,
        )

    except DownloaderException as exc:
        await status_msg.edit_text(
            f"❌ <b>Xatolik yuz berdi:</b>\n<code>{html.escape(str(exc))}</code>",
            parse_mode=ParseMode.HTML,
        )

    except Exception as exc:
        logger.error("Kutilmagan xatolik: %s", exc, exc_info=True)
        await status_msg.edit_text(
            "❌ <b>Kutilmagan xatolik yuz berdi!</b>\nIltimos, qaytadan urinib ko'ring.",
            parse_mode=ParseMode.HTML,
        )

    finally:
        if tmpdir_obj is not None:
            try:
                tmpdir_obj.cleanup()
            except Exception:
                pass


@music_router.callback_query(F.data.startswith("rmx:"))
async def handle_remix_callback(callback: CallbackQuery, config: Config) -> None:
    """Foydalanuvchi Remix / SpeedUp / Slowed tugmasini bosganda ishlovchi handler."""
    data_key = callback.data.split(":", 1)[1] if callback.data else ""
    cached = REMIX_CACHE.get(data_key)

    if not cached:
        await callback.answer("⚠️ So'rov muddati o'tgan. Iltimos, qaytadan havola yuboring.", show_alert=True)
        return

    base_query, variant = cached
    full_query = f"{base_query} {variant}"

    await callback.answer(f"⏳ '{variant.capitalize()}' varianti qidirilmoqda...", show_alert=False)

    status_msg = await callback.message.answer(
        f"🔍 <i>'{html.escape(full_query)}' YouTube'dan qidirilmoqda va yuklanmoqda...</i>",
        parse_mode=ParseMode.HTML,
    )

    tmpdir_obj: Optional[tempfile.TemporaryDirectory] = None
    try:
        tmpdir_obj = tempfile.TemporaryDirectory()
        tmpdir = tmpdir_obj.name

        audio_path, video_title = await search_and_download_audio(
            query=full_query,
            output_dir=tmpdir,
            timeout_seconds=config.download_timeout_seconds,
            max_size_mb=config.max_audio_size_mb,
        )

        audio_file = FSInputFile(
            path=audio_path,
            filename=f"{video_title}.mp3",
        )

        caption = (
            f"🎵 Nomi: <b>{html.escape(video_title)}</b>\n"
            f"✨ Turi: <b>{variant.upper()}</b>"
        )

        await callback.message.answer_audio(
            audio=audio_file,
            caption=caption,
            title=video_title,
            performer=variant.upper(),
            parse_mode=ParseMode.HTML,
        )

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as exc:
        logger.error("Remix yuklashda xatolik: %s", exc, exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>'{html.escape(variant.capitalize())}' variantini yuklab bo'lmadi:</b>\n"
            f"<code>{html.escape(str(exc))}</code>",
            parse_mode=ParseMode.HTML,
        )

    finally:
        if tmpdir_obj is not None:
            try:
                tmpdir_obj.cleanup()
            except Exception:
                pass
