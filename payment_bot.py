import asyncio
import atexit
import json
import os
import re
import tempfile
from datetime import datetime
from env_loader import load_env_file
import discord
from discord import app_commands


load_env_file()
BOT_TOKEN = os.getenv("PAYMENT_BOT_TOKEN", "").strip()
TICKETS_FILE = "payment_tickets.json"
PAYMENT_CATEGORY_NAME = "payment-tickets"
QRIS_IMAGE_PATH = os.getenv("PAYMENT_QRIS_PATH", "qris.jpg")
QRIS_IMAGE_URL = os.getenv("PAYMENT_QRIS_URL", "")
SCRIPT_PANEL_GUILD_ID = os.getenv("SCRIPT_PANEL_GUILD_ID", "1472920057679056929").strip()
SCRIPT_PANEL_CHANNEL_ID = os.getenv("SCRIPT_PANEL_CHANNEL_ID", "1477467127563686063").strip()
SCRIPT_PANEL_URL = os.getenv("SCRIPT_PANEL_URL", "").strip()
if not SCRIPT_PANEL_URL and SCRIPT_PANEL_GUILD_ID and SCRIPT_PANEL_CHANNEL_ID:
    SCRIPT_PANEL_URL = f"https://discord.com/channels/{SCRIPT_PANEL_GUILD_ID}/{SCRIPT_PANEL_CHANNEL_ID}"
OWNER_IDS = [975269168184168539]
OWNER_ROLE_IDS = []

LOCK_DIR = os.path.join(tempfile.gettempdir(), "payment_bot_locks")
INSTANCE_LOCK_PATH = os.path.join(LOCK_DIR, "payment_bot.instance.lock")
_instance_lock_fd = None


def normalize_tickets(data):
    if not isinstance(data, dict):
        data = {}
    user_tickets = data.get("user_tickets")
    channels = data.get("channels")
    if not isinstance(user_tickets, dict):
        user_tickets = {}
    if not isinstance(channels, dict):
        channels = {}
    return {"user_tickets": user_tickets, "channels": channels}


def ensure_lock_dir():
    try:
        os.makedirs(LOCK_DIR, exist_ok=True)
    except Exception:
        pass


def acquire_instance_lock():
    global _instance_lock_fd
    ensure_lock_dir()
    try:
        _instance_lock_fd = os.open(INSTANCE_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(_instance_lock_fd, str(os.getpid()).encode("utf-8"))
        return True
    except FileExistsError:
        try:
            with open(INSTANCE_LOCK_PATH, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            stale_pid = int(raw) if raw else None
        except Exception:
            stale_pid = None

        is_stale = False
        if stale_pid is None:
            is_stale = True
        else:
            try:
                os.kill(stale_pid, 0)
            except OSError:
                is_stale = True
            except Exception:
                is_stale = False

        if is_stale:
            try:
                os.remove(INSTANCE_LOCK_PATH)
            except Exception:
                return False
            try:
                _instance_lock_fd = os.open(INSTANCE_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(_instance_lock_fd, str(os.getpid()).encode("utf-8"))
                return True
            except Exception:
                return False

        return False
    except Exception:
        return False


def release_instance_lock():
    global _instance_lock_fd
    try:
        if _instance_lock_fd is not None:
            os.close(_instance_lock_fd)
            _instance_lock_fd = None
    except Exception:
        pass
    try:
        if os.path.exists(INSTANCE_LOCK_PATH):
            os.remove(INSTANCE_LOCK_PATH)
    except Exception:
        pass


def acquire_user_create_lock(guild_id: int, user_id: int):
    ensure_lock_dir()
    lock_path = os.path.join(LOCK_DIR, f"{guild_id}_{user_id}.lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        return fd, lock_path
    except FileExistsError:
        return None, lock_path


def release_user_create_lock(fd, lock_path):
    try:
        if fd is not None:
            os.close(fd)
    except Exception:
        pass
    try:
        if lock_path and os.path.exists(lock_path):
            os.remove(lock_path)
    except Exception:
        pass


def load_tickets():
    if os.path.exists(TICKETS_FILE):
        try:
            with open(TICKETS_FILE, "r", encoding="utf-8") as f:
                return normalize_tickets(json.load(f))
        except Exception:
            pass
    return normalize_tickets({})


def save_tickets(data):
    data = normalize_tickets(data)
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


def get_owner_mentions(guild: discord.Guild) -> str:
    mentions = []
    for owner_id in OWNER_IDS:
        member = guild.get_member(owner_id)
        mentions.append(member.mention if member else f"<@{owner_id}>")
    return " ".join(mentions)


def user_ticket_key(guild_id: int, user_id: int) -> str:
    return f"{guild_id}:{user_id}"


def channel_ticket_key(channel_id: int) -> str:
    return str(channel_id)


def get_or_create_payment_category(guild: discord.Guild):
    target_name = PAYMENT_CATEGORY_NAME.strip().lower()
    matches = []
    for category in guild.categories:
        if category.name.strip().lower() == target_name:
            matches.append(category)
    if not matches:
        return None
    matches.sort(key=lambda c: (c.position, c.id))
    return matches[0]


async def delete_payment_category_if_empty(guild: discord.Guild, category_id: int | None):
    if not category_id:
        return
    category = guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        return
    if len(category.channels) > 0:
        return
    try:
        await category.delete(reason="No active ticket channels left")
    except Exception:
        pass


async def ensure_single_payment_category(guild: discord.Guild):
    target_name = PAYMENT_CATEGORY_NAME.strip().lower()
    matches = []
    for category in guild.categories:
        if category.name.strip().lower() == target_name:
            matches.append(category)

    if not matches:
        return await guild.create_category(PAYMENT_CATEGORY_NAME, reason="Create payment ticket category")

    matches.sort(key=lambda c: (c.position, c.id))
    primary = matches[0]
    duplicates = matches[1:]

    for dup in duplicates:
        for ch in list(dup.channels):
            try:
                await ch.edit(category=primary, reason="Merge duplicate payment ticket category")
            except Exception:
                pass
        if len(dup.channels) == 0:
            try:
                await dup.delete(reason="Remove duplicate payment ticket category")
            except Exception:
                pass

    return primary


async def reconcile_single_open_ticket_for_user(guild: discord.Guild, user_id: int, data):
    open_channels = find_open_ticket_channels_for_user(guild, user_id)
    if not open_channels:
        return None

    primary = open_channels[0]
    ukey = user_ticket_key(guild.id, user_id)
    pkey = str(primary.id)

    data["user_tickets"][ukey] = primary.id
    if pkey not in data["channels"]:
        data["channels"][pkey] = {
            "guild_id": guild.id,
            "channel_id": primary.id,
            "user_id": user_id,
            "status": "open",
            "created_at": datetime.now().isoformat(),
        }
    else:
        data["channels"][pkey]["status"] = "open"

    for dup in open_channels[1:]:
        dkey = str(dup.id)
        info = data["channels"].get(dkey, {
            "guild_id": guild.id,
            "channel_id": dup.id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
        })
        info["status"] = "closed"
        info["closed_at"] = datetime.now().isoformat()
        data["channels"][dkey] = info
        try:
            await dup.delete(reason="Duplicate ticket cleanup (1 user = 1 ticket)")
        except Exception:
            pass

    save_tickets(data)
    return primary


def find_existing_open_ticket_from_data(guild: discord.Guild, user_id: int, data):
    for info in data.get("channels", {}).values():
        if info.get("status") != "open":
            continue
        if int(info.get("guild_id", 0)) != guild.id:
            continue
        if int(info.get("user_id", 0)) != user_id:
            continue
        ch = guild.get_channel(int(info.get("channel_id", 0)))
        if ch is not None:
            return ch
    return None


def find_existing_open_ticket_channel(guild: discord.Guild, user_id: int, data):
    for info in data.get("channels", {}).values():
        if info.get("status") != "open":
            continue
        if int(info.get("guild_id", 0)) != guild.id:
            continue
        if int(info.get("user_id", 0)) != user_id:
            continue
        channel = guild.get_channel(int(info.get("channel_id", 0)))
        if channel is not None:
            return channel

    marker = f"customer_id={user_id}"
    for channel in guild.text_channels:
        topic = channel.topic or ""
        if marker in topic:
            info = data.get("channels", {}).get(str(channel.id))
            if info and str(info.get("status", "open")).lower() in {"closed", "done"}:
                continue
            return channel

    return None


def find_open_ticket_channels_for_user(guild: discord.Guild, user_id: int):
    marker = f"customer_id={user_id}"
    channels = []
    for channel in guild.text_channels:
        topic = channel.topic or ""
        if marker in topic:
            channels.append(channel)
    channels.sort(key=lambda c: c.id)
    return channels


def extract_customer_id_from_topic(topic: str):
    if not topic:
        return None
    match = re.search(r"customer_id=(\d+)", topic)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def resolve_ticket_info_for_channel(data, channel: discord.abc.GuildChannel):
    ckey = channel_ticket_key(channel.id)
    info = data["channels"].get(ckey)
    if info:
        return ckey, info

    customer_id = extract_customer_id_from_topic(getattr(channel, "topic", "") or "")
    if customer_id is None:
        return ckey, None

    info = {
        "guild_id": channel.guild.id,
        "channel_id": channel.id,
        "user_id": customer_id,
        "status": "open",
        "created_at": datetime.now().isoformat(),
    }
    data["channels"][ckey] = info
    data["user_tickets"][user_ticket_key(channel.guild.id, customer_id)] = channel.id
    save_tickets(data)
    return ckey, info


def mark_ticket_closed(data, ckey, info):
    info["status"] = "closed"
    info["closed_at"] = datetime.now().isoformat()
    data["channels"][ckey] = info
    ukey = user_ticket_key(info["guild_id"], info["user_id"])
    if ukey in data["user_tickets"]:
        del data["user_tickets"][ukey]
    save_tickets(data)


def rollback_ticket_open(data, ckey, info):
    info["status"] = "open"
    info.pop("closed_at", None)
    data["channels"][ckey] = info
    ukey = user_ticket_key(info["guild_id"], info["user_id"])
    data["user_tickets"][ukey] = info["channel_id"]
    save_tickets(data)


async def send_ticket_panel_message(channel: discord.TextChannel, customer: discord.abc.User, guild: discord.Guild):
    owner_mentions = get_owner_mentions(guild)
    info_embed = discord.Embed(
        title="Payment Ticket Opened",
        description="Ticket berhasil dibuat.",
        color=0x0099FF,
    )
    info_embed.add_field(
        name="Customer",
        value=customer.mention,
        inline=True,
    )
    info_embed.add_field(
        name="Status",
        value="Menunggu owner merespons",
        inline=True,
    )
    info_embed.add_field(
        name="Instruksi",
        value="Jelaskan produk yang akan dibeli. Owner akan lanjutkan proses transaksi di sini.",
        inline=False,
    )
    info_embed.set_footer(text=f"Payment Bot | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    await channel.send(
        content=f"{customer.mention} {owner_mentions}".strip(),
        embed=info_embed,
        view=TicketControlView(),
    )


async def send_ticket_closed_dm(
    customer: discord.abc.User,
    closed_by: discord.abc.User,
    ticket_name: str,
    server_name: str,
    reason: str = "No reason provided",
):
    safe_reason = (reason or "No reason provided").strip()
    if len(safe_reason) > 1000:
        safe_reason = safe_reason[:1000] + "..."

    closed_embed = discord.Embed(
        title="Ticket Closed",
        description=f"This ticket has been closed by {closed_by.mention}.",
        color=0xF1C40F,
    )
    closed_embed.add_field(name="Reason", value=safe_reason, inline=False)
    closed_embed.add_field(name="Ticket Name", value=ticket_name, inline=False)
    closed_embed.add_field(name="Server", value=server_name, inline=False)
    closed_embed.set_footer(text=f"Payment Bot | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    await customer.send(embed=closed_embed)


async def close_ticket_channel(interaction: discord.Interaction, data, ckey, info, reason: str = "No reason provided"):
    close_reason = (reason or "No reason provided").strip() or "No reason provided"
    category_id = interaction.channel.category_id if interaction.channel else None
    guild = interaction.guild
    ticket_name = interaction.channel.name if interaction.channel else "unknown-ticket"
    server_name = guild.name if guild else "Unknown Server"
    customer = None
    user_id = info.get("user_id")
    customer_id = None
    if user_id is not None:
        try:
            customer_id = int(user_id)
        except (TypeError, ValueError):
            customer_id = None
    if customer_id is not None:
        customer = client.get_user(customer_id)
        if customer is None:
            try:
                customer = await client.fetch_user(customer_id)
            except Exception:
                customer = None

    mark_ticket_closed(data, ckey, info)
    interaction_ack = True
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            interaction_ack = False
        except Exception:
            interaction_ack = False

    try:
        if interaction.channel:
            await interaction.channel.send("Ticket telah ditutup...")
        elif interaction_ack:
            await interaction.followup.send("Ticket telah ditutup...", ephemeral=True)
    except Exception:
        pass

    await asyncio.sleep(3)

    try:
        if customer is not None:
            try:
                await send_ticket_closed_dm(
                    customer=customer,
                    closed_by=interaction.user,
                    ticket_name=ticket_name,
                    server_name=server_name,
                    reason=close_reason,
                )
            except discord.Forbidden:
                pass
            except Exception:
                pass

        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        if guild is not None:
            await delete_payment_category_if_empty(guild, category_id)
    except discord.Forbidden:
        rollback_ticket_open(data, ckey, info)
        if interaction_ack:
            await interaction.followup.send(
                "Gagal menutup ticket: bot tidak punya izin `Manage Channels`/`Delete Channels`.",
                ephemeral=True,
            )
    except discord.HTTPException as e:
        rollback_ticket_open(data, ckey, info)
        if interaction_ack:
            await interaction.followup.send(
                f"Gagal menutup ticket: {e}",
                ephemeral=True,
            )


class CloseTicketReasonModal(discord.ui.Modal):
    def __init__(self, data, ckey, info):
        super().__init__(title="Close Ticket Reason", custom_id="close_ticket_reason_modal")
        self.data = data
        self.ckey = ckey
        self.info = info
        self.reason_input = discord.ui.TextInput(
            label="Reason",
            placeholder="Tuliskan alasan ticket ditutup",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=3,
            max_length=500,
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value.strip()
        if not reason:
            await interaction.response.send_message("Alasan wajib diisi.", ephemeral=True)
            return

        owner_allowed = is_owner(interaction.user.id) or interaction.user.guild_permissions.manage_channels
        ticket_owner_allowed = str(interaction.user.id) == str(self.info.get("user_id"))
        if not (owner_allowed or ticket_owner_allowed):
            await interaction.response.send_message("Kamu tidak punya izin menutup ticket ini.", ephemeral=True)
            return

        latest_data = load_tickets()
        latest_ckey, latest_info = resolve_ticket_info_for_channel(latest_data, interaction.channel)
        latest_status = str(latest_info.get("status", "open")).lower() if latest_info else "unknown"
        if not latest_info or latest_status not in {"open", "done"}:
            await interaction.response.send_message("Ticket tidak ditemukan atau sudah ditutup.", ephemeral=True)
            return

        await close_ticket_channel(interaction, latest_data, latest_ckey, latest_info, reason=reason)


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Mark Paid", style=discord.ButtonStyle.green, custom_id="mark_paid_ticket_btn")
    async def mark_paid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        interaction_ack = True
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.NotFound:
                interaction_ack = False
            except Exception:
                interaction_ack = False

        if interaction.guild is None:
            if interaction_ack:
                await interaction.followup.send("Gunakan tombol ini di server.", ephemeral=True)
            return

        if (not is_owner(interaction.user.id)) and (not interaction.user.guild_permissions.manage_channels):
            if interaction_ack:
                await interaction.followup.send("Hanya owner/admin yang bisa menandai tiket sebagai paid.", ephemeral=True)
            return

        data = load_tickets()
        _, info = resolve_ticket_info_for_channel(data, interaction.channel)
        if not info or info.get("status") != "open":
            if interaction_ack:
                await interaction.followup.send("Data ticket tidak ditemukan atau sudah ditutup.", ephemeral=True)
            return

        customer_id = int(info["user_id"])
        customer = interaction.guild.get_member(customer_id)
        customer_mention = customer.mention if customer else f"<@{customer_id}>"

        embed = discord.Embed(
            title="Payment Confirmed",
            description=f"{customer_mention} pembayaran sudah dikonfirmasi owner.",
            color=0x00FF88,
        )
        embed.add_field(
            name="Langkah Selanjutnya",
            value="1. Klik tombol Open Customer Panel\n2. Redeem key dari owner\n3. Coba akses bot setelah redeem berhasil",
            inline=False,
        )
        if not SCRIPT_PANEL_URL:
            embed.add_field(
                name="Catatan",
                value="Set env `SCRIPT_PANEL_URL` agar tombol Open Script Panel aktif.",
                inline=False,
            )
        embed.set_footer(text=f"Payment Bot | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        panel_view = None
        if SCRIPT_PANEL_URL:
            panel_view = discord.ui.View()
            panel_view.add_item(discord.ui.Button(label="Open Customer Panel", style=discord.ButtonStyle.link, url=SCRIPT_PANEL_URL))
        if interaction.channel:
            await interaction.channel.send(embed=embed, view=panel_view)
        elif interaction_ack:
            await interaction.followup.send(embed=embed, view=panel_view, ephemeral=True)

        dm_embed = discord.Embed(
            title="Pembayaran Dikonfirmasi",
            description="Pembayaran kamu sudah dikonfirmasi owner.",
            color=0x00FF88,
        )
        dm_embed.add_field(
            name="Server",
            value=interaction.guild.name,
            inline=True,
        )
        dm_embed.add_field(
            name="Ticket",
            value=interaction.channel.name if interaction.channel else "N/A",
            inline=True,
        )
        dm_embed.add_field(
            name="Langkah Selanjutnya",
            value="Klik tombol Open Customer Panel, redeem key dari owner, lalu cek akses bot kamu.",
            inline=False,
        )
        dm_embed.set_footer(text=f"Payment Bot | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        if customer:
            try:
                if SCRIPT_PANEL_URL:
                    dm_view = discord.ui.View()
                    dm_view.add_item(discord.ui.Button(label="Open Customer Panel", style=discord.ButtonStyle.link, url=SCRIPT_PANEL_URL))
                    await customer.send(embed=dm_embed, view=dm_view)
                else:
                    await customer.send(embed=dm_embed)
            except discord.Forbidden:
                if interaction_ack:
                    await interaction.followup.send(
                        f"Tidak bisa kirim DM ke {customer_mention} (DM user tertutup).",
                        ephemeral=True,
                    )

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            await interaction.response.send_message("Gunakan tombol ini di server.", ephemeral=True)
            return

        data = load_tickets()
        ckey, info = resolve_ticket_info_for_channel(data, interaction.channel)
        if not info:
            await interaction.response.send_message("Ticket ini tidak terdaftar.", ephemeral=True)
            return

        owner_allowed = is_owner(interaction.user.id) or interaction.user.guild_permissions.manage_channels
        ticket_owner_allowed = str(interaction.user.id) == str(info.get("user_id"))
        if not (owner_allowed or ticket_owner_allowed):
            await interaction.response.send_message("Kamu tidak punya izin menutup ticket ini.", ephemeral=True)
            return

        await interaction.response.send_modal(CloseTicketReasonModal(data, ckey, info))


class PaymentPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Transaction Ticket", style=discord.ButtonStyle.blurple, custom_id="create_payment_ticket_btn")
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            await interaction.response.send_message("Gunakan tombol ini di server.", ephemeral=True)
            return

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        ukey = user_ticket_key(guild.id, interaction.user.id)
        lock_fd, lock_path = acquire_user_create_lock(guild.id, interaction.user.id)
        if lock_fd is None:
            await interaction.followup.send(
                "Permintaan create ticket sedang diproses. Tunggu 2-3 detik lalu cek lagi.",
                ephemeral=True,
            )
            return

        if ukey not in _create_ticket_locks:
            _create_ticket_locks[ukey] = asyncio.Lock()

        try:
            async with _create_ticket_locks[ukey]:
                data = load_tickets()

                reconciled_channel = await reconcile_single_open_ticket_for_user(guild, interaction.user.id, data)
                if reconciled_channel is not None:
                    try:
                        await send_ticket_panel_message(reconciled_channel, interaction.user, guild)
                    except Exception:
                        await interaction.followup.send(
                            f"Ticket aktif ditemukan ({reconciled_channel.mention}), tapi panel gagal dikirim ulang.",
                            ephemeral=True,
                        )
                    else:
                        await interaction.followup.send(
                            f"Kamu sudah punya ticket aktif: {reconciled_channel.mention}",
                            ephemeral=True,
                        )
                    return

                existing_channel = find_existing_open_ticket_from_data(guild, interaction.user.id, data)
                if existing_channel is None:
                    existing_channel = find_existing_open_ticket_channel(guild, interaction.user.id, data)
                if existing_channel is not None:
                    data["user_tickets"][ukey] = existing_channel.id
                    if str(existing_channel.id) not in data["channels"]:
                        data["channels"][str(existing_channel.id)] = {
                            "guild_id": guild.id,
                            "channel_id": existing_channel.id,
                            "user_id": interaction.user.id,
                            "status": "open",
                            "created_at": datetime.now().isoformat(),
                        }
                    save_tickets(data)
                    try:
                        await send_ticket_panel_message(existing_channel, interaction.user, guild)
                    except Exception:
                        await interaction.followup.send(
                            f"Ticket aktif ditemukan ({existing_channel.mention}), tapi panel gagal dikirim ulang.",
                            ephemeral=True,
                        )
                    else:
                        await interaction.followup.send(
                            f"Kamu sudah punya ticket aktif: {existing_channel.mention}",
                            ephemeral=True,
                        )
                    return

                try:
                    category = await ensure_single_payment_category(guild)
                except discord.Forbidden:
                    await interaction.followup.send(
                        "Bot tidak punya izin `Manage Channels` untuk membuat kategori ticket.",
                        ephemeral=True,
                    )
                    return
                except discord.HTTPException as e:
                    await interaction.followup.send(
                        f"Gagal membuat kategori ticket: {e}",
                        ephemeral=True,
                    )
                    return

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True,
                        embed_links=True,
                    ),
                }

                bot_member = guild.me or guild.get_member(client.user.id)
                if bot_member:
                    overwrites[bot_member] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True,
                        embed_links=True,
                        attach_files=True,
                    )

                for owner_id in OWNER_IDS:
                    member = guild.get_member(owner_id)
                    if member:
                        overwrites[member] = discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=True,
                            manage_channels=True,
                            read_message_history=True,
                        )

                for role_id in OWNER_ROLE_IDS:
                    role = guild.get_role(role_id)
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(
                            view_channel=True,
                            send_messages=True,
                            manage_channels=True,
                            read_message_history=True,
                        )

                base_name = f"ticket-{interaction.user.name}".lower()
                safe_name = re.sub(r"[^a-z0-9-]", "-", base_name.replace(" ", "-"))
                safe_name = re.sub(r"-{2,}", "-", safe_name).strip("-")
                if not safe_name:
                    safe_name = f"ticket-{interaction.user.id}"

                data = load_tickets()
                existing_channel = find_existing_open_ticket_channel(guild, interaction.user.id, data)
                if existing_channel is not None:
                    data["user_tickets"][ukey] = existing_channel.id
                    if str(existing_channel.id) not in data["channels"]:
                        data["channels"][str(existing_channel.id)] = {
                            "guild_id": guild.id,
                            "channel_id": existing_channel.id,
                            "user_id": interaction.user.id,
                            "status": "open",
                            "created_at": datetime.now().isoformat(),
                        }
                    save_tickets(data)
                    try:
                        await send_ticket_panel_message(existing_channel, interaction.user, guild)
                    except Exception:
                        await interaction.followup.send(
                            f"Ticket aktif ditemukan ({existing_channel.mention}), tapi panel gagal dikirim ulang.",
                            ephemeral=True,
                        )
                    else:
                        await interaction.followup.send(
                            f"Kamu sudah punya ticket aktif: {existing_channel.mention}",
                            ephemeral=True,
                        )
                    return

                try:
                    channel = await guild.create_text_channel(
                        safe_name[:90],
                        category=category,
                        overwrites=overwrites,
                        topic=f"Payment ticket | customer_id={interaction.user.id}",
                        reason="New payment ticket created",
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        "Bot tidak punya izin membuat channel ticket. Cek permission role bot.",
                        ephemeral=True,
                    )
                    return
                except discord.HTTPException as e:
                    await interaction.followup.send(
                        f"Gagal membuat channel ticket: {e}",
                        ephemeral=True,
                    )
                    return

                try:
                    await ensure_single_payment_category(guild)
                except Exception:
                    pass

                open_channels = find_open_ticket_channels_for_user(guild, interaction.user.id)
                if len(open_channels) > 1:
                    primary_channel = open_channels[0]
                    if primary_channel.id != channel.id:
                        try:
                            await channel.delete(reason="Duplicate ticket auto-cleanup")
                        except Exception:
                            pass
                        data = load_tickets()
                        data["user_tickets"][ukey] = primary_channel.id
                        if str(primary_channel.id) not in data["channels"]:
                            data["channels"][str(primary_channel.id)] = {
                                "guild_id": guild.id,
                                "channel_id": primary_channel.id,
                                "user_id": interaction.user.id,
                                "status": "open",
                                "created_at": datetime.now().isoformat(),
                            }
                        save_tickets(data)
                        try:
                            await send_ticket_panel_message(primary_channel, interaction.user, guild)
                        except Exception:
                            await interaction.followup.send(
                                f"Ticket aktif ditemukan ({primary_channel.mention}), tapi panel gagal dikirim ulang.",
                                ephemeral=True,
                            )
                        else:
                            await interaction.followup.send(
                                f"Kamu sudah punya ticket aktif: {primary_channel.mention}",
                                ephemeral=True,
                            )
                        return

                data["user_tickets"][ukey] = channel.id
                data["channels"][str(channel.id)] = {
                    "guild_id": guild.id,
                    "channel_id": channel.id,
                    "user_id": interaction.user.id,
                    "status": "open",
                    "created_at": datetime.now().isoformat(),
                }
                save_tickets(data)

                try:
                    await send_ticket_panel_message(channel, interaction.user, guild)
                except discord.Forbidden:
                    data["channels"].pop(str(channel.id), None)
                    data["user_tickets"].pop(ukey, None)
                    save_tickets(data)
                    await interaction.followup.send(
                        "Ticket dibuat tapi bot tidak punya akses kirim panel ke channel ticket. Cek permission role bot.",
                        ephemeral=True,
                    )
                    return
                except discord.HTTPException as e:
                    data["channels"].pop(str(channel.id), None)
                    data["user_tickets"].pop(ukey, None)
                    save_tickets(data)
                    await interaction.followup.send(
                        f"Gagal kirim panel awal ke ticket: {e}",
                        ephemeral=True,
                    )
                    return

                await interaction.followup.send(f"Ticket berhasil dibuat: {channel.mention}", ephemeral=True)
        finally:
            release_user_create_lock(lock_fd, lock_path)


intents = discord.Intents.default()

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
_panel_view = None
_ticket_control_view = None
_create_ticket_locks = {}


@tree.command(name="payment_panel", description="Kirim panel ticket transaksi key")
@app_commands.default_permissions(manage_channels=True)
async def payment_panel(interaction: discord.Interaction):
    if not interaction.response.is_done():
        try:
            await interaction.response.defer()
        except Exception:
            pass

    embed = discord.Embed(
        title="Key Transaction Panel",
        description="Panel ini dipakai untuk mempertemukan customer dan owner dalam transaksi key bot.",
        color=0x0099FF,
    )
    embed.add_field(
        name="Cara Pakai",
        value="Klik tombol di bawah untuk membuat ticket privat transaksi.",
        inline=False,
    )
    embed.set_footer(text=f"Payment Bot | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    global _panel_view
    if _panel_view is None:
        _panel_view = PaymentPanelView()
        client.add_view(_panel_view)

    try:
        await interaction.followup.send(embed=embed, view=_panel_view)
    except discord.NotFound:
        if interaction.channel:
            await interaction.channel.send(embed=embed, view=_panel_view)


@tree.command(name="close_ticket", description="Tutup ticket transaksi channel ini")
@app_commands.describe(reason="Alasan penutupan ticket")
async def close_ticket(interaction: discord.Interaction, reason: str):
    reason = reason.strip()
    if not reason:
        await interaction.response.send_message("Alasan wajib diisi.", ephemeral=True)
        return

    data = load_tickets()
    ckey, info = resolve_ticket_info_for_channel(data, interaction.channel)
    if not info:
        await interaction.response.send_message("Perintah ini hanya bisa dipakai di channel ticket.", ephemeral=True)
        return

    owner_allowed = is_owner(interaction.user.id) or interaction.user.guild_permissions.manage_channels
    ticket_owner_allowed = str(interaction.user.id) == str(info.get("user_id"))
    if not (owner_allowed or ticket_owner_allowed):
        await interaction.response.send_message("Kamu tidak punya izin menutup ticket ini.", ephemeral=True)
        return

    await close_ticket_channel(interaction, data, ckey, info, reason=reason)


@tree.command(name="done", description="Tandai transaksi di ticket ini sebagai selesai")
async def done(interaction: discord.Interaction):
    data = load_tickets()
    ckey, info = resolve_ticket_info_for_channel(data, interaction.channel)
    if not info:
        await interaction.response.send_message("Perintah ini hanya bisa dipakai di channel ticket.", ephemeral=True)
        return

    owner_allowed = is_owner(interaction.user.id) or interaction.user.guild_permissions.manage_channels
    ticket_owner_allowed = str(interaction.user.id) == str(info.get("user_id"))
    if not (owner_allowed or ticket_owner_allowed):
        await interaction.response.send_message("Kamu tidak punya izin menandai ticket ini sebagai done.", ephemeral=True)
        return

    status = str(info.get("status", "open")).lower()
    if status == "closed":
        await interaction.response.send_message("Ticket ini sudah ditutup.", ephemeral=True)
        return
    if status == "done":
        await interaction.response.send_message("Ticket ini sudah ditandai done sebelumnya.", ephemeral=True)
        return

    info["status"] = "done"
    info["done_at"] = datetime.now().isoformat()
    data["channels"][ckey] = info
    ukey = user_ticket_key(info["guild_id"], info["user_id"])
    if ukey in data["user_tickets"]:
        del data["user_tickets"][ukey]
    save_tickets(data)

    done_embed = discord.Embed(
        title="Transaksi Selesai",
        description="Terimakasih sudah percaya dengan DrxDvs. TRXStatus: **DONE**.",
        color=0x00FF88,
    )
    done_embed.add_field(name="Ditandai Oleh", value=interaction.user.mention, inline=True)
    done_embed.add_field(name="Waktu", value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"), inline=True)
    done_embed.set_footer(text="Payment Bot")
    await interaction.response.send_message(embed=done_embed)


@tree.command(name="payment", description="Tampilkan QRIS pembayaran")
async def payment(interaction: discord.Interaction):
    embed = discord.Embed(
        title="QRIS Payment",
        description="Scan QRIS di bawah untuk melakukan pembayaran.",
        color=0x00AAFF,
    )
    embed.set_footer(text=f"Payment Bot | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    if os.path.exists(QRIS_IMAGE_PATH):
        file = discord.File(QRIS_IMAGE_PATH, filename="qris.png")
        embed.set_image(url="attachment://qris.png")
        await interaction.response.send_message(embed=embed, file=file)
        return

    if QRIS_IMAGE_URL:
        embed.set_image(url=QRIS_IMAGE_URL)
        await interaction.response.send_message(embed=embed)
        return

    await interaction.response.send_message(
        "Gambar QRIS belum tersedia. Tambahkan file `qris.jpg` atau set env `PAYMENT_QRIS_URL`.",
        ephemeral=True,
    )


@client.event
async def on_ready():
    global _panel_view, _ticket_control_view
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs")
    )
    _panel_view = PaymentPanelView()
    _ticket_control_view = TicketControlView()
    client.add_view(_panel_view)
    client.add_view(_ticket_control_view)

    try:
        await tree.sync()
    except Exception as e:
        print(f"Error syncing commands: {e}")

    print(f"Payment bot online as {client.user}")


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("PAYMENT_BOT_TOKEN belum di-set. Set env var PAYMENT_BOT_TOKEN dulu.")
    if not acquire_instance_lock():
        raise RuntimeError("payment_bot.py sudah berjalan di proses lain. Tutup instance lama dulu.")
    atexit.register(release_instance_lock)
    client.run(BOT_TOKEN)
