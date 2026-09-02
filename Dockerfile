FROM python:3.11-slim

# FFmpeg, Node.js (YouTube n-challenge/signature solving uchun) va curl o'rnatish
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nodejs curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
