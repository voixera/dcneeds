# DRX Bot Control

Dashboard ini siap deploy ke Vercel, tetapi proses Discord bot tetap harus berjalan di server/VPS/PC yang menjalankan file Python bot.

## Local Control API

1. Isi `.env` di mesin bot:

```env
CONTROL_API_TOKEN=isi-token-rahasia-panjang
CONTROL_HOST=127.0.0.1
CONTROL_PORT=8787
```

2. Jalankan control server:

```bash
python control_server.py
```

3. Jika dashboard Vercel perlu mengakses mesin ini dari internet, publish control API memakai reverse proxy/tunnel HTTPS, lalu set `CONTROL_API_URL` ke URL publik tersebut.

## Vercel Environment

Set environment variables ini di Vercel:

```env
CONTROL_API_URL=https://url-control-api-kamu
CONTROL_API_TOKEN=isi-token-yang-sama-dengan-.env-bot
```

## Dashboard Development

```bash
npm install
npm run dev
```

Dashboard akan tersedia di `http://localhost:3000`.
