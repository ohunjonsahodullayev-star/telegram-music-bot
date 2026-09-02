"""
Audio va Video yuklab olish hamda YouTube qidiruv servisi.
yt-dlp kutubxonasi orqali video yuklanadi va FFmpeg yordamida MP3 formatga o'tkaziladi.
"""

import asyncio
import glob
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import yt_dlp
    from yt_dlp.utils import DownloadError as YtDlpDownloadError
except ImportError:
    yt_dlp = None

    class YtDlpDownloadError(Exception):
        """yt-dlp o'rnatilmagan muhitda testlar uchun moslashtirilgan xatolik."""
        pass

logger = logging.getLogger(__name__)


@dataclass
class MediaResult:
    """Yuklab olingan audio va video ma'lumotlari."""

    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None


class DownloaderException(Exception):
    """Downloader xizmati uchun umumiy xatolik asosi."""
    pass


class VideoUnavailableError(DownloaderException):
    """Video topilmadi, o'chirilgan yoki akkaunt yopiq (private) bo'lganda tashlanadigan xatolik."""
    pass


class AudioSizeLimitError(DownloaderException):
    """Fayl hajmi Telegram cheklovidan (50 MB) oshib ketganda tashlanadigan xatolik."""
    pass


class DownloaderTimeoutError(DownloaderException):
    """Yuklab olish jarayoni belgilangan vaqt ichida tugamasa tashlanadigan xatolik."""
    pass


def _find_ffmpeg_dir() -> Optional[str]:
    """Tizimda FFmpeg joylashgan katalogni aniqlaydi."""
    loc = shutil.which("ffmpeg")
    if loc:
        return os.path.dirname(loc)

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_pattern = os.path.join(
            local_app_data,
            "Microsoft",
            "WinGet",
            "Packages",
            "*FFmpeg*",
            "*",
            "bin",
        )
        dirs = glob.glob(winget_pattern)
        for d in dirs:
            if os.path.exists(os.path.join(d, "ffmpeg.exe")):
                return d
    return None


def _get_base_ydl_opts(client_type: str = "android") -> dict:
    """
    Asosiy umumiy yt-dlp parametrlarini qaytaradi.
    YouTube'ning datacenter/bot cheklovlarini aylanib o'tish uchun Android/Mobile clientlari qo'llanadi.
    """
    client_list = ["android", "android_creator", "mweb", "ios"] if client_type == "android" else ["android_creator", "tv_embedded", "ios"]
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {
                "player_client": client_list,
                "player_skip": ["webpage", "configs"],
            }
        },
    }
    ffmpeg_dir = _find_ffmpeg_dir()
    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir
    return opts


def _sync_download_media(url: str, output_dir: str, max_size_mb: int = 50) -> MediaResult:
    """
    Sinxron ravishda videoni (MP4) va audioni (MP3) yuklab oladi.
    """
    if yt_dlp is None:
        raise DownloaderException("yt-dlp kutubxonasi tizimda topilmadi.")

    result = MediaResult()

    # 1. Video yuklab olish (MP4 formatda, maksimal 50MB)
    video_template = os.path.join(output_dir, "video.%(ext)s")
    video_opts = _get_base_ydl_opts("android")
    video_opts.update({
        "format": "best[ext=mp4][filesize<?50M]/best[filesize<?50M]/18/22/best",
        "outtmpl": video_template,
        "merge_output_format": "mp4",
    })

    # 2. Audio yuklab olish (MP3 192kbps)
    audio_template = os.path.join(output_dir, "audio_%(id)s.%(ext)s")
    audio_opts = _get_base_ydl_opts("android")
    audio_opts.update({
        "format": "bestaudio/best",
        "outtmpl": audio_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    })

    try:
        logger.info("Videoni yuklash boshlandi: %s", url)
        try:
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    result.title = info.get("title")
                    result.duration = info.get("duration")

            video_files = [
                f for f in glob.glob(os.path.join(output_dir, "video.*"))
                if not f.endswith(".mp3")
            ]
            if video_files:
                v_path = video_files[0]
                v_size = os.path.getsize(v_path) / (1024 * 1024)
                if v_size <= max_size_mb:
                    result.video_path = v_path
                    logger.info("Video muvaffaqiyatli yuklandi: %s (%.2f MB)", v_path, v_size)
        except Exception as vid_err:
            logger.warning("Videoni yuklashda ogohlantirish (audio baribir yuklanadi): %s", vid_err)

        logger.info("Audioni yuklash boshlandi: %s", url)
        try:
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                ydl.download([url])
        except YtDlpDownloadError as audio_err:
            # Agar birinchi urinishda bot blokirovkasi bo'lsa, zaxira client bilan qayta urinish
            if "confirm you’re not a bot" in str(audio_err) or "sign in" in str(audio_err).lower():
                logger.info("Zaxira extractor client bilan qayta urinilmoqda...")
                fallback_opts = _get_base_ydl_opts("fallback")
                fallback_opts.update({
                    "format": "bestaudio/best",
                    "outtmpl": audio_template,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                })
                with yt_dlp.YoutubeDL(fallback_opts) as ydl_fb:
                    ydl_fb.download([url])
            else:
                raise

        mp3_files = glob.glob(os.path.join(output_dir, "audio_*.mp3"))
        if not mp3_files:
            mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))

        if not mp3_files:
            raise DownloaderException("Audio faylni MP3 formatga o'tkazishda xatolik: MP3 fayl topilmadi.")

        audio_path = mp3_files[0]
        a_size = os.path.getsize(audio_path) / (1024 * 1024)
        if a_size > max_size_mb:
            raise AudioSizeLimitError(f"Audio fayl hajmi ({a_size:.1f} MB) {max_size_mb} MB limitdan oshdi.")

        result.audio_path = audio_path
        return result

    except YtDlpDownloadError as exc:
        err_msg = str(exc).lower()
        if any(w in err_msg for w in ["private", "unavailable", "not found", "deleted", "login required"]):
            raise VideoUnavailableError("Video topilmadi, yopiq (private) akkauntda yoki o'chirilgan.") from exc
        raise DownloaderException(f"Yuklab olishda xatolik: {exc}") from exc


def _sync_search_and_download_audio(query: str, output_dir: str, max_size_mb: int = 50) -> Tuple[str, str]:
    """
    YouTube qidiruvi orqali audioni qidirib MP3 formatda yuklaydi.
    """
    if yt_dlp is None:
        raise DownloaderException("yt-dlp kutubxonasi topilmadi.")

    search_query = f"ytsearch1:{query}"
    audio_template = os.path.join(output_dir, "remix_%(id)s.%(ext)s")

    opts = _get_base_ydl_opts("android")
    opts.update({
        "format": "bestaudio/best",
        "outtmpl": audio_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    })

    try:
        logger.info("YouTube qidiruv orqali yuklash boshlandi: %s", search_query)
        video_title = query
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if info and "entries" in info and info["entries"]:
                entry = info["entries"][0]
                video_title = entry.get("title", query)

        mp3_files = glob.glob(os.path.join(output_dir, "remix_*.mp3"))
        if not mp3_files:
            mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))

        if not mp3_files:
            raise DownloaderException(f"'{query}' bo'yicha audio topilmadi.")

        audio_path = mp3_files[0]
        a_size = os.path.getsize(audio_path) / (1024 * 1024)
        if a_size > max_size_mb:
            raise AudioSizeLimitError(f"Audio hajmi ({a_size:.1f} MB) {max_size_mb} MB dan oshib ketdi.")

        return audio_path, video_title

    except YtDlpDownloadError as exc:
        raise DownloaderException(f"Qidiruvda yuklash xatoligi: {exc}") from exc


async def download_media(
    url: str,
    output_dir: str,
    timeout_seconds: int = 120,
    max_size_mb: int = 50,
) -> MediaResult:
    """Asinxron holda Video va Audioni yuklab oladi."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_download_media, url, output_dir, max_size_mb),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise DownloaderTimeoutError(f"Yuklab olish vaqti ({timeout_seconds}s) tugadi.") from exc


async def search_and_download_audio(
    query: str,
    output_dir: str,
    timeout_seconds: int = 60,
    max_size_mb: int = 50,
) -> Tuple[str, str]:
    """Asinxron holda YouTube qidiruvidan audioni yuklaydi."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_search_and_download_audio, query, output_dir, max_size_mb),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise DownloaderTimeoutError(f"Qidiruv vaqti ({timeout_seconds}s) tugadi.") from exc


async def download_audio(
    url: str,
    output_dir: str,
    timeout_seconds: int = 120,
    max_size_mb: int = 50,
) -> str:
    """Eski modul chaqiruvlari uchun audio yuklash funksiyasi."""
    res = await download_media(url, output_dir, timeout_seconds, max_size_mb)
    if not res.audio_path:
        raise DownloaderException("Audio yuklab olinmadi.")
    return res.audio_path
