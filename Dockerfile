# Python 3.11 asosidagi yengil Linux imidji
FROM python:3.11-slim

# Tizim paketlarini yangilash va FFmpeg o'rnatish
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Ishchi katalogni yaratish
WORKDIR /app

# Kutubxonalar ro'yxatini ko'chirish va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Loyihaning barcha kodlarini ko'chirish
COPY . .

# Botni ishga tushirish
CMD ["python", "bot.py"]
