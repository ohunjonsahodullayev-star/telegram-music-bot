"""
Downloader servisini tekshiruvchi testlar.
yt-dlp operatsiyalari mock qilinadi. unittest va pytest bilan mos.
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import services.downloader as downloader_mod
from services.downloader import (
    AudioSizeLimitError,
    DownloaderException,
    DownloaderTimeoutError,
    MediaResult,
    VideoUnavailableError,
    YtDlpDownloadError,
    _sync_download_media,
    _sync_search_and_download_audio,
    download_media,
    search_and_download_audio,
)


class TestDownloader(unittest.IsolatedAsyncioTestCase):
    """Downloader xizmati testlari."""

    def setUp(self):
        self.mock_yt_dlp = MagicMock()
        self.orig_yt_dlp = downloader_mod.yt_dlp
        downloader_mod.yt_dlp = self.mock_yt_dlp

    def tearDown(self):
        downloader_mod.yt_dlp = self.orig_yt_dlp

    def test_sync_download_media_success(self):
        """Muvaffaqiyatli video va audio yuklab olish ssenariysi."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_mp3 = os.path.join(tmpdir, "audio_123.mp3")
            fake_mp4 = os.path.join(tmpdir, "video.mp4")
            with open(fake_mp3, "wb") as f:
                f.write(b"fake audio data")
            with open(fake_mp4, "wb") as f:
                f.write(b"fake video data")

            mock_ydl_instance = MagicMock()
            mock_ydl_instance.extract_info.return_value = {"title": "Test Title", "duration": 30}
            self.mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl_instance

            result = _sync_download_media(
                url="https://youtu.be/dQw4w9WgXcQ",
                output_dir=tmpdir,
                max_size_mb=50,
            )

            self.assertIsInstance(result, MediaResult)
            self.assertEqual(result.audio_path, fake_mp3)
            self.assertEqual(result.video_path, fake_mp4)
            self.assertEqual(result.title, "Test Title")

    def test_sync_search_and_download_audio(self):
        """YouTube qidiruvi orqali audio yuklash ssenariysi."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_mp3 = os.path.join(tmpdir, "remix_123.mp3")
            with open(fake_mp3, "wb") as f:
                f.write(b"fake remix audio")

            mock_ydl_instance = MagicMock()
            mock_ydl_instance.extract_info.return_value = {
                "entries": [{"title": "Shape of You Remix (Official)"}]
            }
            self.mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl_instance

            audio_path, title = _sync_search_and_download_audio(
                query="Shape of You remix",
                output_dir=tmpdir,
                max_size_mb=50,
            )

            self.assertEqual(audio_path, fake_mp3)
            self.assertEqual(title, "Shape of You Remix (Official)")

    def test_sync_download_video_unavailable(self):
        """Video yopiq yoki o'chirilgan bo'lsa VideoUnavailableError tashlanishini tekshirish."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ydl_instance = MagicMock()
            mock_ydl_instance.extract_info.side_effect = YtDlpDownloadError("Video is private or unavailable")
            mock_ydl_instance.download.side_effect = YtDlpDownloadError("Video is private or unavailable")
            self.mock_yt_dlp.YoutubeDL.return_value.__enter__.return_value = mock_ydl_instance

            with self.assertRaises(VideoUnavailableError):
                _sync_download_media(
                    url="https://www.instagram.com/reel/private123/",
                    output_dir=tmpdir,
                    max_size_mb=50,
                )


if __name__ == "__main__":
    unittest.main()
