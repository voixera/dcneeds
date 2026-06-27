# Deploy ke Railway

Setup ini memakai satu Docker container dan satu launcher:

```bash
python render_worker.py
```

Launcher hanya menjalankan tiga service:

- `drxsrvrmanage.py`
- `drxfarm.py`
- `discord-oauth-guard`

## Railway

1. Push repo ini ke GitHub.
2. Buat project baru di Railway dari GitHub repo.
3. Railway memakai `railway.json` dan `Dockerfile`.
4. Isi environment variables di Railway.

## Environment Wajib

Isi token untuk tiga service yang dipakai:

```env
DISCORD_SRVRMANAGE_TOKEN=
DISCORD_FARM_TOKEN=
DISCORD_TOKEN=
CLIENT_ID=
GUILD_ID=
```

Gunakan daftar service ini:

```env
ENABLED_BOTS=drxsrvrmanage,drxfarm,oauthguard
ALLOW_MULTI_BOT=true
MAX_RUNNING_BOTS=3
SKIP_MISSING_BOT_TOKENS=true
RESTART_FAILED_BOTS=true
RESTART_DELAY_SECONDS=10
```

Jika Railway plan kecil masih terkena exit code `137`, turunkan sementara:

```env
MAX_RUNNING_BOTS=2
```

atau jalankan satu service saja:

```env
ENABLED_BOTS=drxsrvrmanage
```

## OAuth Guard

Untuk `discord-oauth-guard`, OCR/Tesseract bisa boros RAM. Di Railway kecil, gunakan:

```env
OCR_ENABLED=false
OCR_MAX_CONCURRENT=1
OCR_IMAGE_MAX_DIMENSION=960
```

Slash command OAuth Guard tetap perlu didaftarkan dari folder `discord-oauth-guard`:

```bash
npm run deploy:commands
```

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
