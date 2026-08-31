"""
Konfiguratsiya moduli.
.env fayldan sozlamalarni o'qiydi va dastur ishga tushishi bilan validatsiya qiladi.
"""

import glob
import logging
import os
import sys
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv o'rnatilmagan bo'lsa os.environ dan to'g'ridan-to'g'ri o'qiladi
    pass


def _ensure_ffmpeg_in_path() -> None:
    """
    Windows tizimida WinGet orqali o'rnatilgan FFmpeg yo'lini avtomatik PATH ga qo'shish.
    Bu terminal qayta ishga tushirilmagan holatda ham yt-dlp ning ffmpeg ni topishini ta'minlaydi.
    """
    if sys.platform != "win32":
        return

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        return

    # WinGet paketlari katalogidan ffmpeg.exe qidiriladi
    winget_pattern = os.path.join(
        local_app_data,
        "Microsoft",
        "WinGet",
        "Packages",
        "*FFmpeg*",
        "*",
        "bin",
    )
    matching_dirs = glob.glob(winget_pattern)
    for bin_dir in matching_dirs:
        if os.path.exists(os.path.join(bin_dir, "ffmpeg.exe")):
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
                logging.getLogger(__name__).debug("FFmpeg PATH ga qo'shildi: %s", bin_dir)
            break


# FFmpeg yo'lini tekshirish va sozlash
_ensure_ffmpeg_in_path()


@dataclass(frozen=True)
class Config:
    """Telegram bot sozlamalari klassi."""

    bot_token: str
    max_audio_size_mb: int = 50
    download_timeout_seconds: int = 120
    recognition_timeout_seconds: int = 30
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "Config":
        """
        Atrof-muhit o'zgaruvchilaridan (environment variables) sozlamalarni o'qiydi.
        BOT_TOKEN mavjud bo'lmasa yoki bo'sh bo'lsa, darhol xatolik qaytaradi.
        """
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token or token == "1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ_1234567":
            raise ValueError(
                "XATOLIK: Haqiqiy BOT_TOKEN aniqlanmadi!\n"
                "Iltimos, Telegram'dagi @BotFather orqali olingan tokenni .env faylida ko'rsating."
            )

        try:
            max_size = int(os.getenv("MAX_AUDIO_SIZE_MB", "50"))
        except ValueError:
            max_size = 50

        try:
            download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))
        except ValueError:
            download_timeout = 120

        try:
            recognition_timeout = int(os.getenv("RECOGNITION_TIMEOUT_SECONDS", "30"))
        except ValueError:
            recognition_timeout = 30

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        return cls(
            bot_token=token,
            max_audio_size_mb=max_size,
            download_timeout_seconds=download_timeout,
            recognition_timeout_seconds=recognition_timeout,
            log_level=log_level,
        )


def setup_logging(log_level: str = "INFO") -> None:
    """Tizim logging sozlamalarini o'rnatish."""
    level = getattr(logging, log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s:%(lineno)d) - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
