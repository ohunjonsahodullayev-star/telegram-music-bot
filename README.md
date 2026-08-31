# 🎵 Instagram & YouTube Musiqa Aniqlovchi Telegram Bot

Ushbu Telegram bot foydalanuvchi yuborgan **Instagram** (Reels, Post, IGTV) yoki **YouTube** (Video, Shorts, youtu.be) havolalaridan videoni yuklab oladi, undan audioni (MP3 192kbps) ajratadi va **Shazam** xizmati yordamida fondagi qo'shiq nomi va ijrochisini aniqlab foydalanuvchiga taqdim etadi.

---

## 🚀 Imkoniyatlari

- 📥 **Video va Audio yuklash:** Instagram va YouTube platformalaridagi ochiq videolardan yuqori sifatli audio (MP3, 192 kbps) ajratib olish.
- 🔍 **Musiqani avtomatik aniqlash:** `shazamio` kutubxonasi orqali qo'shiq nomi va ijrochisining nomini aniqlash.
- ⚡ **Asinxron va tezkor:** `aiogram 3.x` va `asyncio` asosida qurilgan. Blocking I/O operatsiyalari alohida thread'da ishlaydi, asosiy event loop qotib qolmaydi.
- 🧹 **Avtomatik tozalash:** Har bir so'rov alohida vaqtinchalik katalogda bajariladi va ish yakunlangach darhol xotiradan o'chiriladi.
- 🛡️ **Xatoliklarga chidamlilik:** Barcha istisno holatlar (yopiq akkauntlar, o'chirilgan videolar, 50MB dan katta hajmlar, tarmoq uzilishlari) ushlanadi va foydalanuvchiga xushmuomala xabarlar qaytariladi.

---

## 🛠️ Texnologiyalar

- **Python 3.11+**
- **aiogram 3.15+** — Asinxron Telegram Bot freymvorki
- **yt-dlp** — Video va audio oqimlarini yuklab olish vositasi
- **shazamio** — Shazam API orqali musiqani aniqlash kutubxonasi
- **ffmpeg** — Audio konvertatsiya va MP3 formatga o'tkazish uchun tizim vositasi
- **python-dotenv** — `.env` konfiguratsiyasini boshqarish
- **pytest & pytest-asyncio** — Unit testlar

---

## 📋 Tizim talabi: FFmpeg o'rnatish

Audio fayllarni MP3 formatiga o'tkazish uchun tizimingizda `ffmpeg` o'rnatilgan va tizim `PATH`iga qo'shilgan bo'lishi shart.

### 🔹 Ubuntu / Debian:
```bash
sudo apt update
sudo apt install -y ffmpeg
ffmpeg -version
```

### 🔹 macOS (Homebrew orqali):
```bash
brew install ffmpeg
ffmpeg -version
```

### 🔹 Windows:
1. **Winget orqali (eng tez usul):**
   PowerShell terminalida:
   ```powershell
   winget install "FFmpeg (Essentials Build)"
   ```
2. **Chocolatey orqali:**
   ```powershell
   choco install ffmpeg
   ```
3. **Qo'lda o'rnatish:**
   - [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) saytidan `ffmpeg-release-essentials.zip` faylini yuklab oling.
   - Arxivni `C:\ffmpeg` papkasiga oching.
   - `C:\ffmpeg\bin` manzilini tizimning `Environment Variables` (Path) ga qo'shing.
   - Terminalda tekshirish: `ffmpeg -version`

---

## ⚙️ O'rnatish va Ishga tushirish

### 1. Loyihani yuklab olish va papkaga o'tish
```bash
cd telegram_music_bot
```

### 2. Virtual muhit (Virtual Environment) yaratish va faollashtirish
- **Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

### 3. Kerakli kutubxonalarni o'rnatish
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Telegram Bot tokenini olish va `.env` faylini sozlash
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring va ko'rsatmalarga rioya qilib yangi bot yarating.
3. Berilgan API tokenni nusxalab oling.
4. `.env.example` faylidan nusxa olib `.env` faylini yarating:
   - **Linux/macOS:** `cp .env.example .env`
   - **Windows:** `copy .env.example .env`
5. `.env` faylini oching va bot tokeningizni kiriting:
   ```env
   BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ_1234567
   MAX_AUDIO_SIZE_MB=50
   DOWNLOAD_TIMEOUT_SECONDS=120
   RECOGNITION_TIMEOUT_SECONDS=30
   LOG_LEVEL=INFO
   ```

### 5. Botni ishga tushirish
```bash
python bot.py
```

---

## 🧪 Unit Testlarni Ishga Tushirish

Barcha funksional xizmatlar, URL validatsiyalari va Shazam modullari uchun tayyorlangan testlarni tekshirish uchun:

```bash
pytest -v
```

---

## 📁 Loyiha Strukturasi

```
telegram_music_bot/
├── bot.py                 # Asosiy ishga tushirish fayli, dispatcher, polling
├── config.py              # .env sozlamalarini yuklash va validatsiya qilish
├── handlers/              # Telegram handlerlari
│   ├── __init__.py
│   ├── start.py           # /start va /help komandalari
│   └── music.py           # Havolalarni qabul qilish va audio jo'natish handleri
├── services/              # Asosiy biznes logika va tashqi xizmatlar
│   ├── __init__.py
│   ├── downloader.py      # yt-dlp orqali videoni yuklab MP3 qilish
│   └── recognizer.py      # shazamio orqali qo'shiqni aniqlash
├── utils/                 # Yordamchi vositalar
│   ├── __init__.py
│   └── validators.py      # Instagram va YouTube URL regex tekshiruvi
├── tests/                 # Avtomatlashtirilgan unit testlar
│   ├── __init__.py
│   ├── test_validators.py # URL validatsiya testlari
│   ├── test_downloader.py # Yuklab olish mock testlari
│   └── test_recognizer.py # Shazam mock testlari
├── requirements.txt       # Kutubxonalar ro'yxati (aniq versiyalarda)
├── .env.example           # Muhit o'zgaruvchilari namunasi
└── README.md              # To'liq qo'llanma
```

---

## ⚠️ Cheklovlar va Muhim Eslatmalar

1. **Instagram Public Akkauntlar:** Bot faqat ochiq (public) Instagram profillaridagi Reels va Postlarni yuklay oladi. Yopiq (private) akkauntlardagi videolarni yuklab bo'lmaydi.
2. **Telegram Fayl Hajmi Limiti:** Oddiy Telegram botlari orqali maksimal **50 MB** gacha bo'lgan fayllarni yuborish mumkin. Agar audio hajmi 50 MB dan katta bo'lsa, bot foydalanuvchiga bu haqda xabar beradi va yuklashni to'xtatadi.
3. **Shazam Tanish Aniqligi:** Agar videodagi ovoz juda shovqinli, nutq bilan to'la yoki musiqa juda qisqa (bir necha soniya) bo'lsa, Shazam qo'shiqni aniqlay olmasligi mumkin. Bunday holatda ham bot audio faylni foydalanuvchiga baribir yuboradi.
