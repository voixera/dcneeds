# Deploy Gabungan ke Railway

Setup ini memakai satu Docker container dan satu launcher:

```bash
python render_worker.py
```

Launcher menjalankan bot Python di root project dan bot TypeScript di `bypassdelta/`.

## Railway

1. Push repo ini ke GitHub.
2. Buat project baru di Railway dari GitHub repo.
3. Railway akan memakai `railway.json` dan `Dockerfile`.
4. Isi environment variables di Railway.

Railway memakai `CMD`/start command Dockerfile saat deploy berbasis Dockerfile. `railway.json` juga mengunci start command ke `python render_worker.py`.

## Environment Wajib

Isi token sesuai bot yang mau dijalankan:

```env
DISCORD_BOT_TOKEN=
DISCORD_MUSIC_TOKEN=
DISCORD_FARM_TOKEN=
DISCORD_SRVRMANAGE_TOKEN=
KEY_BOT_TOKEN=
PAYMENT_BOT_TOKEN=
PANEL_BOT_TOKEN=
BYPASS_DISCORD_TOKEN=
BYPASS_CLIENT_ID=
```

Kalau hanya mau menjalankan beberapa bot:

```env
ENABLED_BOTS=bot,drxmusic,bypassdelta
```

Kalau `ENABLED_BOTS=all`, launcher akan mencoba semua service tetapi skip yang tokennya kosong karena:

```env
SKIP_MISSING_BOT_TOKENS=true
```

## Bypass Delta

Sub-app berada di:

```text
bypassdelta/
```

Env yang dipakai:

```env
BYPASS_DISCORD_TOKEN=
BYPASS_CLIENT_ID=
BYPASS_API_URL=
BYPASS_API_KEY=
BYPASS_ENABLE_MESSAGE_CONTENT=true
BYPASS_DISABLE_DIRECT_LOOKUP=false
AUTHORIZED_USER_IDS=
```

`BYPASS_API_URL` biasanya berbentuk endpoint `/bypass`. Kalau tidak diisi, bot masih bisa mencoba direct lookup untuk service yang didukung kodenya, tapi command yang butuh provider API akan gagal.

## Persistent Data

Jika kamu menambahkan Railway Volume, mount ke path seperti:

```env
PERSISTENT_DATA_DIR=/app/data
```

Launcher akan mengarahkan data ini ke volume:

- `whitelist.json`
- `farm_whitelist.json`
- `keys.json`
- `payment_tickets.json`
- `bypassdelta/.tmp`

## Import Source

Kode `bypassdelta/` diimport dari:

```text
https://github.com/voixera/bypassdelta
commit df313e458c20893c3c2a223e1238682271787665
```
