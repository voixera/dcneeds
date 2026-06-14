FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FFMPEG_PATH=ffmpeg

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        gnupg \
        libopus0 \
        libsodium23 \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bypassdelta/package*.json ./bypassdelta/
RUN cd bypassdelta && npm ci

COPY bot-fifa-worldcup/package*.json ./bot-fifa-worldcup/
RUN cd bot-fifa-worldcup && npm ci

COPY discord-oauth-guard/package*.json ./discord-oauth-guard/
RUN cd discord-oauth-guard && npm ci

COPY . .

CMD ["python", "render_worker.py"]
