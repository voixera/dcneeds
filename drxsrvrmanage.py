import asyncio
import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Optional
from env_loader import load_env_file
import discord
from discord import app_commands


load_env_file()

TOKEN = (
    os.getenv("DISCORD_SRVRMANAGE_TOKEN")
    or os.getenv("DISCORD_SERVERMANAGE_TOKEN")
    or os.getenv("DISCORD_BOT_TOKEN")
    or ""
).strip()

CONFIG_FILE = Path(os.getenv("SRVRMANAGE_CONFIG_FILE") or "srvrmanage_config.json")
EMBED_COLOR = discord.Color.from_rgb(32, 34, 37)


def _safe_int(value) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(data: dict) -> None:
    tmp = CONFIG_FILE.with_suffix(CONFIG_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def get_log_channel_id(guild_id: int) -> Optional[int]:
    data = load_config()
    cfg = data.get(str(guild_id))
    if not isinstance(cfg, dict):
        return None
    return _safe_int(cfg.get("log_channel_id"))


def set_log_channel_id(guild_id: int, channel_id: Optional[int]) -> None:
    data = load_config()
    key = str(guild_id)
    cfg = data.get(key)
    if not isinstance(cfg, dict):
        cfg = {}
        data[key] = cfg
    if channel_id is None:
        cfg.pop("log_channel_id", None)
    else:
        cfg["log_channel_id"] = int(channel_id)
    save_config(data)


async def send_log(guild: discord.Guild, embed: discord.Embed) -> None:
    channel_id = get_log_channel_id(guild.id)
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel is None or not hasattr(channel, "send"):
        return
    try:
        await channel.send(embed=embed)
    except Exception:
        pass


def is_member(interaction: discord.Interaction) -> bool:
    return interaction.guild is not None and isinstance(interaction.user, discord.Member)


def has_perm(interaction: discord.Interaction, perm_name: str) -> bool:
    if not is_member(interaction):
        return False
    perms = interaction.user.guild_permissions
    return bool(getattr(perms, perm_name, False) or perms.administrator)


def build_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(description=description, color=EMBED_COLOR)
    embed.set_author(name=title)
    return embed


class ConfirmView(discord.ui.View):
    def __init__(self, requester_id: int, timeout: float = 25.0):
        super().__init__(timeout=timeout)
        self.requester_id = requester_id
        self.value: Optional[bool] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user is None or interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "Hanya user yang menjalankan command ini yang bisa konfirmasi.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


def can_manage_target(invoker: discord.Member, target: discord.Member) -> bool:
    if invoker.guild.owner_id == invoker.id:
        return True
    if target.guild.owner_id == target.id:
        return False
    return invoker.top_role > target.top_role


def can_bot_manage_role(guild: discord.Guild, role: discord.Role) -> bool:
    me = guild.me
    if me is None:
        return False
    return me.top_role > role



intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = False

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(name="srv_help", description="List fitur server manager")
async def srv_help(interaction: discord.Interaction) -> None:
    embed = build_embed(
        "🛠️ Server Manager",
        "\n".join(
            [
                "**Info**: `/serverinfo`, `/userinfo`, `/ping`",
                "**Moderasi**: `/purge`, `/kick`, `/ban`, `/unban`, `/timeout`, `/untimeout`",
                "**Channel**: `/lock`, `/unlock`, `/slowmode`, `/announce`, `/channel_create`, `/channel_delete`, `/channel_rename`",
                "**Role**: `/role_give`, `/role_take`, `/role_create`, `/role_delete`",
                "**Log**: `/setlog`",
            ]
        ),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="ping", description="Cek latency bot")
async def ping(interaction: discord.Interaction) -> None:
    latency_ms = int(client.latency * 1000)
    await interaction.response.send_message(
        embed=build_embed("🏓 Pong", f"Latency: **{latency_ms}ms**"),
        ephemeral=True,
    )


@tree.command(name="setlog", description="Set channel log untuk aksi moderasi (admin)")
async def setlog(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "administrator"):
        await interaction.response.send_message("Butuh permission **Administrator**.", ephemeral=True)
        return
    if channel is None:
        set_log_channel_id(interaction.guild.id, None)
        await interaction.response.send_message("Log channel dimatikan.", ephemeral=True)
        return
    set_log_channel_id(interaction.guild.id, channel.id)
    await interaction.response.send_message(f"Log channel diset ke {channel.mention}.", ephemeral=True)


@tree.command(name="serverinfo", description="Info server")
async def serverinfo(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    guild = interaction.guild
    embed = discord.Embed(title=guild.name, color=EMBED_COLOR)
    embed.add_field(name="ID", value=str(guild.id), inline=True)
    embed.add_field(name="Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Members", value=str(guild.member_count or "Unknown"), inline=True)
    embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="userinfo", description="Info user/member")
async def userinfo(interaction: discord.Interaction, member: Optional[discord.Member] = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    member = member or (interaction.user if isinstance(interaction.user, discord.Member) else None)
    if member is None:
        await interaction.response.send_message("Gagal membaca member.", ephemeral=True)
        return
    roles = [r.mention for r in member.roles if r != interaction.guild.default_role]
    embed = discord.Embed(title=str(member), color=EMBED_COLOR)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=str(member.id), inline=True)
    embed.add_field(
        name="Joined",
        value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "-",
        inline=True,
    )
    embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "-", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="purge", description="Hapus pesan (bulk delete)")
@app_commands.describe(amount="Jumlah pesan (1-100)", user="Opsional: hanya hapus dari user ini")
async def purge(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100],
    user: Optional[discord.Member] = None,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_messages"):
        await interaction.response.send_message("Butuh permission `Manage Messages`.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Command ini hanya untuk text channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    def check(msg: discord.Message) -> bool:
        return True if user is None else msg.author.id == user.id

    try:
        deleted = await interaction.channel.purge(
            limit=int(amount),
            check=check,
            reason=f"Purge by {interaction.user}",
        )
    except discord.Forbidden:
        await interaction.followup.send("Bot tidak punya izin `Manage Messages` / `Read Message History`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.followup.send(f"Gagal purge: {exc}", ephemeral=True)
        return

    await interaction.followup.send(embed=build_embed("🧹 Purge", f"Deleted **{len(deleted)}** messages."), ephemeral=True)
    await send_log(
        interaction.guild,
        build_embed("LOG: Purge", f"{interaction.user.mention} purge {len(deleted)} pesan di {interaction.channel.mention}."),
    )


@tree.command(name="kick", description="Kick member dari server")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "kick_members"):
        await interaction.response.send_message("Butuh permission `Kick Members`.", ephemeral=True)
        return
    if interaction.user is not None and member.id == interaction.user.id:
        await interaction.response.send_message("Tidak bisa kick diri sendiri.", ephemeral=True)
        return

    view = ConfirmView(interaction.user.id if interaction.user else 0)
    await interaction.response.send_message(
        embed=build_embed("Confirm Kick", f"Kick {member.mention}?"),
        view=view,
        ephemeral=True,
    )
    await view.wait()
    if view.value is not True:
        return

    try:
        await member.kick(reason=reason or f"Kick by {interaction.user}")
    except discord.Forbidden:
        await interaction.edit_original_response(embed=build_embed("Kick Failed", "Bot tidak punya izin `Kick Members`."), view=None)
        return
    except Exception as exc:
        await interaction.edit_original_response(embed=build_embed("Kick Failed", f"{exc}"), view=None)
        return

    await interaction.edit_original_response(embed=build_embed("✅ Kicked", f"{member} kicked."), view=None)
    await send_log(
        interaction.guild,
        build_embed("LOG: Kick", f"{interaction.user.mention} kick `{member}`. Reason: `{reason or '-'}`"),
    )


@tree.command(name="ban", description="Ban member dari server")
@app_commands.describe(delete_message_days="Hapus pesan terakhir (0-7 hari)")
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    delete_message_days: app_commands.Range[int, 0, 7] = 0,
    reason: Optional[str] = None,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "ban_members"):
        await interaction.response.send_message("Butuh permission `Ban Members`.", ephemeral=True)
        return
    if interaction.user is not None and member.id == interaction.user.id:
        await interaction.response.send_message("Tidak bisa ban diri sendiri.", ephemeral=True)
        return

    view = ConfirmView(interaction.user.id if interaction.user else 0)
    await interaction.response.send_message(
        embed=build_embed("Confirm Ban", f"Ban {member.mention}? (delete_message_days={delete_message_days})"),
        view=view,
        ephemeral=True,
    )
    await view.wait()
    if view.value is not True:
        return

    try:
        await interaction.guild.ban(
            member,
            reason=reason or f"Ban by {interaction.user}",
            delete_message_days=int(delete_message_days),
        )
    except discord.Forbidden:
        await interaction.edit_original_response(embed=build_embed("Ban Failed", "Bot tidak punya izin `Ban Members`."), view=None)
        return
    except Exception as exc:
        await interaction.edit_original_response(embed=build_embed("Ban Failed", f"{exc}"), view=None)
        return

    await interaction.edit_original_response(embed=build_embed("✅ Banned", f"{member} banned."), view=None)
    await send_log(
        interaction.guild,
        build_embed("LOG: Ban", f"{interaction.user.mention} ban `{member}`. Reason: `{reason or '-'}`"),
    )


@tree.command(name="unban", description="Unban user via user ID")
async def unban(interaction: discord.Interaction, user_id: str, reason: Optional[str] = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "ban_members"):
        await interaction.response.send_message("Butuh permission `Ban Members`.", ephemeral=True)
        return

    target_id = _safe_int("".join(ch for ch in (user_id or "") if ch.isdigit()))
    if target_id is None:
        await interaction.response.send_message("Format user_id tidak valid.", ephemeral=True)
        return

    try:
        user = await client.fetch_user(target_id)
        await interaction.guild.unban(user, reason=reason or f"Unban by {interaction.user}")
    except discord.NotFound:
        await interaction.response.send_message("User tidak ditemukan / tidak sedang keban.", ephemeral=True)
        return
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Ban Members`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal unban: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(embed=build_embed("✅ Unbanned", f"Unbanned <@{target_id}>."), ephemeral=True)
    await send_log(
        interaction.guild,
        build_embed("LOG: Unban", f"{interaction.user.mention} unban `<@{target_id}>`. Reason: `{reason or '-'}`"),
    )


@tree.command(name="timeout", description="Timeout member (mute sementara)")
@app_commands.describe(minutes="Durasi timeout (1-10080 menit)")
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 10080],
    reason: Optional[str] = None,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "moderate_members"):
        await interaction.response.send_message("Butuh permission `Moderate Members`.", ephemeral=True)
        return
    try:
        until = discord.utils.utcnow() + timedelta(minutes=int(minutes))
        await member.timeout(until, reason=reason or f"Timeout by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Moderate Members`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal timeout: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(
        embed=build_embed("⏳ Timed Out", f"{member.mention} timeout **{minutes} menit**."),
        ephemeral=True,
    )
    await send_log(
        interaction.guild,
        build_embed("LOG: Timeout", f"{interaction.user.mention} timeout `{member}` {minutes} menit. Reason: `{reason or '-'}`"),
    )


@tree.command(name="untimeout", description="Hapus timeout member")
async def untimeout(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "moderate_members"):
        await interaction.response.send_message("Butuh permission `Moderate Members`.", ephemeral=True)
        return
    try:
        await member.timeout(None, reason=reason or f"Untimeout by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Moderate Members`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal untimeout: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(
        embed=build_embed("✅ Timeout Cleared", f"Timeout cleared for {member.mention}."),
        ephemeral=True,
    )
    await send_log(
        interaction.guild,
        build_embed("LOG: Untimeout", f"{interaction.user.mention} untimeout `{member}`. Reason: `{reason or '-'}`"),
    )


@tree.command(name="slowmode", description="Set slowmode channel ini")
@app_commands.describe(seconds="0 untuk off (0-21600)")
async def slowmode(interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_channels"):
        await interaction.response.send_message("Butuh permission `Manage Channels`.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Command ini hanya untuk text channel.", ephemeral=True)
        return
    try:
        await interaction.channel.edit(slowmode_delay=int(seconds), reason=f"Slowmode by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Channels`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal set slowmode: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("🐢 Slowmode", f"Slowmode set ke **{seconds}s**."), ephemeral=True)


async def _set_send_messages(interaction: discord.Interaction, allowed: bool) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_channels"):
        await interaction.response.send_message("Butuh permission `Manage Channels`.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Command ini hanya untuk text channel.", ephemeral=True)
        return
    try:
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = allowed
        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=f"Lock by {interaction.user}",
        )
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Channels`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal update permission: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("🔒 Channel", "Unlocked" if allowed else "Locked"), ephemeral=True)


@tree.command(name="lock", description="Lock channel ini (disable send_messages untuk @everyone)")
async def lock(interaction: discord.Interaction) -> None:
    await _set_send_messages(interaction, allowed=False)


@tree.command(name="unlock", description="Unlock channel ini (enable send_messages untuk @everyone)")
async def unlock(interaction: discord.Interaction) -> None:
    await _set_send_messages(interaction, allowed=True)


@tree.command(name="announce", description="Kirim pengumuman ke channel")
async def announce(interaction: discord.Interaction, channel: discord.TextChannel, message: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_messages"):
        await interaction.response.send_message("Butuh permission `Manage Messages`.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        await channel.send(message)
    except discord.Forbidden:
        await interaction.followup.send("Bot tidak punya izin kirim pesan di channel itu.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.followup.send(f"Gagal kirim: {exc}", ephemeral=True)
        return
    await interaction.followup.send(embed=build_embed("📣 Announced", f"Sent to {channel.mention}"), ephemeral=True)


@tree.command(name="role_give", description="Kasih role ke member")
async def role_give(interaction: discord.Interaction, member: discord.Member, role: discord.Role) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_roles"):
        await interaction.response.send_message("Butuh permission `Manage Roles`.", ephemeral=True)
        return
    if not can_manage_target(interaction.user, member):
        await interaction.response.send_message("Kamu tidak bisa manage member ini (role hierarchy).", ephemeral=True)
        return
    if not can_bot_manage_role(interaction.guild, role):
        await interaction.response.send_message("Bot tidak bisa manage role itu. Naikkan posisi role bot.", ephemeral=True)
        return
    try:
        await member.add_roles(role, reason=f"Role give by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal kasih role: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("✅ Role Given", f"{role.mention} -> {member.mention}"), ephemeral=True)


@tree.command(name="role_take", description="Cabut role dari member")
async def role_take(interaction: discord.Interaction, member: discord.Member, role: discord.Role) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_roles"):
        await interaction.response.send_message("Butuh permission `Manage Roles`.", ephemeral=True)
        return
    if not can_manage_target(interaction.user, member):
        await interaction.response.send_message("Kamu tidak bisa manage member ini (role hierarchy).", ephemeral=True)
        return
    if not can_bot_manage_role(interaction.guild, role):
        await interaction.response.send_message("Bot tidak bisa manage role itu. Naikkan posisi role bot.", ephemeral=True)
        return
    try:
        await member.remove_roles(role, reason=f"Role take by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal cabut role: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("✅ Role Removed", f"{role.mention} <- {member.mention}"), ephemeral=True)


@tree.command(name="role_create", description="Buat role baru")
@app_commands.describe(color_hex="Contoh: #ff0000")
async def role_create(
    interaction: discord.Interaction,
    name: str,
    color_hex: str = "#5865F2",
    hoist: bool = False,
    mentionable: bool = False,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_roles"):
        await interaction.response.send_message("Butuh permission `Manage Roles`.", ephemeral=True)
        return
    try:
        color = discord.Color.from_str(color_hex)
    except ValueError:
        await interaction.response.send_message("Format color salah. Contoh: `#ff0000`.", ephemeral=True)
        return
    try:
        role = await interaction.guild.create_role(
            name=name,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
            reason=f"Role created by {interaction.user}",
        )
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal create role: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("✅ Role Created", f"{role.mention}"), ephemeral=True)


@tree.command(name="role_delete", description="Hapus role")
async def role_delete(interaction: discord.Interaction, role: discord.Role) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_roles"):
        await interaction.response.send_message("Butuh permission `Manage Roles`.", ephemeral=True)
        return
    if role == interaction.guild.default_role:
        await interaction.response.send_message("Role @everyone tidak bisa dihapus.", ephemeral=True)
        return
    if not can_bot_manage_role(interaction.guild, role):
        await interaction.response.send_message("Bot tidak bisa hapus role itu. Naikkan posisi role bot.", ephemeral=True)
        return
    view = ConfirmView(interaction.user.id if interaction.user else 0)
    await interaction.response.send_message(
        embed=build_embed("Confirm Role Delete", f"Hapus role `{role.name}`?"),
        view=view,
        ephemeral=True,
    )
    await view.wait()
    if view.value is not True:
        return
    role_name = role.name
    try:
        await role.delete(reason=f"Role deleted by {interaction.user}")
    except discord.Forbidden:
        await interaction.edit_original_response(embed=build_embed("Delete Failed", "Bot tidak punya izin `Manage Roles`."), view=None)
        return
    except Exception as exc:
        await interaction.edit_original_response(embed=build_embed("Delete Failed", f"{exc}"), view=None)
        return
    await interaction.edit_original_response(embed=build_embed("✅ Role Deleted", f"`{role_name}`"), view=None)


@tree.command(name="channel_create", description="Buat channel baru")
@app_commands.describe(kind="Jenis channel")
@app_commands.choices(
    kind=[
        app_commands.Choice(name="text", value="text"),
        app_commands.Choice(name="voice", value="voice"),
    ]
)
async def channel_create(
    interaction: discord.Interaction,
    name: str,
    kind: app_commands.Choice[str],
    category: Optional[discord.CategoryChannel] = None,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_channels"):
        await interaction.response.send_message("Butuh permission `Manage Channels`.", ephemeral=True)
        return
    try:
        if kind.value == "voice":
            ch = await interaction.guild.create_voice_channel(name=name, category=category, reason=f"Channel created by {interaction.user}")
        else:
            ch = await interaction.guild.create_text_channel(name=name, category=category, reason=f"Channel created by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Channels`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal create channel: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("✅ Channel Created", f"{getattr(ch, 'mention', ch.name)}"), ephemeral=True)


@tree.command(name="channel_delete", description="Hapus channel")
async def channel_delete(interaction: discord.Interaction, channel: discord.abc.GuildChannel) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_channels"):
        await interaction.response.send_message("Butuh permission `Manage Channels`.", ephemeral=True)
        return
    view = ConfirmView(interaction.user.id if interaction.user else 0)
    await interaction.response.send_message(
        embed=build_embed("Confirm Channel Delete", f"Hapus channel `{channel.name}`?"),
        view=view,
        ephemeral=True,
    )
    await view.wait()
    if view.value is not True:
        return
    name = channel.name
    try:
        await channel.delete(reason=f"Channel deleted by {interaction.user}")
    except discord.Forbidden:
        await interaction.edit_original_response(embed=build_embed("Delete Failed", "Bot tidak punya izin `Manage Channels`."), view=None)
        return
    except Exception as exc:
        await interaction.edit_original_response(embed=build_embed("Delete Failed", f"{exc}"), view=None)
        return
    await interaction.edit_original_response(embed=build_embed("✅ Channel Deleted", f"`{name}`"), view=None)


@tree.command(name="channel_rename", description="Rename channel")
async def channel_rename(interaction: discord.Interaction, channel: discord.abc.GuildChannel, new_name: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_channels"):
        await interaction.response.send_message("Butuh permission `Manage Channels`.", ephemeral=True)
        return
    try:
        await channel.edit(name=new_name, reason=f"Channel rename by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Channels`.", ephemeral=True)
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal rename: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("✅ Renamed", f"`{new_name}`"), ephemeral=True)


@tree.command(name="setnick", description="Set nickname member")
async def setnick(interaction: discord.Interaction, member: discord.Member, nickname: Optional[str] = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not has_perm(interaction, "manage_nicknames"):
        await interaction.response.send_message("Butuh permission `Manage Nicknames`.", ephemeral=True)
        return
    me = interaction.guild.me or interaction.guild.get_member(client.user.id if client.user else 0)
    if me is None:
        await interaction.response.send_message("Gagal membaca role/perms bot di server ini.", ephemeral=True)
        return

    if member.id == me.id:
        if not (me.guild_permissions.change_nickname or me.guild_permissions.administrator):
            await interaction.response.send_message(
                "Bot butuh permission `Change Nickname` untuk ganti nickname sendiri.",
                ephemeral=True,
            )
            return
    else:
        if not (me.guild_permissions.manage_nicknames or me.guild_permissions.administrator):
            await interaction.response.send_message(
                "Bot tidak punya permission `Manage Nicknames` di server ini.\n"
                "Catatan: checklist permission saat invite/OAuth2 tidak selalu mengubah role bot yang sudah ada — "
                "pastikan di Server Settings → Roles (role bot) juga dicentang.",
                ephemeral=True,
            )
            return
        if interaction.guild.owner_id == member.id:
            await interaction.response.send_message("Tidak bisa mengubah nickname **owner server**.", ephemeral=True)
            return
        if me.top_role <= member.top_role:
            await interaction.response.send_message(
                "Gagal karena **role hierarchy**: posisi role bot harus di atas role target.",
                ephemeral=True,
            )
            return
    try:
        await member.edit(nick=nickname, reason=f"Nick change by {interaction.user}")
    except discord.Forbidden:
        await interaction.response.send_message(
            "Discord menolak aksi ini (Forbidden).\n"
            "Cek: permission bot (`Manage Nicknames`) + role bot harus di atas target (dan target bukan owner).",
            ephemeral=True,
        )
        return
    except Exception as exc:
        await interaction.response.send_message(f"Gagal set nick: {exc}", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_embed("✅ Nick Updated", f"{member.mention}"), ephemeral=True)


@client.event
async def on_ready() -> None:
    try:
        await tree.sync()
    except Exception as exc:
        print(f"[drxsrvrmanage] Gagal sync command: {exc}")
    print(f"[drxsrvrmanage] Logged in as {client.user}")
    try:
        await client.change_presence(
            status=discord.Status.dnd,
            activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs"),
        )
    except Exception:
        pass


def main() -> int:
    if not TOKEN:
        print("[drxsrvrmanage] Missing token. Set DISCORD_SRVRMANAGE_TOKEN or DISCORD_BOT_TOKEN in .env")
        return 2
    try:
        client.run(TOKEN)
        return 0
    except Exception as exc:
        msg = str(exc)
        print(f"[drxsrvrmanage] Fatal error: {exc}")
        if "Cannot connect to host discord.com:443" in msg or "Access is denied" in msg or "WinError 5" in msg:
            print(
                "[drxsrvrmanage] Hint: koneksi ke Discord terblokir (firewall/antivirus/proxy/VPN atau network restricted)."
            )
        elif "Improper token" in msg or "401" in msg:
            print("[drxsrvrmanage] Hint: token salah/invalid. Cek DISCORD_SRVRMANAGE_TOKEN di .env")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
