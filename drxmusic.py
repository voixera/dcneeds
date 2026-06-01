import asyncio
import glob
import os
import re
import shutil
from dataclasses import dataclass
from typing import Optional
from env_loader import load_env_file
import discord
import yt_dlp
from discord.ext import commands


load_env_file()

BOT_TOKEN = (
    os.getenv("DISCORD_MUSIC_TOKEN")
    or os.getenv("MUSIC_BOT_TOKEN")
    or os.getenv("DISCORD_BOT_TOKEN")
    or ""
).strip()
if not BOT_TOKEN:
    raise RuntimeError("DISCORD_MUSIC_TOKEN belum di-set. Set DISCORD_MUSIC_TOKEN di .env dulu.")
SEARCH_RESULT_LIMIT = 5
CHECK_CANDIDATE_LIMIT = 3
IDLE_TIMEOUT_SECONDS = 3000
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}
YTDL_FORMAT_OPTIONS = {
    "ignoreconfig": True,
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "extract_flat": False,
    "socket_timeout": 12,
}

cookie_file = (os.getenv("YTDLP_COOKIE_FILE") or os.getenv("YTDL_COOKIE_FILE") or "").strip()
if not cookie_file and os.path.exists("cookies.txt"):
    cookie_file = "cookies.txt"

ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)
YTDL_COOKIE_OPTIONS = dict(YTDL_FORMAT_OPTIONS)
if cookie_file and os.path.exists(cookie_file):
    YTDL_COOKIE_OPTIONS["cookiefile"] = cookie_file
    ytdl_cookie = yt_dlp.YoutubeDL(YTDL_COOKIE_OPTIONS)
else:
    ytdl_cookie = None


def ytdl_extract_info_with_fallback(query: str) -> dict:
    try:
        return ytdl.extract_info(query, download=False)
    except Exception as e:
        msg = str(e)
        if ytdl_cookie is not None and ("Sign in to confirm you" in msg or "not a bot" in msg):
            try:
                return ytdl_cookie.extract_info(query, download=False)
            except Exception as e2:
                msg = f"{msg} | cookie-fallback: {e2}"
        if "Requested format is not available" not in msg and "Sign in to confirm you" not in msg:
            raise RuntimeError(msg)

        fallback_ytdl = yt_dlp.YoutubeDL(dict(YTDL_FORMAT_OPTIONS))
        try:
            return fallback_ytdl.extract_info(query, download=False)
        except Exception:
            minimal_opts = {
                "ignoreconfig": True,
                "quiet": True,
                "noplaylist": True,
                "extract_flat": False,
            }
            minimal_ytdl = yt_dlp.YoutubeDL(minimal_opts)
            return minimal_ytdl.extract_info(query, download=False)


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
        os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*\ffmpeg-*\bin\ffmpeg.exe"
        ),
    ]
    for pattern in glob_candidates:
        matches = glob.glob(pattern)
        if matches:
            matches.sort(reverse=True)
            return matches[0]

    return "ffmpeg"


FFMPEG_EXECUTABLE = resolve_ffmpeg_executable()
YOUTUBE_MUSIC_EMOJI = "<:ytmusic:1480114978035073234>"
EMBED_COLOR = discord.Color.from_rgb(32, 34, 37)


@dataclass
class Track:
    title: str
    stream_url: str
    webpage_url: str
    duration: int
    requester: str
    http_headers: Optional[dict] = None


def build_track_status_embed(track: Track, status_text: str, footer_text: Optional[str] = None) -> discord.Embed:
    embed = discord.Embed(
        description=(
            f"{YOUTUBE_MUSIC_EMOJI} {status_text} "
            f"[**{discord.utils.escape_markdown(track.title)}**]({track.webpage_url})"
        ),
        color=EMBED_COLOR,
    )
    if footer_text:
        embed.set_footer(text=footer_text)
    return embed


def build_status_embed(
    title: str,
    description: str,
    footer_text: Optional[str] = None,
    show_emoji: bool = True,
) -> discord.Embed:
    embed = discord.Embed(description=description, color=EMBED_COLOR)
    author_name = f"{YOUTUBE_MUSIC_EMOJI} {title}" if show_emoji else title
    embed.set_author(name=author_name)
    if footer_text:
        embed.set_footer(text=footer_text)
    return embed


def build_error_embed(description: str) -> discord.Embed:
    return build_status_embed("Music Error", description)


def build_success_embed(title: str, description: str, footer_text: Optional[str] = None) -> discord.Embed:
    return build_status_embed(title, description, footer_text=footer_text)


def build_idle_disconnect_embed() -> discord.Embed:
    return build_status_embed(
        "Idle timeout",
        "No tracks have been playing for the past 3 minutes, leaving now.",
        show_emoji=False,
    )


async def reply_with_embed(ctx: commands.Context, embed: discord.Embed) -> None:
    await ctx.reply(embed=embed)


async def send_with_embed(channel: discord.abc.Messageable, embed: discord.Embed) -> None:
    await channel.send(embed=embed)


def pick_best_audio_stream(info: dict) -> tuple[str, dict]:
    formats = info.get("formats") or []
    candidates = []

    for fmt in formats:
        if fmt.get("acodec") in (None, "none"):
            continue
        if not fmt.get("url"):
            continue
        if fmt.get("vcodec") not in (None, "none"):
            continue
        candidates.append(fmt)

    if not candidates:
        url = info.get("url")
        if not url:
            video_id = info.get("id")
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
        if not url:
            url = info.get("webpage_url")
        if not url:
            raise RuntimeError("Gagal mendapatkan stream URL audio.")
        return url, (info.get("http_headers") or {})

    def score(fmt: dict) -> tuple[int, float, float]:
        protocol = (fmt.get("protocol") or "").lower()
        ext = (fmt.get("ext") or "").lower()
        protocol_rank = 1 if protocol in ("https", "http") else 0
        ext_rank = 1 if ext in ("mp3", "m4a", "opus", "ogg", "webm") else 0
        bitrate = float(fmt.get("abr") or fmt.get("tbr") or 0)
        return (protocol_rank + ext_rank, bitrate, float(fmt.get("asr") or 0))

    best = max(candidates, key=score)
    return best["url"], (best.get("http_headers") or info.get("http_headers") or {})


class GuildMusicPlayer:
    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue: asyncio.Queue[Track] = asyncio.Queue()
        self.current: Optional[Track] = None
        self.next_event = asyncio.Event()
        self.volume = 0.7
        self.announce_channel_id: Optional[int] = None
        self.loop_task = bot.loop.create_task(self.player_loop())

    def set_announce_channel(self, channel_id: int):
        self.announce_channel_id = channel_id

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next_event.clear()
            try:
                track = await asyncio.wait_for(self.queue.get(), timeout=IDLE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                guild = self.bot.get_guild(self.guild_id)
                if guild and guild.voice_client and guild.voice_client.is_connected():
                    if self.announce_channel_id:
                        announce_channel = self.bot.get_channel(self.announce_channel_id)
                        if announce_channel is not None and hasattr(announce_channel, "send"):
                            try:
                                await send_with_embed(announce_channel, build_idle_disconnect_embed())
                            except Exception:
                                pass
                    try:
                        await guild.voice_client.disconnect(force=True)
                    except Exception:
                        pass
                self.current = None
                continue

            self.current = track
            guild = self.bot.get_guild(self.guild_id)
            if guild is None:
                self.current = None
                continue

            voice_client = guild.voice_client
            if voice_client is None or not voice_client.is_connected():
                await self.queue.put(track)
                self.current = None
                await asyncio.sleep(1)
                continue

            ffmpeg_kwargs = dict(FFMPEG_OPTIONS)
            before_options = ffmpeg_kwargs.get("before_options", "")
            if track.http_headers:
                user_agent = track.http_headers.get("User-Agent")
                if user_agent:
                    before_options += f' -user_agent "{user_agent}"'
                referer = track.http_headers.get("Referer") or track.webpage_url
                if referer:
                    before_options += f' -referer "{referer}"'
            ffmpeg_kwargs["before_options"] = before_options.strip()

            source = discord.FFmpegPCMAudio(
                track.stream_url,
                executable=FFMPEG_EXECUTABLE,
                **ffmpeg_kwargs,
            )
            audio_source = discord.PCMVolumeTransformer(source, volume=self.volume)

            if self.announce_channel_id:
                announce_channel = self.bot.get_channel(self.announce_channel_id)
                if announce_channel is not None and hasattr(announce_channel, "send"):
                    try:
                        await send_with_embed(
                            announce_channel,
                            build_track_status_embed(track, "Started playing"),
                        )
                    except Exception:
                        pass

            def _after_playback(error: Optional[Exception]):
                if error:
                    print(f"[Music] Playback error in guild {self.guild_id}: {error}")
                self.bot.loop.call_soon_threadsafe(self.next_event.set)

            voice_client.play(audio_source, after=_after_playback)
            await self.next_event.wait()
            self.current = None

    @property
    def queue_size(self) -> int:
        return self.queue.qsize()


class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.players: dict[int, GuildMusicPlayer] = {}

    def get_player(self, guild: discord.Guild) -> GuildMusicPlayer:
        player = self.players.get(guild.id)
        if player is None:
            player = GuildMusicPlayer(self, guild.id)
            self.players[guild.id] = player
        return player


bot = MusicBot()


def score_yt_entry(entry: dict, query: str) -> tuple[int, int, int, int]:
    title = (entry.get("title") or "").lower()
    channel = (
        entry.get("channel")
        or entry.get("uploader")
        or entry.get("uploader_id")
        or ""
    ).lower()
    query_l = query.lower()

    channel_official = 0
    if "official artist channel" in channel:
        channel_official += 5
    if "vevo" in channel:
        channel_official += 4
    if " - topic" in channel or channel.endswith("topic"):
        channel_official += 3
    if "official" in channel:
        channel_official += 2
    if entry.get("channel_is_verified"):
        channel_official += 2

    avoid_non_original = 0
    bad_tokens = (
        "cover",
        "karaoke",
        "nightcore",
        "slowed",
        "sped up",
        "remix",
        "fanmade",
        "instrumental",
        "8d",
    )
    if any(t in title for t in bad_tokens):
        avoid_non_original -= 6

    query_match = 0
    for token in re.findall(r"[a-z0-9]+", query_l):
        if token and token in title:
            query_match += 1

    duration = int(entry.get("duration") or 0)
    duration_reasonable = 1 if 90 <= duration <= 600 else 0

    return (channel_official, avoid_non_original, query_match, duration_reasonable)


def rank_yt_entries(entries: list[dict], query: str) -> list[dict]:
    return sorted(entries, key=lambda e: score_yt_entry(e, query), reverse=True)


def extract_youtube_music_track_sync(query: str, requester: str) -> Track:
    if "spotify.com/" in query or query.strip().lower().startswith("spotify:"):
        raise RuntimeError("Source itu tidak didukung. Pakai judul lagu atau link YouTube.")

    search_query = query
    ranking_query = query
    if not re.match(r"^https?://", search_query.strip(), flags=re.IGNORECASE):
        search_query = f"ytsearch{SEARCH_RESULT_LIMIT}:{search_query}"

    info = ytdl_extract_info_with_fallback(search_query)
    if "entries" in info and info["entries"]:
        ranked = rank_yt_entries(info["entries"], ranking_query)
        last_err = None
        resolved = None

        for entry in ranked[:CHECK_CANDIDATE_LIMIT]:
            try:
                candidate = entry
                if not candidate.get("formats"):
                    url = candidate.get("webpage_url")
                    if not url and candidate.get("id"):
                        url = f"https://www.youtube.com/watch?v={candidate['id']}"
                    if not url:
                        continue
                    candidate = ytdl_extract_info_with_fallback(url)

                pick_best_audio_stream(candidate)
                resolved = candidate
                break
            except Exception as e:
                last_err = e
                continue

        if resolved is None:
            if last_err:
                raise RuntimeError(f"Tidak ada kandidat YouTube yang playable: {last_err}")
            raise RuntimeError("Tidak ada kandidat YouTube yang playable.")
        info = resolved

    stream_url, headers = pick_best_audio_stream(info)

    return Track(
        title=info.get("title", "Unknown Title"),
        stream_url=stream_url,
        webpage_url=info.get("webpage_url") or query,
        duration=int(info.get("duration") or 0),
        requester=requester,
        http_headers=headers,
    )


async def extract_track(query: str, requester: str) -> Track:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_youtube_music_track_sync, query, requester)


async def ensure_voice(ctx: commands.Context) -> Optional[discord.VoiceClient]:
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await reply_with_embed(ctx, build_error_embed("Kamu harus join voice channel dulu."))
        return None

    target_channel = ctx.author.voice.channel
    me = ctx.guild.me or ctx.guild.get_member(bot.user.id)
    if me is None:
        await reply_with_embed(ctx, build_error_embed("Gagal membaca member bot di server ini."))
        return None

    perms = target_channel.permissions_for(me)
    if not perms.connect:
        await reply_with_embed(ctx, build_error_embed("Bot tidak punya izin `Connect` di voice channel itu."))
        return None
    if not perms.speak:
        await reply_with_embed(ctx, build_error_embed("Bot tidak punya izin `Speak` di voice channel itu."))
        return None
    if not perms.view_channel:
        await reply_with_embed(ctx, build_error_embed("Bot tidak punya izin `View Channel` di voice channel itu."))
        return None

    voice_client = ctx.guild.voice_client

    if voice_client and voice_client.channel != target_channel:
        try:
            await voice_client.move_to(target_channel)
            try:
                await ctx.guild.change_voice_state(channel=target_channel, self_deaf=True)
            except Exception:
                pass
            return voice_client
        except Exception:
            try:
                await voice_client.disconnect(force=True)
            except Exception:
                pass
            voice_client = None

    if voice_client is None:
        stale = ctx.guild.voice_client
        if stale is not None:
            try:
                await stale.disconnect(force=True)
            except Exception:
                pass
            await asyncio.sleep(1.0)

        last_error = None
        for attempt in range(2):
            try:
                voice_client = await target_channel.connect(timeout=20.0, reconnect=False)
                try:
                    await ctx.guild.change_voice_state(channel=target_channel, self_deaf=True)
                except Exception:
                    pass
                break
            except discord.errors.ConnectionClosed as e:
                last_error = e
                if getattr(e, "code", None) == 4017:
                    if isinstance(target_channel, discord.VoiceChannel):
                        await reply_with_embed(
                            ctx,
                            build_error_embed(
                                "Discord menolak koneksi voice dengan kode `4017` "
                                "(enforcement DAVE/E2EE untuk non-stage voice). "
                                "Coba gunakan **Stage Channel** sebagai workaround, "
                                "atau update library voice yang sudah support DAVE."
                            ),
                        )
                    await asyncio.sleep(2.0)
                    continue
                await reply_with_embed(
                    ctx,
                    build_error_embed(
                        f"Gagal join voice: websocket close code `{getattr(e, 'code', 'unknown')}`"
                    ),
                )
                return None
            except asyncio.TimeoutError as e:
                last_error = e
                await asyncio.sleep(2.0)
            except Exception as e:
                last_error = e
                if "davey library needed" in str(e).lower():
                    await reply_with_embed(
                        ctx,
                        build_error_embed(
                            "Library voice `davey` belum terpasang. "
                            "Install dulu: `python -m pip install -U davey discord.py PyNaCl` "
                            "lalu restart bot."
                        ),
                    )
                    return None
                await asyncio.sleep(2.0)

        if voice_client is None:
            await reply_with_embed(
                ctx,
                build_error_embed(
                    f"Gagal join voice setelah retry. Error terakhir: `{last_error}`"
                ),
            )
            return None

    return voice_client


def format_duration(seconds: int) -> str:
    try:
        total_seconds = int(float(seconds))
    except (TypeError, ValueError):
        return "Live/Unknown"

    if total_seconds <= 0:
        return "Live/Unknown"

    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs"),
    )
    print(f"[Music] FFmpeg executable: {FFMPEG_EXECUTABLE}")
    print(f"[Music] YT cookie file: {cookie_file if (cookie_file and os.path.exists(cookie_file)) else 'none'}")


@bot.command(name="join", aliases=["j"])
async def join_cmd(ctx: commands.Context):
    voice_client = await ensure_voice(ctx)
    if voice_client:
        me = ctx.guild.me or ctx.guild.get_member(bot.user.id)
        if me and me.voice and me.voice.mute:
            await reply_with_embed(
                ctx,
                build_success_embed(
                    "Voice Connected",
                    f"Join ke **{discord.utils.escape_markdown(voice_client.channel.name)}**, tapi bot sedang `server mute`.",
                ),
            )
            return
        await reply_with_embed(
            ctx,
            build_success_embed(
                "Voice Connected",
                f"Join ke **{discord.utils.escape_markdown(voice_client.channel.name)}** dan bot sudah deafen.",
            ),
        )


@bot.command(name="beep")
async def beep_cmd(ctx: commands.Context):
    voice_client = await ensure_voice(ctx)
    if voice_client is None:
        return
    if voice_client.is_playing():
        voice_client.stop()

    try:
        source = discord.FFmpegPCMAudio(
            "sine=frequency=880:duration=2",
            executable=FFMPEG_EXECUTABLE,
            before_options="-f lavfi",
            options="-vn",
        )
        voice_client.play(source)
        await reply_with_embed(ctx, build_success_embed("Playback Test", "Tes audio 2 detik diputar (`!beep`)."))
    except Exception as e:
        await reply_with_embed(ctx, build_error_embed(f"Gagal tes audio: `{e}`"))


@bot.command(name="debugplay")
async def debugplay_cmd(ctx: commands.Context, *, query: Optional[str] = None):
    if not query:
        await reply_with_embed(ctx, build_error_embed("Format: `!debugplay <judul/link youtube>`."))
        return
    try:
        track = await extract_track(query, str(ctx.author))
        await reply_with_embed(
            ctx,
            build_success_embed(
                "Debug Stream",
                f"Title: `{track.title}`\nURL: `{track.stream_url[:180]}`\nHasHeaders: `{bool(track.http_headers)}`",
            ),
        )
    except Exception as e:
        await reply_with_embed(ctx, build_error_embed(f"Debug gagal: `{e}`"))


@bot.command(name="play", aliases=["p"])
async def play_cmd(ctx: commands.Context, *, query: Optional[str] = None):
    if not query:
        await reply_with_embed(ctx, build_error_embed("Format: `!play <judul lagu atau link YouTube>`."))
        return

    voice_client = await ensure_voice(ctx)
    if voice_client is None:
        return

    player = bot.get_player(ctx.guild)
    player.set_announce_channel(ctx.channel.id)

    async with ctx.typing():
        try:
            track = await extract_track(query, str(ctx.author))
        except Exception as e:
            raw_msg = str(e)
            clean_msg = re.sub(r"\x1b\[[0-9;]*m", "", raw_msg)
            if "Sign in to confirm you" in clean_msg or "not a bot" in clean_msg:
                await reply_with_embed(
                    ctx,
                    build_error_embed(
                        "YouTube minta verifikasi bot. Export cookies browser ke file `cookies.txt` atau set `.env` `YTDLP_COOKIE_FILE=<path cookies.txt>`, lalu restart bot."
                    ),
                )
                return
            await reply_with_embed(ctx, build_error_embed(f"Gagal ambil audio track: `{clean_msg}`"))
            return

    await player.queue.put(track)

    if voice_client.is_playing() or voice_client.is_paused() or player.current is not None:
        await reply_with_embed(
            ctx,
            build_track_status_embed(track, "Added to queue", footer_text=f"Queue position: {player.queue_size}"),
        )


@bot.command(name="skip", aliases=["s"])
async def skip_cmd(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await reply_with_embed(ctx, build_error_embed("Bot belum ada di voice channel."))
        return

    if not voice_client.is_playing():
        await reply_with_embed(ctx, build_error_embed("Tidak ada lagu yang sedang diputar."))
        return

    voice_client.stop()
    await reply_with_embed(ctx, build_success_embed("Playback Updated", "Lagu di-skip."))


@bot.command(name="pause")
async def pause_cmd(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_playing():
        await reply_with_embed(ctx, build_error_embed("Tidak ada lagu aktif untuk di-pause."))
        return

    voice_client.pause()
    await reply_with_embed(ctx, build_success_embed("Playback Paused", "Playback di-pause."))


@bot.command(name="resume")
async def resume_cmd(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_paused():
        await reply_with_embed(ctx, build_error_embed("Tidak ada lagu yang sedang pause."))
        return

    voice_client.resume()
    await reply_with_embed(ctx, build_success_embed("Playback Resumed", "Playback dilanjutkan."))


@bot.command(name="stop")
async def stop_cmd(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await reply_with_embed(ctx, build_error_embed("Bot belum join voice channel."))
        return

    player = bot.get_player(ctx.guild)
    while not player.queue.empty():
        try:
            player.queue.get_nowait()
            player.queue.task_done()
        except asyncio.QueueEmpty:
            break

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    await reply_with_embed(ctx, build_success_embed("Playback Stopped", "Playback dihentikan dan queue dibersihkan."))


@bot.command(name="leave", aliases=["dc", "disconnect"])
async def leave_cmd(ctx: commands.Context):
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await reply_with_embed(ctx, build_error_embed("Bot belum join voice channel."))
        return

    await voice_client.disconnect(force=True)
    await reply_with_embed(ctx, build_success_embed("Voice Disconnected", "Keluar dari voice channel."))


@bot.command(name="queue", aliases=["q"])
async def queue_cmd(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if player.queue.empty():
        if player.current:
            await reply_with_embed(ctx, build_track_status_embed(player.current, "Queue Overview", footer_text="Queue kosong."))
        else:
            await reply_with_embed(ctx, build_success_embed("Queue Overview", "Queue kosong."))
        return

    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_author(name=f"{YOUTUBE_MUSIC_EMOJI} Queue Overview")
    if player.current:
        embed.add_field(
            name="Now Playing",
            value=(
                f"[**{discord.utils.escape_markdown(player.current.title)}**]({player.current.webpage_url})\n"
                f"`{format_duration(player.current.duration)}` • `{player.current.requester}`"
            ),
            inline=False,
        )

    preview = []
    for idx, item in enumerate(list(player.queue._queue)[:10], start=1):
        preview.append(
            f"`{idx}.` [**{discord.utils.escape_markdown(item.title)}**]({item.webpage_url}) • `{format_duration(item.duration)}`"
        )

    embed.add_field(name="Next Queue", value="\n".join(preview), inline=False)
    if player.queue_size > 10:
        embed.set_footer(text=f"Showing 10 of {player.queue_size} queued tracks")
    await reply_with_embed(ctx, embed)


@bot.command(name="np", aliases=["nowplaying"])
async def now_playing_cmd(ctx: commands.Context):
    player = bot.get_player(ctx.guild)
    if not player.current:
        await reply_with_embed(ctx, build_error_embed("Tidak ada lagu yang sedang diputar."))
        return

    embed = build_track_status_embed(
        player.current,
        "Now playing",
        footer_text=f"Duration: {format_duration(player.current.duration)} | Request by: {player.current.requester}",
    )
    await reply_with_embed(ctx, embed)


@bot.command(name="volume", aliases=["vol"])
async def volume_cmd(ctx: commands.Context, volume: int):
    if volume < 0 or volume > 200:
        await reply_with_embed(ctx, build_error_embed("Volume harus 0-200."))
        return

    player = bot.get_player(ctx.guild)
    player.volume = volume / 100

    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.source and isinstance(voice_client.source, discord.PCMVolumeTransformer):
        voice_client.source.volume = player.volume

    await reply_with_embed(ctx, build_success_embed("Volume Updated", f"Volume diset ke `{volume}%`."))


@bot.command(name="helpmusic", aliases=["hm"])
async def helpmusic_cmd(ctx: commands.Context):
    embed = discord.Embed(color=EMBED_COLOR)
    embed.set_author(name=f"{YOUTUBE_MUSIC_EMOJI} Music Commands")
    embed.add_field(
        name="Available Commands",
        value=(
            "`!join` join voice + deafen\n"
            "`!play <judul/link youtube>` putar dari YouTube Music\n"
            "`!skip` skip lagu\n"
            "`!pause` / `!resume`\n"
            "`!queue` lihat antrean\n"
            "`!np` lagu saat ini\n"
            "`!volume 0-200` atur volume\n"
            "`!stop` stop + clear queue\n"
            "`!leave` keluar voice"
        ),
        inline=False,
    )
    embed.set_footer(text="Pencarian diprioritaskan channel official artist/band.")
    await reply_with_embed(ctx, embed)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await reply_with_embed(ctx, build_error_embed(f"Argumen kurang untuk `{ctx.command}`. Cek `!helpmusic`."))
        return
    if isinstance(error, commands.BadArgument):
        await reply_with_embed(ctx, build_error_embed("Format argumen tidak valid. Cek `!helpmusic`."))
        return
    if isinstance(error, commands.CommandInvokeError):
        await reply_with_embed(ctx, build_error_embed(f"Terjadi error saat menjalankan command: `{error.original}`"))
        return
    raise error


def main():
    token_sources = [
        ("env DISCORD_MUSIC_TOKEN", os.getenv("DISCORD_MUSIC_TOKEN")),
        ("env MUSIC_BOT_TOKEN", os.getenv("MUSIC_BOT_TOKEN")),
        ("env DISCORD_BOT_TOKEN", os.getenv("DISCORD_BOT_TOKEN")),
    ]
    token = None
    token_source = None

    for source_name, candidate in token_sources:
        candidate = (candidate or "").strip().strip("'").strip('"')
        if candidate:
            token = candidate
            token_source = source_name
            break

    if not token:
        raise RuntimeError(
            "Token tidak ditemukan. Set DISCORD_MUSIC_TOKEN di .env, lalu restart bot."
        )

    try:
        bot.run(token)
    except discord.errors.LoginFailure as e:
        raise RuntimeError(
            f"Token Discord tidak valid atau sudah di-reset. Sumber token yang dipakai: {token_source}. "
            "Perbarui token bot di `.env` (DISCORD_MUSIC_TOKEN), lalu restart bot."
        ) from e
    except discord.errors.PrivilegedIntentsRequired as e:
        raise RuntimeError(
            "Message Content Intent belum aktif. Buka Discord Developer Portal -> Bot -> Privileged Gateway Intents -> aktifkan Message Content Intent, lalu restart bot."
        ) from e


if __name__ == "__main__":
    main()
