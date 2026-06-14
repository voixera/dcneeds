# discord-oauth-guard

Discord bot untuk membantu melindungi server dari spam scam OAuth, fake giveaway, fake Nitro, fake crypto reward, fake MrBeast/Kai Cenat promotion, fake Steam gift, dan spam gambar dari akun yang sudah mengotorisasi aplikasi Discord berbahaya.

Bot ini tidak bisa membaca daftar OAuth app yang pernah diotorisasi user. Fokusnya adalah mendeteksi perilaku dan konten yang biasanya muncul setelah akun korban dipakai untuk spam: gambar berulang, OCR keyword scam, mention abuse, akun baru, dan pengiriman attachment lintas channel.

## Fitur

- OCR gambar dengan `tesseract.js`.
- Normalisasi gambar dan perceptual hash menggunakan `sharp`.
- Keyword scam mudah ditambah di `src/config/scamKeywords.js` atau lewat `/scamkeywords`.
- Risk score 0-100 dengan threshold:
  - `0-39`: safe
  - `40-69`: suspicious
  - `70-100`: malicious
- Auto moderation untuk skor malicious:
  - delete message
  - timeout user
  - log embed ke channel moderator
  - simpan riwayat ke SQLite
- Warning dan pencatatan untuk skor suspicious.
- Spam pattern detection:
  - gambar sama berulang
  - gambar sama di banyak channel
  - banyak attachment dalam waktu pendek
- Slash command dashboard:
  - `/scamstats`
  - `/scamlogs`
  - `/scamkeywords`
  - `/scamconfig`
  - `/scamhash`
  - `/scamscan`
  - `/joinvoice`

## Requirements

- Node.js latest LTS, direkomendasikan Node `24+`.
- Bot Discord dengan permission:
  - View Channels
  - Send Messages
  - Embed Links
  - Read Message History
  - Manage Messages
  - Moderate Members
  - Connect
  - View Audit Log, opsional untuk menampilkan siapa yang disconnect atau move bot dari voice
  - Manage Channels, opsional untuk membuat log channel otomatis
- Gateway intents di Developer Portal:
  - Server Members Intent
  - Message Content Intent

## Instalasi

```bash
cd discord-oauth-guard
npm install
cp .env.example .env
```

Isi `.env`:

```env
DISCORD_TOKEN=your_discord_bot_token
CLIENT_ID=your_application_client_id
GUILD_ID=your_test_guild_id
```

Inisialisasi database:

```bash
npm run db:init
```

Daftarkan slash commands:

```bash
npm run deploy:commands
```

Jalankan bot:

```bash
npm start
```

## Konfigurasi Penting

Default ada di `.env.example` dan `src/config/defaultConfig.js`.

```env
SUSPICIOUS_THRESHOLD=40
MALICIOUS_THRESHOLD=70
TIMEOUT_DURATION_MS=3600000
IMAGE_SIMILARITY_DISTANCE=8
SPAM_WINDOW_SECONDS=120
SPAM_ATTACHMENT_THRESHOLD=4
SPAM_CHANNEL_THRESHOLD=3
MASS_MENTION_THRESHOLD=5
VOICE_RECONNECT_DELAY_MS=5000
```

Keyword default ada di:

```text
src/config/scamKeywords.js
```

Keyword juga bisa dikelola lewat:

```text
/scamkeywords list
/scamkeywords add keyword:"free discord nitro"
/scamkeywords remove keyword:"free discord nitro"
/scamkeywords reset
```

## Cara Kerja Deteksi

Saat pesan punya attachment gambar:

1. Bot download gambar ke `data/tmp`.
2. OCR dijalankan dengan Tesseract.
3. Teks OCR dan teks pesan discan oleh `scamDetector`.
4. Bot membuat perceptual hash 8x8 dari gambar.
5. Hash dibandingkan dengan hash sebelumnya di SQLite memakai Hamming distance.
6. Aktivitas user dalam window pendek dianalisis untuk burst dan multi-channel spam.
7. `riskEngine` menghasilkan skor dan severity.
8. `moderationService` menjalankan aksi sesuai severity.

## Skema Database

Schema ada di:

```text
src/database/schema.sql
```

Tabel utama:

- `detected_scams`
- `image_hashes`
- `strike_history`
- `timeout_history`
- `risk_scores`
- `configuration`
- `user_activity`

## Commands

### `/scamstats`

Menampilkan statistik deteksi dan top user dalam rentang hari tertentu.

### `/scamlogs`

Menampilkan deteksi terbaru lengkap dengan user, channel, score, keyword, dan alasan.

### `/scamkeywords`

Mengelola keyword scam untuk OCR dan scan teks.

### `/scamconfig`

Melihat dan mengubah konfigurasi runtime per server.

Key yang tersedia:

- `suspiciousThreshold`
- `maliciousThreshold`
- `timeoutDurationMs`
- `enableAutoTimeout`
- `deleteMaliciousMessages`
- `imageSimilarityDistance`
- `spamAttachmentThreshold`
- `spamChannelThreshold`
- `massMentionThreshold`
- `voiceReconnectDelayMs`

### `/scamhash`

Melihat hash gambar terbaru atau menghapus hash tertentu.

### `/scamscan`

Scan manual teks atau gambar tanpa melakukan moderasi otomatis dan tanpa menyimpan hash baru.

### `/joinvoice`

Menjaga bot tetap berada di voice channel dengan self mute dan self deafen.

```text
/joinvoice join
/joinvoice join channel:#voice
/joinvoice notify channel:#mod-log
/joinvoice setchannel channel:#mod-log
/joinvoice status
/joinvoice leave
```

Jika bot dikeluarkan, disconnect, atau dipindahkan dari voice channel tersimpan, bot akan mengirim embed notif ke channel yang diatur dengan `/joinvoice notify` atau `/joinvoice setchannel`. Bot juga akan mencoba rejoin otomatis ke voice channel tersimpan. Jika bot punya permission `View Audit Log`, notif akan mencoba menampilkan executor yang melakukan disconnect atau move.

## Production Notes

- Jalankan bot dengan process manager seperti `pm2`, Docker, systemd, atau platform hosting Node.
- Pastikan role bot berada di atas role member yang ingin bisa di-timeout.
- Untuk voice guard, pastikan bot punya permission `Connect` ke voice channel dan `View Audit Log` jika ingin notif menyebut executor.
- Tesseract OCR bisa berat untuk server kecil. Atur `IMAGE_MAX_BYTES` dan `OCR_TIMEOUT_MS`.
- Jika terlalu banyak false positive, naikkan `MALICIOUS_THRESHOLD`, turunkan bobot di `src/config/defaultConfig.js`, atau hapus keyword yang terlalu umum.
- Jika scam image sering lolos karena crop/resize kecil, naikkan `IMAGE_SIMILARITY_DISTANCE` secara bertahap.

## Struktur

```text
discord-oauth-guard/
├─ src/
│  ├─ commands/
│  ├─ events/
│  ├─ services/
│  │  ├─ ocrService.js
│  │  ├─ imageHashService.js
│  │  ├─ riskEngine.js
│  │  └─ scamDetector.js
│  ├─ database/
│  ├─ config/
│  ├─ utils/
│  └─ index.js
├─ data/
├─ logs/
├─ .env.example
├─ package.json
└─ README.md
```
