"""
Video va Audio yuklab olish xizmati (yt-dlp + FFmpeg).
YouTube va Instagram havolalaridan video (MP4) va toza audio (MP3) ajratib oladi.
"""

import asyncio
import glob
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Optional, Tuple

import yt_dlp
from yt_dlp.utils import DownloadError as YtDlpDownloadError

logger = logging.getLogger(__name__)


@dataclass
class MediaResult:
    """Yuklab olingan media ma'lumotlari."""
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None


class DownloaderException(Exception):
    """Downloader xizmati xatoligi."""
    pass


class VideoUnavailableError(DownloaderException):
    """Video topilmadi yoki yopiq."""
    pass


class AudioSizeLimitError(DownloaderException):
    """Fayl hajmi limitdan oshdi."""
    pass


class DownloaderTimeoutError(DownloaderException):
    """Yuklab olish vaqti tugadi."""
    pass


def _find_ffmpeg_dir() -> Optional[str]:
    """Tizimda FFmpeg katalogini aniqlash."""
    loc = shutil.which("ffmpeg")
    if loc:
        return os.path.dirname(loc)

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        dirs = glob.glob(os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "*FFmpeg*", "*", "bin"))
        for d in dirs:
            if os.path.exists(os.path.join(d, "ffmpeg.exe")):
                return d
    return None


def _get_base_ydl_opts() -> dict:
    """yt-dlp uchun asosiy sozlamalar (Node.js JS runtime va Android client bilan)."""
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
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "player_skip": ["webpage", "configs"],
            }
        },
    }
    ffmpeg_dir = _find_ffmpeg_dir()
    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir

    if shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}

    return opts


def _sync_download_media(url: str, output_dir: str, max_size_mb: int = 50) -> MediaResult:
    """Videoni (MP4) va audioni (MP3) yuklab oladi."""
    result = MediaResult()

    # 1. Video yuklab olish (MP4)
    video_template = os.path.join(output_dir, "video.%(ext)s")
    video_opts = _get_base_ydl_opts()
    video_opts.update({
        "format": "best[ext=mp4][filesize<?50M]/best[filesize<?50M]/18/22/best",
        "outtmpl": video_template,
        "merge_output_format": "mp4",
    })

    # 2. Audio yuklab olish (MP3 192kbps)
    audio_template = os.path.join(output_dir, "audio_%(id)s.%(ext)s")
    audio_opts = _get_base_ydl_opts()
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
        # Video
        try:
            with yt_dlp.YoutubeDL(video_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    result.title = info.get("title")
                    result.duration = info.get("duration")

            v_files = [f for f in glob.glob(os.path.join(output_dir, "video.*")) if not f.endswith(".mp3")]
            if v_files:
                v_path = v_files[0]
                if (os.path.getsize(v_path) / (1024 * 1024)) <= max_size_mb:
                    result.video_path = v_path
        except Exception as vid_err:
            logger.warning("Video yuklashda xabar: %s", vid_err)

        # Audio
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            ydl.download([url])

        mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))
        if not mp3_files:
            raise DownloaderException("MP3 formatga o'tkazishda fayl topilmadi.")

        audio_path = mp3_files[0]
        a_size = os.path.getsize(audio_path) / (1024 * 1024)
        if a_size > max_size_mb:
            raise AudioSizeLimitError(f"Audio hajmi ({a_size:.1f} MB) {max_size_mb} MB limitdan oshdi.")

        result.audio_path = audio_path
        return result

    except YtDlpDownloadError as exc:
        err_msg = str(exc).lower()
        if any(w in err_msg for w in ["private", "unavailable", "not found", "deleted"]):
            raise VideoUnavailableError("Video topilmadi, yopiq akkauntda yoki o'chirilgan.") from exc
        raise DownloaderException(f"Yuklab olishda xatolik: {exc}") from exc


def _sync_search_and_download_audio(query: str, output_dir: str, max_size_mb: int = 50) -> Tuple[str, str]:
    """YouTube qidiruv orqali MP3 yuklaydi."""
    search_query = f"ytsearch1:{query}"
    audio_template = os.path.join(output_dir, "remix_%(id)s.%(ext)s")

    opts = _get_base_ydl_opts()
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
        video_title = query
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if info and "entries" in info and info["entries"]:
                entry = info["entries"][0]
                video_title = entry.get("title", query)

        mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))
        if not mp3_files:
            raise DownloaderException(f"'{query}' bo'yicha audio topilmadi.")

        audio_path = mp3_files[0]
        a_size = os.path.getsize(audio_path) / (1024 * 1024)
        if a_size > max_size_mb:
            raise AudioSizeLimitError(f"Audio hajmi ({a_size:.1f} MB) {max_size_mb} MB dan oshdi.")

        return audio_path, video_title

    except YtDlpDownloadError as exc:
        raise DownloaderException(f"Qidiruvda xatolik: {exc}") from exc


async def download_media(url: str, output_dir: str, timeout_seconds: int = 120, max_size_mb: int = 50) -> MediaResult:
    """Asinxron media yuklash."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_download_media, url, output_dir, max_size_mb),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise DownloaderTimeoutError(f"Yuklab olish vaqti ({timeout_seconds}s) tugadi.") from exc


async def search_and_download_audio(query: str, output_dir: str, timeout_seconds: int = 60, max_size_mb: int = 50) -> Tuple[str, str]:
    """Asinxron qidiruv audiosi yuklash."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_search_and_download_audio, query, output_dir, max_size_mb),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise DownloaderTimeoutError(f"Qidiruv vaqti ({timeout_seconds}s) tugadi.") from exc
