"""
Musiqa aniqlash (Shazam) servisini tekshiruvchi unit testlar.
shazamio operatsiyalari mock qilinadi. unittest va pytest bilan mos.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

import services.recognizer as recognizer_mod
from services.recognizer import TrackInfo, recognize_music


class TestRecognizer(unittest.IsolatedAsyncioTestCase):
    """Shazam orqali qo'shiq aniqlash testlari."""

    def setUp(self):
        self.mock_shazam_cls = MagicMock()
        self.orig_shazam = recognizer_mod.Shazam
        recognizer_mod.Shazam = self.mock_shazam_cls

    def tearDown(self):
        recognizer_mod.Shazam = self.orig_shazam

    async def test_recognize_music_success(self):
        """Muvaffaqiyatli qo'shiq aniqlanishi ssenariysi."""
        mock_shazam_result = {
            "matches": [{"id": "12345"}],
            "track": {
                "title": "Shape of You",
                "subtitle": "Ed Sheeran",
                "images": {
                    "coverart": "https://example.com/cover.jpg",
                },
            },
        }

        mock_shazam_inst = MagicMock()
        mock_shazam_inst.recognize = AsyncMock(return_value=mock_shazam_result)
        self.mock_shazam_cls.return_value = mock_shazam_inst

        track = await recognize_music("fake/path/audio.mp3", timeout_seconds=5)

        self.assertIsNotNone(track)
        self.assertIsInstance(track, TrackInfo)
        self.assertEqual(track.title, "Shape of You")
        self.assertEqual(track.subtitle, "Ed Sheeran")
        self.assertEqual(track.cover_url, "https://example.com/cover.jpg")

    async def test_recognize_music_not_found(self):
        """Qo'shiq bazadan topilmagan holatda None qaytishi."""
        mock_shazam_inst = MagicMock()
        mock_shazam_inst.recognize = AsyncMock(return_value={"matches": []})
        self.mock_shazam_cls.return_value = mock_shazam_inst

        track = await recognize_music("fake/path/audio.mp3", timeout_seconds=5)
        self.assertIsNone(track)

    async def test_recognize_music_empty_track(self):
        """Track kaliti bo'sh bo'lgan holatda None qaytishi."""
        mock_shazam_inst = MagicMock()
        mock_shazam_inst.recognize = AsyncMock(return_value={"track": {}})
        self.mock_shazam_cls.return_value = mock_shazam_inst

        track = await recognize_music("fake/path/audio.mp3", timeout_seconds=5)
        self.assertIsNone(track)

    async def test_recognize_music_timeout(self):
        """Shazam so'rovi timeout bo'lganda dastur to'xtamasdan None qaytishi."""
        mock_shazam_inst = MagicMock()

        async def slow_recognize(*args, **kwargs):
            await asyncio.sleep(2)
            return {"track": {"title": "Slow Song"}}

        mock_shazam_inst.recognize = slow_recognize
        self.mock_shazam_cls.return_value = mock_shazam_inst

        track = await recognize_music("fake/path/audio.mp3", timeout_seconds=0.1)
        self.assertIsNone(track)

    async def test_recognize_music_exception_safety(self):
        """Shazam ichida kutilmagan xatolik yuz berganda xatolik tashlamasdan None qaytishi."""
        mock_shazam_inst = MagicMock()
        mock_shazam_inst.recognize = AsyncMock(side_effect=Exception("Shazam network error"))
        self.mock_shazam_cls.return_value = mock_shazam_inst

        track = await recognize_music("fake/path/audio.mp3", timeout_seconds=5)
        self.assertIsNone(track)


if __name__ == "__main__":
    unittest.main()
