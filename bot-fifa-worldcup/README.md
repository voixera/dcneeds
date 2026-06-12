# Bot FIFA Worldcup

Bot Discord.js v14 untuk jadwal, hasil, klasemen, informasi tim, prediksi skor, leaderboard, dan notifikasi pertandingan Piala Dunia.

## Setup

1. Install dependency:

   ```bash
   npm install
   ```

2. Isi `.env` di root workspace `discordresource/`.
   Bot bisa memakai `DISCORD_BOT_TOKEN` yang sudah ada. Kalau ingin token khusus, tambahkan:

   ```env
   DISCORD_FIFA_TOKEN=...
   DISCORD_FIFA_CLIENT_ID=...
   DISCORD_FIFA_GUILD_ID=...
   DISCORD_FIFA_NOTIFICATION_CHANNEL_ID=...
   ```

   Jika Railway menampilkan `DiscordAPIError[50001]: Missing Access`, cek lagi `DISCORD_FIFA_GUILD_ID`. ID itu harus ID server tempat bot sudah di-invite dengan scope `bot` dan `applications.commands`. Kosongkan `DISCORD_FIFA_GUILD_ID` untuk memakai command global.

4. Untuk jawaban live dari Groq dengan web search bawaan, isi juga:

   ```env
   FIFA_LIVE_ANSWERS_ENABLED=true
   GROQ_API_KEY=...
   GROQ_MODEL=groq/compound-mini
   ```

   Gunakan `groq/compound-mini` atau `groq/compound` agar Groq bisa memakai web search. Kalau `GROQ_API_KEY` belum diset, command tetap memakai data lokal.

3. Jalankan bot:

   ```bash
   npm start
   ```

## Command

- `/jadwal` menampilkan jadwal pertandingan.
- `/hasil` menampilkan hasil pertandingan terbaru.
- `/klasemen` menampilkan klasemen grup.
- `/tim` menampilkan informasi tim nasional.
- `/prediksi` menyimpan atau mengubah prediksi skor.
- `/leaderboard` menampilkan ranking poin prediksi.

## Data

Saat pertama kali berjalan, bot membuat `database/db.json` dari `database/seedData.js`. Untuk mengganti jadwal, hasil, klasemen, dan tim, ubah `database/db.json` setelah file tersebut dibuat, atau integrasikan API pada `services/worldCupService.js`.

Aturan poin prediksi ada di `config/worldcup.js`.
