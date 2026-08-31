"""
Qo'shiqni aniqlash (Shazam) servisi.
shazamio kutubxonasi yordamida audio fayldan musiqa nomi va ijrochisini aniqlaydi.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

try:
    from shazamio import Shazam
except ImportError:
    Shazam = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrackInfo:
    """Aniqlangan qo'shiq ma'lumotlari modeli."""

    title: str
    subtitle: str
    cover_url: Optional[str] = None


async def recognize_music(
    audio_path: str,
    timeout_seconds: int = 30,
) -> Optional[TrackInfo]:
    """
    Shazam xizmati orqali audio faylni skanerlaydi va qo'shiq ma'lumotlarini qaytaradi.

    Musiqa topilmasa yoki xatolik yuz bersa xatolik tashlamaydi, None qaytaradi.
    Bu bot audio faylni baribir foydalanuvchiga yetkazishiga imkon beradi.

    Args:
        audio_path (str): MP3 faylning to'liq yo'li.
        timeout_seconds (int): Shazam so'rovi uchun maksimal kutish vaqti (soniya).

    Returns:
        Optional[TrackInfo]: Qo'shiq ma'lumotlari yoki None (topilmasa).
    """
    if Shazam is None:
        logger.warning("shazamio kutubxonasi o'rnatilmagan.")
        return None

    shazam = Shazam()

    try:
        logger.info("Shazam orqali qo'shiqni aniqlash boshlandi: %s", audio_path)

        # Timeout bilan himoyalangan so'rov
        recognition_task = shazam.recognize(audio_path)
        result = await asyncio.wait_for(recognition_task, timeout=timeout_seconds)

        if not result or not isinstance(result, dict):
            logger.info("Shazam natijasi bo'sh qaytdi.")
            return None

        track_data = result.get("track")
        if not track_data or not isinstance(track_data, dict):
            logger.info("Shazam bazasidan mos qo'shiq topilmadi.")
            return None

        title = track_data.get("title")
        subtitle = track_data.get("subtitle", "Noma'lum ijrochi")

        if not title:
            logger.info("Qo'shiq nomi aniqlanmadi.")
            return None

        # Muqova rasmini olish (agar mavjud bo'lsa)
        images = track_data.get("images", {})
        cover_url = (
            images.get("coverart")
            or images.get("coverarthq")
            or images.get("background")
        )

        track_info = TrackInfo(
            title=title.strip(),
            subtitle=subtitle.strip() if subtitle else "Noma'lum ijrochi",
            cover_url=cover_url,
        )

        logger.info("Qo'shiq muvaffaqiyatli aniqlandi: %s - %s", track_info.subtitle, track_info.title)
        return track_info

    except asyncio.TimeoutError:
        logger.warning(
            "Shazam qidiruv vaqti tugadi (Timeout: %ds): %s",
            timeout_seconds,
            audio_path,
        )
        return None
    except Exception as exc:
        logger.warning(
            "Shazam orqali aniqlashda xatolik yuz berdi: %s",
            exc,
            exc_info=True,
        )
        return None
