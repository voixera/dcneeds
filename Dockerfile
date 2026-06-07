FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FFMPEG_PATH=ffmpeg

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        libopus0 \
        libsodium23 \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bypassdelta/package*.json ./bypassdelta/
RUN cd bypassdelta && npm ci

COPY . .

CMD ["python", "render_worker.py"]
