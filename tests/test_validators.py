"""
URL validator modulini tekshiruvchi testlar.
unittest va pytest bilan mos keladi.
"""

import unittest
from utils.validators import extract_valid_url


class TestValidators(unittest.TestCase):
    """URL ajratib olish va tekshirish testlari."""

    def test_extract_instagram_urls(self):
        """Instagram havolalarining to'g'ri ajratib olinishini tekshirish."""
        urls = [
            "https://www.instagram.com/reel/C1234567890/",
            "http://instagram.com/p/B_12345_abc/",
            "https://www.instagram.com/reels/DA123456789/?igsh=MW...",
            "https://instagram.com/tv/C987654321/",
        ]
        for url in urls:
            extracted = extract_valid_url(url)
            self.assertIsNotNone(extracted, f"URL topilmadi: {url}")
            self.assertTrue(extracted.startswith("http"))

    def test_extract_youtube_urls(self):
        """YouTube havolalarining to'g'ri ajratib olinishini tekshirish."""
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&feature=shared",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/3iV2GqG_tVw",
            "https://youtube.com/embed/dQw4w9WgXcQ",
        ]
        for url in urls:
            extracted = extract_valid_url(url)
            self.assertIsNotNone(extracted, f"URL topilmadi: {url}")
            self.assertTrue("youtube.com" in extracted or "youtu.be" in extracted)

    def test_extract_url_from_dirty_text(self):
        """Matn ichidagi havolani to'g'ri ajratib olishni tekshirish."""
        text = "Salom bot, mana bu videodagi qo'shiqni topib ber: https://youtu.be/dQw4w9WgXcQ rahmat!"
        extracted = extract_valid_url(text)
        self.assertEqual(extracted, "https://youtu.be/dQw4w9WgXcQ")

    def test_multiple_urls_returns_first(self):
        """Bir nechta havola bo'lganda birinchisi olinishini tekshirish."""
        text = (
            "Birinchi havola https://www.instagram.com/reel/C12345/ va "
            "ikkinchi havola https://youtu.be/dQw4w9WgXcQ"
        )
        extracted = extract_valid_url(text)
        self.assertIsNotNone(extracted)
        self.assertIn("instagram.com/reel/C12345", extracted)

    def test_invalid_urls_and_plain_text(self):
        """Noto'g'ri havolalar yoki oddiy matn bo'lganda None qaytishini tekshirish."""
        invalid_cases = [
            "Salom bot, qandaysan?",
            "https://facebook.com/watch?v=123",
            "https://tiktok.com/@user/video/123",
            "https://t.me/telegram",
            "",
            None,
        ]
        for case in invalid_cases:
            self.assertIsNone(extract_valid_url(case))


if __name__ == "__main__":
    unittest.main()
