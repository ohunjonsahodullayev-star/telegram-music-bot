"""
URL validatsiya moduli.
Instagram va YouTube havolalarini xabar matnidan aniqlash va ajratib olish uchun mo'ljallangan.
"""

import re
from typing import Optional

# Instagram havolalari uchun regex (Post, Reel, TV)
INSTAGRAM_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/[a-zA-Z0-9_\-\.]+/?(?:\?[^\s]*)?",
    re.IGNORECASE,
)

# YouTube havolalari uchun regex (Standart video, Shorts, qisqa youtu.be, embed)
YOUTUBE_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/(?:watch\?(?:[^\s]*&)?v=[a-zA-Z0-9_-]+[^\s]*|shorts/[a-zA-Z0-9_-]+[^\s]*|embed/[a-zA-Z0-9_-]+[^\s]*)|youtu\.be/[a-zA-Z0-9_-]+[^\s]*)",
    re.IGNORECASE,
)


def extract_valid_url(text: str) -> Optional[str]:
    """
    Foydalanuvchi yuborgan xabar matnidan birinchi mos kelgan Instagram yoki YouTube havolasini ajratib oladi.

    ESLATMA:
    Agar xabarda bir nechta havola mavjud bo'lsa, server resurslarini tejash va navbatda adashmaslik
    uchun faqat birinchi topilgan havola qayta ishlanadi, qolganlari e'tiborsiz qoldiriladi.
    Foydalanuvchi qolgan havolalarni alohida xabar sifatida yuborishi mumkin.

    Args:
        text (str): Foydalanuvchi yuborgan xabar matni.

    Returns:
        Optional[str]: Topilgan havola yoki None (agar mos keladigan havola topilmasa).
    """
    if not text or not isinstance(text, str):
        return None

    # Avval Instagram havolasini tekshiramiz
    insta_match = INSTAGRAM_PATTERN.search(text)
    # So'ngra YouTube havolasini tekshiramiz
    yt_match = YOUTUBE_PATTERN.search(text)

    # Agar ikkalasi ham bo'lsa, matnda birinchi paydo bo'lganini tanlaymiz
    if insta_match and yt_match:
        if insta_match.start() < yt_match.start():
            return insta_match.group(0)
        return yt_match.group(0)
    elif insta_match:
        return insta_match.group(0)
    elif yt_match:
        return yt_match.group(0)

    return None
