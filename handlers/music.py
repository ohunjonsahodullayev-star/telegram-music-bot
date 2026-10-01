"""
Musiqa, Video va Qidiruv handleri.
1. Instagram va YouTube havolalaridan video (MP4) va toza audio (MP3) yuklaydi va Shazam orqali aniqlaydi.
2. Matn (qo'shiq nomi/ijrochi) yuborilganda, to'g'ridan-to'g'ri YouTube'dan musiqani qidirib, tayyor MP3 qilib beradi.
3. Remix, Speed Up, Slowed, Acoustic variantlarini taqdim etadi.
"""

import html
import logging
import os
import re
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

# Remix qidiruv so'rovlarini saqlash uchun kesh
REMIX_CACHE: Dict[str, Tuple[str, str]] = {}


def _sanitize_filename(name: str) -> str:
    """Fayl nomi uchun xavfli belgilarni olib tashlaydi."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return clean[:60] if clean else "audio"


def _create_remix_keyboard(track_name: str) -> InlineKeyboardMarkup:
    """Remix variantlari uchun Inline tugmalar."""
    key_remix = str(uuid.uuid4())[:8]
    key_speedup = str(uuid.uuid4())[:8]
    key_slowed = str(uuid.uuid4())[:8]
    key_cover = str(uuid.uuid4())[:8]

    clean_track = track_name[:80]
    REMIX_CACHE[key_remix] = (clean_track, "remix")
    REMIX_CACHE[key_speedup] = (clean_track, "speed up")
    REMIX_CACHE[key_slowed] = (clean_track, "slowed reverb")
    REMIX_CACHE[key_cover] = (clean_track, "cover acoustic")

    return InlineKeyboardMarkup(
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


@music_router.message(F.text)
async def handle_music_message(message: Message, config: Config) -> None:
    """
    Foydalanuvchi yuborgan xabarni qayta ishlaydi:
    - Agar havola (Instagram/YouTube) bo'lsa: Video va Audio yuklaydi.
    - Agar matn (qo'shiq nomi) bo'lsa: To'g'ridan-to'g'ri musiqani qidirib topadi va MP3 yuklaydi.
    """
    text = (message.text or "").strip()
    if text.startswith("/"):
        return

    url = extract_valid_url(text)

    # ==========================================
    # 1. HAVOLA YUBORILGAN HOLAT (Instagram / YouTube)
    # ==========================================
    if url:
        status_msg = await message.answer("⏳ <i>Video va audio yuklab olinmoqda...</i>", parse_mode=ParseMode.HTML)
        tmpdir_obj: Optional[tempfile.TemporaryDirectory] = None

        try:
            tmpdir_obj = tempfile.TemporaryDirectory()
            tmpdir = tmpdir_obj.name

            # Video va audio yuklash
            media: MediaResult = await download_media(
                url=url,
                output_dir=tmpdir,
                timeout_seconds=config.download_timeout_seconds,
                max_size_mb=config.max_audio_size_mb,
            )

            if not media.audio_path or not os.path.exists(media.audio_path):
                raise DownloaderException("Audioni ajratib bo'lmadi.")

            # Shazam orqali aniqlash
            await status_msg.edit_text("🔍 <i>Qo'shiq Shazam orqali aniqlanmoqda...</i>", parse_mode=ParseMode.HTML)
            track_info: Optional[TrackInfo] = await recognize_music(
                audio_path=media.audio_path,
                timeout_seconds=config.recognition_timeout_seconds,
            )

            # Agar video mavjud bo'lsa, videoni yuborish
            if media.video_path and os.path.exists(media.video_path):
                await status_msg.edit_text("🎬 <i>Video yuborilmoqda...</i>", parse_mode=ParseMode.HTML)
                safe_url = html.escape(url, quote=True)
                video_caption = f"🎬 <b>Yuklab olingan video</b>\n🔗 <a href=\"{safe_url}\">Asl havola</a>"
                try:
                    await message.answer_video(
                        video=FSInputFile(media.video_path),
                        caption=video_caption,
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    try:
                        await message.answer_video(video=FSInputFile(media.video_path))
                    except Exception:
                        pass

            # Audio faylni jo'natish
            await status_msg.edit_text("🎧 <i>Audio fayl tayyorlanmoqda...</i>", parse_mode=ParseMode.HTML)

            if track_info:
                caption = (
                    f"🎵 Nomi: <b>{html.escape(track_info.title)}</b>\n"
                    f"👤 Ijrochi: <b>{html.escape(track_info.subtitle)}</b>\n\n"
                    f"👇 <i>Variantlarni yuklash:</i>"
                )
                title = track_info.title
                performer = track_info.subtitle
                search_base = f"{track_info.subtitle} {track_info.title}"
            else:
                title_name = media.title or "Audio Track"
                caption = (
                    f"🎵 Nomi: <b>{html.escape(title_name)}</b>\n\n"
                    f"👇 <i>Variantlarni yuklash:</i>"
                )
                title = title_name
                performer = "YouTube / Instagram"
                search_base = title_name

            safe_filename = f"{_sanitize_filename(title)}.mp3"
            audio_file = FSInputFile(path=media.audio_path, filename=safe_filename)
            remix_keyboard = _create_remix_keyboard(search_base)

            try:
                await message.answer_audio(
                    audio=audio_file,
                    caption=caption,
                    title=title[:60],
                    performer=performer[:60],
                    reply_markup=remix_keyboard,
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                await message.answer_audio(
                    audio=FSInputFile(path=media.audio_path, filename="audio.mp3"),
                    reply_markup=remix_keyboard,
                )

            try:
                await status_msg.delete()
            except Exception:
                pass

        except VideoUnavailableError:
            await status_msg.edit_text("❌ <b>Video topilmadi, o'chirilgan yoki yopiq akkauntda.</b>", parse_mode=ParseMode.HTML)
        except AudioSizeLimitError:
            await status_msg.edit_text(f"⚠️ <b>Fayl hajmi {config.max_audio_size_mb} MB limitdan oshdi.</b>", parse_mode=ParseMode.HTML)
        except DownloaderTimeoutError:
            await status_msg.edit_text("⏳ <b>Vaqt tugadi. Iltimos, qayta urinib ko'ring.</b>", parse_mode=ParseMode.HTML)
        except DownloaderException as exc:
            await status_msg.edit_text(f"❌ <b>Yuklab olishda xatolik:</b>\n<code>{html.escape(str(exc))}</code>", parse_mode=ParseMode.HTML)
        except Exception as exc:
            logger.error("Xatolik: %s", exc, exc_info=True)
            await status_msg.edit_text("⚠️ <b>Yuklab olishda xatolik yuz berdi.</b>", parse_mode=ParseMode.HTML)
        finally:
            if tmpdir_obj is not None:
                try:
                    tmpdir_obj.cleanup()
                except Exception:
                    pass

    # ==========================================
    # 2. MATN (QO'SHIQ NOMI) YUBORILGAN HOLAT (Musiqa qidiruvi)
    # ==========================================
    else:
        status_msg = await message.answer(f"🔍 <i>«{html.escape(text)}» bo'yicha musiqa qidirilmoqda...</i>", parse_mode=ParseMode.HTML)
        tmpdir_obj: Optional[tempfile.TemporaryDirectory] = None

        try:
            tmpdir_obj = tempfile.TemporaryDirectory()
            tmpdir = tmpdir_obj.name

            audio_path, video_title = await search_and_download_audio(
                query=text,
                output_dir=tmpdir,
                timeout_seconds=config.download_timeout_seconds,
                max_size_mb=config.max_audio_size_mb,
            )

            # Shazam orqali qo'shiqni aniqlash
            track_info = await recognize_music(
                audio_path=audio_path,
                timeout_seconds=config.recognition_timeout_seconds,
            )

            if track_info:
                title = track_info.title
                performer = track_info.subtitle
                search_base = f"{track_info.subtitle} {track_info.title}"
                caption = (
                    f"🎵 Nomi: <b>{html.escape(track_info.title)}</b>\n"
                    f"👤 Ijrochi: <b>{html.escape(track_info.subtitle)}</b>\n\n"
                    f"👇 <i>Variantlarni yuklash:</i>"
                )
            else:
                title = video_title
                performer = "Musiqa"
                search_base = video_title
                caption = (
                    f"🎵 Nomi: <b>{html.escape(video_title)}</b>\n\n"
                    f"👇 <i>Variantlarni yuklash:</i>"
                )

            safe_filename = f"{_sanitize_filename(title)}.mp3"
            audio_file = FSInputFile(path=audio_path, filename=safe_filename)
            remix_keyboard = _create_remix_keyboard(search_base)

            try:
                await message.answer_audio(
                    audio=audio_file,
                    caption=caption,
                    title=title[:60],
                    performer=performer[:60],
                    reply_markup=remix_keyboard,
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                await message.answer_audio(
                    audio=FSInputFile(path=audio_path, filename="music.mp3"),
                    reply_markup=remix_keyboard,
                )

            try:
                await status_msg.delete()
            except Exception:
                pass

        except Exception as exc:
            logger.error("Musiqa qidiruvida xatolik: %s", exc)
            await status_msg.edit_text(f"❌ <b>«{html.escape(text)}»</b> bo'yicha musiqa topilmadi.", parse_mode=ParseMode.HTML)
        finally:
            if tmpdir_obj is not None:
                try:
                    tmpdir_obj.cleanup()
                except Exception:
                    pass


@music_router.callback_query(F.data.startswith("rmx:"))
async def handle_remix_callback(callback: CallbackQuery, config: Config) -> None:
    """Remix, Speed Up, Slowed yoki Cover tugmalari bosilganda ishlovchi handler."""
    await callback.answer("Qidiruv boshlandi...")
    cache_key = callback.data.split(":", 1)[1]

    if cache_key not in REMIX_CACHE:
        await callback.message.reply("⚠️ <i>Tugma muddati tugagan. Havolani qayta yuboring.</i>", parse_mode=ParseMode.HTML)
        return

    base_query, variant = REMIX_CACHE[cache_key]
    search_query = f"{base_query} {variant}"
    status_msg = await callback.message.reply(f"🔍 <b>{variant.title()}</b> <i>varianti qidirilmoqda...</i>", parse_mode=ParseMode.HTML)

    tmpdir_obj: Optional[tempfile.TemporaryDirectory] = None
    try:
        tmpdir_obj = tempfile.TemporaryDirectory()
        tmpdir = tmpdir_obj.name

        audio_path, video_title = await search_and_download_audio(
            query=search_query,
            output_dir=tmpdir,
            timeout_seconds=config.download_timeout_seconds,
            max_size_mb=config.max_audio_size_mb,
        )

        safe_filename = f"{_sanitize_filename(video_title)}.mp3"
        audio_file = FSInputFile(path=audio_path, filename=safe_filename)
        caption = f"🎵 <b>{html.escape(video_title)}</b>\n⚡ Variant: <b>{html.escape(variant.title())}</b>"

        try:
            await callback.message.reply_audio(
                audio=audio_file,
                caption=caption,
                title=video_title[:60],
                performer=variant.title()[:60],
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await callback.message.reply_audio(
                audio=FSInputFile(path=audio_path, filename="remix.mp3"),
            )

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as exc:
        logger.error("Remix xatosi: %s", exc)
        await status_msg.edit_text(f"❌ <b>{variant.title()}</b> topilmadi.", parse_mode=ParseMode.HTML)
    finally:
        if tmpdir_obj is not None:
            try:
                tmpdir_obj.cleanup()
            except Exception:
                pass
