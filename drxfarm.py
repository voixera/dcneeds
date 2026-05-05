import asyncio
import glob
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import discord
from discord import app_commands
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(".env")


WHITELIST_FILE = os.getenv("FARM_WHITELIST_FILE", "whitelist.json")
FARM_ID_WHITELIST_FILE = os.getenv("FARM_ID_WHITELIST_FILE", "farm_whitelist.json")
FARM_ACTIVITY_TEXT = (os.getenv("FARM_ACTIVITY_TEXT") or "🔴 {channel} Live • {time} {tz}").strip()
FARM_ACTIVITY_TYPE = (os.getenv("FARM_ACTIVITY_TYPE") or "playing").strip().lower()
FARM_PRESENCE_STATUS = (os.getenv("FARM_PRESENCE_STATUS") or "online").strip().lower()
FARM_ACTIVITY_UPDATE_SECONDS = int((os.getenv("FARM_ACTIVITY_UPDATE_SECONDS") or "60").strip() or "60")
FARM_ACTIVITY_TIMEZONE = (os.getenv("FARM_ACTIVITY_TIMEZONE") or "Asia/Jakarta").strip()
FARM_ACTIVITY_MAXLEN = int((os.getenv("FARM_ACTIVITY_MAXLEN") or "40").strip() or "40")
FARM_YOUTUBE_LINK = (os.getenv("FARM_YOUTUBE_LINK") or "youtube.com/@JKT48").strip()
FARM_STREAM_URL = (os.getenv("FARM_STREAM_URL") or os.getenv("FARM_YOUTUBE_URL") or "").strip()
FARM_RELAX_VOLUME = float((os.getenv("FARM_RELAX_VOLUME") or "0.55").strip() or "0.55")
RELAX_SOUNDS_DIR = Path((os.getenv("RELAX_SOUNDS_DIR") or "relaxsounds").strip() or "relaxsounds")
TOKEN = (
    os.getenv("DISCORD_FARM_TOKEN")
    or os.getenv("DISCORD_BOT_TOKEN")
    or os.getenv("DISCORD_MUSIC_TOKEN")
    or ""
).strip()


RELAX_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",
    ".aac",
    ".opus",
    ".webm",
}

RELAX_FFMPEG_OPTIONS = {
    "before_options": "-stream_loop -1",
    "options": "-vn",
}


def resolve_ffmpeg_executable() -> str:
    env_path = (os.getenv("FFMPEG_PATH") or "").strip().strip('"')
    if env_path and os.path.exists(env_path):
        return env_path

    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path

    direct_candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for candidate in direct_candidates:
        if os.path.exists(candidate):
            return candidate

    glob_candidates = [
        os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*_8wekyb3d8bbwe\ffmpeg-*\bin\ffmpeg.exe"
        ),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*\ffmpeg-*\bin\ffmpeg.exe"),
    ]
    for pattern in glob_candidates:
        matches = glob.glob(pattern)
        if matches:
            matches.sort(reverse=True)
            return matches[0]

    return "ffmpeg"


FFMPEG_EXECUTABLE = resolve_ffmpeg_executable()


def list_relax_sounds() -> list[Path]:
    if not RELAX_SOUNDS_DIR.exists() or not RELAX_SOUNDS_DIR.is_dir():
        return []
    items: list[Path] = []
    for child in RELAX_SOUNDS_DIR.iterdir():
        if not child.is_file():
            continue
        if child.suffix.lower() not in RELAX_EXTENSIONS:
            continue
        items.append(child)
    items.sort(key=lambda p: p.name.casefold())
    return items


def parse_id_list(value: str | None) -> set[int]:
    if not value:
        return set()
    ids: set[int] = set()
    for part in value.replace("\n", ",").replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


FARMOUT_WHITELIST_IDS = parse_id_list(
    os.getenv("FARMOUT_WHITELIST_IDS") or os.getenv("FARM_WHITELIST_IDS")
)

FARM_ADMIN_IDS = parse_id_list(os.getenv("FARM_ADMIN_IDS"))


def _extract_discord_id(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def load_farm_id_whitelist() -> set[int]:
    path = Path(FARM_ID_WHITELIST_FILE)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()

    if isinstance(data, list):
        out: set[int] = set()
        for value in data:
            try:
                out.add(int(value))
            except Exception:
                continue
        return out

    if isinstance(data, dict):
        ids = data.get("ids")
        if isinstance(ids, list):
            out: set[int] = set()
            for value in ids:
                try:
                    out.add(int(value))
                except Exception:
                    continue
            return out

    return set()


def save_farm_id_whitelist(ids: set[int]) -> None:
    path = Path(FARM_ID_WHITELIST_FILE)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = sorted(ids)
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def is_farm_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or interaction.user is None:
        return False
    if interaction.user.id in FARM_ADMIN_IDS:
        return True
    if interaction.guild.owner_id == interaction.user.id:
        return True
    if isinstance(interaction.user, discord.Member):
        return bool(interaction.user.guild_permissions.administrator)
    return False


def load_whitelist_rows() -> list[dict]:
    if not os.path.exists(WHITELIST_FILE):
        return []
    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def is_user_whitelisted_active(user_id: int) -> bool:
    now = datetime.now()
    for row in load_whitelist_rows():
        if str(row.get("user_id")) != str(user_id):
            continue
        expires_at = parse_iso_datetime(row.get("access_expires_at"))
        if expires_at is None:
            return True
        return now < expires_at
    return False


def is_farmout_allowed(user_id: int) -> bool:
    if user_id in FARMOUT_WHITELIST_IDS:
        return True
    if user_id in load_farm_id_whitelist():
        return True
    return is_user_whitelisted_active(user_id)


def normalize_channel_name(name: str) -> str:
    return re.sub(r"[\W_]+", "", (name or "").casefold(), flags=re.UNICODE)


def find_voice_channel_by_query(
    guild: discord.Guild,
    query: str,
) -> discord.abc.GuildChannel | None:
    query = (query or "").strip()
    if not query:
        return None

    channel_id = _extract_discord_id(query)
    if channel_id is not None:
        channel = guild.get_channel(channel_id)
        if isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            return channel

    normalized_query = normalize_channel_name(query)
    if not normalized_query:
        return None

    candidates = list(getattr(guild, "voice_channels", [])) + list(getattr(guild, "stage_channels", []))

    for ch in candidates:
        if normalize_channel_name(ch.name) == normalized_query:
            return ch

    for ch in candidates:
        if normalized_query in normalize_channel_name(ch.name):
            return ch

    return None


def resolve_presence_status(value: str) -> discord.Status:
    value = (value or "").strip().lower()
    if value in ("online", "on"):
        return discord.Status.online
    if value in ("idle", "afk"):
        return discord.Status.idle
    if value in ("dnd", "donotdisturb", "do_not_disturb", "busy"):
        return discord.Status.dnd
    if value in ("invisible", "offline", "off"):
        return discord.Status.invisible
    return discord.Status.online


intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
_presence_task: asyncio.Task | None = None


async def start_relax_sound(guild: discord.Guild, sound_path: Path) -> None:
    voice_client = guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        raise RuntimeError("Bot belum join voice channel.")

    ffmpeg_kwargs = dict(RELAX_FFMPEG_OPTIONS)
    source = discord.FFmpegPCMAudio(
        str(sound_path),
        executable=FFMPEG_EXECUTABLE,
        **ffmpeg_kwargs,
    )
    audio = discord.PCMVolumeTransformer(source, volume=FARM_RELAX_VOLUME)

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
    voice_client.play(audio)


async def ensure_bot_connected_and_deafened(
    interaction: discord.Interaction,
    voice_channel: discord.abc.Connectable,
) -> None:
    assert interaction.guild is not None

    voice_client = interaction.guild.voice_client
    if voice_client is not None and voice_client.is_connected():
        if voice_client.channel and voice_client.channel.id != voice_channel.id:
            await voice_client.move_to(voice_channel)
        await interaction.guild.change_voice_state(channel=voice_channel, self_deaf=True, self_mute=False)
        return

    await voice_channel.connect(self_deaf=True, self_mute=False)


async def disconnect_bot_from_guild(guild: discord.Guild) -> bool:
    voice_client = guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        return False
    try:
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
    except Exception:
        pass
    await voice_client.disconnect(force=True)
    return True


class FarmJoinModal(discord.ui.Modal, title="Farm Join"):
    channel = discord.ui.TextInput(
        label="Voice channel",
        placeholder="Nama / ID voice channel (contoh: 123... atau General)",
        required=True,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
            return

        target = find_voice_channel_by_query(interaction.guild, str(self.channel.value))
        if target is None:
            candidates = list(getattr(interaction.guild, "voice_channels", [])) + list(
                getattr(interaction.guild, "stage_channels", [])
            )
            candidates.sort(key=lambda c: c.position)
            preview = ", ".join(ch.name for ch in candidates[:10]) if candidates else "-"
            await interaction.response.send_message(
                "Voice channel tidak ditemukan. Isi dengan **nama** channel atau **ID** channel voice.\n"
                f"Contoh voice yang ada: {preview}",
                ephemeral=True,
            )
            return

        if not isinstance(target, (discord.VoiceChannel, discord.StageChannel)):
            await interaction.response.send_message("Channel yang dipilih bukan voice/stage channel.", ephemeral=True)
            return

        me = interaction.guild.me or interaction.guild.get_member(client.user.id if client.user else 0)
        if me is None:
            await interaction.response.send_message("Gagal membaca member bot di server ini.", ephemeral=True)
            return

        perms = target.permissions_for(me)
        if not perms.connect:
            await interaction.response.send_message(
                f"Bot tidak punya izin `Connect` di {target.mention}.",
                ephemeral=True,
            )
            return

        try:
            await ensure_bot_connected_and_deafened(interaction, target)
        except discord.Forbidden:
            await interaction.response.send_message("Bot tidak punya izin untuk join/move voice.", ephemeral=True)
            return
        except Exception as exc:
            await interaction.response.send_message(f"Gagal join voice: {exc}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"OK, bot join {target.mention} dan sudah deafen.",
            ephemeral=True,
        )


class RelaxSoundPickerView(discord.ui.View):
    def __init__(self, requester_id: int, sounds: list[Path], voice_channel_id: int):
        super().__init__(timeout=90)
        self.requester_id = requester_id
        self.sounds = sounds
        self.voice_channel_id = voice_channel_id

        options: list[discord.SelectOption] = []
        for idx, path in enumerate(sounds[:25]):
            label = path.stem.strip() or path.name
            if len(label) > 90:
                label = label[:87].rstrip() + "..."
            options.append(discord.SelectOption(label=label, value=str(idx)))

        self.select = discord.ui.Select(
            placeholder="Pilih relaxsounds",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.select.callback = self._on_select
        self.add_item(self.select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user is None or interaction.user.id != self.requester_id:
            await interaction.response.send_message("Hanya user yang menjalankan `/relax` yang bisa memilih.", ephemeral=True)
            return False
        return True

    async def _on_select(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
            return
        if not self.select.values:
            await interaction.response.send_message("Tidak ada pilihan yang dipilih.", ephemeral=True)
            return
        idx = int(self.select.values[0])
        if idx < 0 or idx >= len(self.sounds):
            await interaction.response.send_message("Pilihan tidak valid.", ephemeral=True)
            return
        sound_path = self.sounds[idx]

        channel = interaction.guild.get_channel(self.voice_channel_id)
        if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            await interaction.response.send_message("Voice channel tidak ditemukan lagi. Jalankan `/relax` ulang.", ephemeral=True)
            return

        try:
            await ensure_bot_connected_and_deafened(interaction, channel)
            await start_relax_sound(interaction.guild, sound_path)
        except Exception as exc:
            await interaction.response.send_message(f"Gagal mulai relax: {exc}", ephemeral=True)
            return

        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True
        await interaction.response.edit_message(
            content=f"Relax aktif: `{sound_path.name}` di {channel.mention} (loop nonstop).",
            view=self,
        )
        self.stop()


def build_activity_text(template: str) -> str:
    def truncate_activity(text: str, max_len: int) -> str:
        text = " ".join((text or "").split())
        max_len = max(0, int(max_len or 0))
        if not max_len or len(text) <= max_len:
            return text
        if max_len <= 3:
            return text[:max_len]
        return text[: max_len - 3].rstrip() + "..."

    def derive_channel_label(yt: str) -> str:
        yt = (yt or "").strip()
        if not yt:
            return "YouTube"
        if not yt.startswith("http://") and not yt.startswith("https://"):
            yt = f"https://{yt}"
        try:
            parsed = urlparse(yt)
            path = (parsed.path or "").strip("/")
        except Exception:
            return "YouTube"

        if not path:
            return "YouTube"
        last = path.split("/")[-1].strip()
        if last.startswith("@") and len(last) > 1:
            return last[1:]
        return last or "YouTube"

    def timezone_suffix(tz: str) -> str:
        tz = (tz or "").strip()
        mapping = {
            "Asia/Jakarta": "WIB",
            "Asia/Makassar": "WITA",
            "Asia/Jayapura": "WIT",
        }
        return mapping.get(tz, "")

    template = (template or "").strip()
    if not template:
        template = "🔴 {channel} Live • {time} {tz}"

    now = datetime.now()
    if ZoneInfo is not None and FARM_ACTIVITY_TIMEZONE:
        try:
            now = now.astimezone(ZoneInfo(FARM_ACTIVITY_TIMEZONE))
        except Exception:
            pass

    clock = now.strftime("%H:%M")
    date = now.strftime("%d/%m")
    tz = timezone_suffix(FARM_ACTIVITY_TIMEZONE)

    channel = derive_channel_label(FARM_YOUTUBE_LINK)
    yt_link = (FARM_YOUTUBE_LINK or "").strip()

    replacements = {
        "{yt}": yt_link,
        "{channel}": channel,
        "{time}": clock,
        "{date}": date,
        "{tz}": tz,
        "{sep}": " • ",
        "{dot}": "🔴",
        "{live}": "LIVE",
    }
    for key, value in replacements.items():
        if key in template:
            template = template.replace(key, value)

    text = " ".join(template.split())

    cleanup = {
        "YouTube": "YT",
        "youtube": "YT",
        "LiveStream": "Live",
        "Livestream": "Live",
        "Live Stream": "Live",
        "Notifier": "Notif",
        "Notifiers": "Notif",
        "Notification": "Notif",
        "Notifications": "Notif",
        " | ": " • ",
        "|": " • ",
    }
    for before, after in cleanup.items():
        text = text.replace(before, after)

    text = re.sub(r"(?:\\s+•\\s+)+", " • ", text).strip(" •")
    text = " ".join(text.split())
    # tz = timezone
    if not tz:
        text = re.sub(r"\\s+[A-Z]{3}\\b\\s*$", "", text).rstrip()
    return truncate_activity(text, FARM_ACTIVITY_MAXLEN)


async def update_presence_once() -> None:
    activity_text = build_activity_text(FARM_ACTIVITY_TEXT)
    if FARM_ACTIVITY_TYPE in ("custom", "status"):
        activity = discord.CustomActivity(name=activity_text)
    elif FARM_ACTIVITY_TYPE in ("watching", "watch"):
        activity = discord.Activity(type=discord.ActivityType.watching, name=activity_text)
    elif FARM_ACTIVITY_TYPE in ("listening", "listen"):
        activity = discord.Activity(type=discord.ActivityType.listening, name=activity_text)
    elif FARM_ACTIVITY_TYPE in ("streaming", "stream"):
        url = FARM_STREAM_URL
        if not url and FARM_YOUTUBE_LINK:
            if FARM_YOUTUBE_LINK.startswith("http://") or FARM_YOUTUBE_LINK.startswith("https://"):
                url = FARM_YOUTUBE_LINK
            else:
                url = f"https://{FARM_YOUTUBE_LINK}"
        activity = discord.Streaming(name=activity_text, url=(url or "https://youtube.com"))
    else:
        activity = discord.Game(name=activity_text)
    await client.change_presence(
        status=discord.Status.dnd,
        activity=activity,
    )
    
async def presence_loop() -> None:
    while not client.is_closed():
        try:
            await update_presence_once()
        except Exception as exc:
            print(f"[drxfarm] Gagal set status/presence: {exc}")
        await asyncio.sleep(max(15, FARM_ACTIVITY_UPDATE_SECONDS))

#Command definitions
@tree.command(name="farmjoin", description="Pilih voice channel untuk bot join & deafen (farm mode).")
async def farmjoin(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
        return
    await interaction.response.send_modal(FarmJoinModal())


@tree.command(name="relax", description="Putar ambience nonstop dari folder relaxsounds.")
async def relax(interaction: discord.Interaction) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
        return
    if not is_farm_admin(interaction):
        await interaction.response.send_message("Khusus admin (atau FARM_ADMIN_IDS) untuk memakai `/relax`.", ephemeral=True)
        return

    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message("Kamu harus join voice channel dulu.", ephemeral=True)
        return

    target = interaction.user.voice.channel
    me = interaction.guild.me or interaction.guild.get_member(client.user.id if client.user else 0)
    if me is None:
        await interaction.response.send_message("Gagal membaca member bot di server ini.", ephemeral=True)
        return
    perms = target.permissions_for(me)
    if not perms.view_channel:
        await interaction.response.send_message("Bot tidak punya izin `View Channel` di voice itu.", ephemeral=True)
        return
    if not perms.connect:
        await interaction.response.send_message("Bot tidak punya izin `Connect` di voice itu.", ephemeral=True)
        return
    if not perms.speak:
        await interaction.response.send_message("Bot tidak punya izin `Speak` di voice itu.", ephemeral=True)
        return

    sounds = list_relax_sounds()
    if not sounds:
        await interaction.response.send_message(
            f"Folder `{RELAX_SOUNDS_DIR}` kosong / tidak ada.\n"
            "Buat folder itu dan isi file audio (mp3/wav/ogg/flac/m4a/aac/opus/webm), lalu coba lagi.",
            ephemeral=True,
        )
        return
    if len(sounds) > 25:
        await interaction.response.send_message(
            f"Terlalu banyak file di `{RELAX_SOUNDS_DIR}` (maks 25 untuk dropdown). "
            "Kurangi jumlah file atau pindahkan sebagian.",
            ephemeral=True,
        )
        return

    view = RelaxSoundPickerView(
        requester_id=interaction.user.id,
        sounds=sounds,
        voice_channel_id=target.id,
    )
    await interaction.response.send_message(
        "Pilih ambience yang mau diputar:",
        view=view,
        ephemeral=True,
    )


@tree.command(name="farmout", description="Keluarkan bot dari voice (khusus whitelist).")
async def farmout(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
        return

    user_id = interaction.user.id if interaction.user else 0
    if not is_farmout_allowed(user_id):
        await interaction.response.send_message("Kamu tidak ada di whitelist untuk `/farmout`.", ephemeral=True)
        return

    try:
        did_disconnect = await disconnect_bot_from_guild(interaction.guild)
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin untuk disconnect voice.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal keluar voice: {exc}", ephemeral=True)
        return

    if not did_disconnect:
        await interaction.response.send_message("Bot sedang tidak ada di voice.", ephemeral=True)
        return

    await interaction.response.send_message("Baik, bot keluar dari voice.", ephemeral=True)


@tree.command(name="farmwl_add", description="Tambah Discord ID ke whitelist /farmout.")
@app_commands.describe(user_id="Discord ID (boleh pakai mention juga)")
async def farmwl_add(interaction: discord.Interaction, user_id: str) -> None:
    if not is_farm_admin(interaction):
        await interaction.response.send_message("Kamu tidak punya akses untuk manage whitelist.", ephemeral=True)
        return

    target_id = _extract_discord_id(user_id)
    if target_id is None:
        await interaction.response.send_message("Format `user_id` tidak valid.", ephemeral=True)
        return

    ids = load_farm_id_whitelist()
    if target_id in ids:
        await interaction.response.send_message(f"ID `{target_id}` sudah ada di whitelist.", ephemeral=True)
        return

    ids.add(target_id)
    try:
        save_farm_id_whitelist(ids)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal simpan whitelist: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Baik, ID `{target_id}` ditambahkan ke whitelist.", ephemeral=True)


@tree.command(name="farmwl_remove", description="Hapus Discord ID dari whitelist /farmout.")
@app_commands.describe(user_id="Discord ID (boleh pakai mention juga)")
async def farmwl_remove(interaction: discord.Interaction, user_id: str) -> None:
    if not is_farm_admin(interaction):
        await interaction.response.send_message("Kamu tidak punya akses untuk manage whitelist.", ephemeral=True)
        return

    target_id = _extract_discord_id(user_id)
    if target_id is None:
        await interaction.response.send_message("Format `user_id` tidak valid.", ephemeral=True)
        return

    ids = load_farm_id_whitelist()
    if target_id not in ids:
        await interaction.response.send_message(f"ID `{target_id}` tidak ada di whitelist.", ephemeral=True)
        return

    ids.remove(target_id)
    try:
        save_farm_id_whitelist(ids)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal simpan whitelist: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"OK, ID `{target_id}` dihapus dari whitelist.", ephemeral=True)


@tree.command(name="farmwl_list", description="Lihat daftar whitelist /farmout.")
async def farmwl_list(interaction: discord.Interaction) -> None:
    if not is_farm_admin(interaction):
        await interaction.response.send_message("Kamu tidak punya akses untuk melihat whitelist.", ephemeral=True)
        return

    ids = sorted(load_farm_id_whitelist())
    if not ids:
        await interaction.response.send_message("Whitelist kosong.", ephemeral=True)
        return

    preview = ", ".join(f"`{value}`" for value in ids[:80])
    more = "" if len(ids) <= 80 else f"\n(+{len(ids) - 80} lagi)"
    await interaction.response.send_message(f"Whitelist IDs ({len(ids)}): {preview}{more}", ephemeral=True)


@client.event
async def on_ready() -> None:
    global _presence_task
    try:
        await tree.sync()
    except Exception as exc:
        print(f"[drxfarm] Gagal sync command: {exc}")
    try:
        await update_presence_once()
    except Exception as exc:
        print(f"[drxfarm] Gagal set status/presence: {exc}")
    if _presence_task is None or _presence_task.done():
        _presence_task = asyncio.create_task(presence_loop())
    user = client.user
    print(f"[drxfarm] Logged in as {user} (id={getattr(user, 'id', None)})")
    if not os.getenv("DISCORD_FARM_TOKEN"):
        print("[drxfarm] Warning: DISCORD_FARM_TOKEN belum diset (pakai fallback token).")
    if FARMOUT_WHITELIST_IDS:
        print(f"[drxfarm] FARMOUT_WHITELIST_IDS aktif: {sorted(FARMOUT_WHITELIST_IDS)}")
    else:
        print(f"[drxfarm] FARMOUT_WHITELIST_IDS kosong; fallback whitelist dari {WHITELIST_FILE}")
    print(f"[drxfarm] Farm file whitelist: {FARM_ID_WHITELIST_FILE} (count={len(load_farm_id_whitelist())})")
    if FARM_ADMIN_IDS:
        print(f"[drxfarm] FARM_ADMIN_IDS aktif: {sorted(FARM_ADMIN_IDS)}")


def main() -> int:
    if not TOKEN:
        raise RuntimeError(
            "Token kosong. Set env `DISCORD_FARM_TOKEN` (disarankan) atau `DISCORD_BOT_TOKEN` / `DISCORD_MUSIC_TOKEN`."
        )
    client.run(TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
