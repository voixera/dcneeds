import os
import discord
from discord import app_commands


TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()

intents = discord.Intents.default()

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    return interaction.user.guild_permissions.administrator


def can_manage_target(invoker: discord.Member, target: discord.Member) -> bool:
    if invoker.guild.owner_id == invoker.id:
        return True
    return invoker.top_role > target.top_role


def can_bot_manage_role(guild: discord.Guild, role: discord.Role) -> bool:
    me = guild.me
    if me is None:
        return False
    return me.top_role > role


def role_list_text(member: discord.Member) -> str:
    roles = [role.mention for role in member.roles if role != member.guild.default_role]
    if not roles:
        return "Tidak ada role selain @everyone."
    return ", ".join(roles)


@tree.command(name="role_add", description="Tambahkan role ke member")
async def role_add(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not is_admin(interaction):
        await interaction.response.send_message("Hanya admin yang bisa memakai command ini.", ephemeral=True)
        return
    if not can_manage_target(interaction.user, member):
        await interaction.response.send_message("Kamu tidak bisa mengatur role user ini (hierarchy role).", ephemeral=True)
        return
    if not can_bot_manage_role(interaction.guild, role):
        await interaction.response.send_message("Bot tidak bisa mengatur role itu. Naikkan posisi role bot.", ephemeral=True)
        return

    try:
        await member.add_roles(role, reason=f"Role added by {interaction.user}")
        await interaction.response.send_message(f"Role {role.mention} ditambahkan ke {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal menambah role: {exc}", ephemeral=True)


@tree.command(name="role_remove", description="Hapus role dari member")
async def role_remove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not is_admin(interaction):
        await interaction.response.send_message("Hanya admin yang bisa memakai command ini.", ephemeral=True)
        return
    if not can_manage_target(interaction.user, member):
        await interaction.response.send_message("Kamu tidak bisa mengatur role user ini (hierarchy role).", ephemeral=True)
        return
    if not can_bot_manage_role(interaction.guild, role):
        await interaction.response.send_message("Bot tidak bisa mengatur role itu. Naikkan posisi role bot.", ephemeral=True)
        return

    try:
        await member.remove_roles(role, reason=f"Role removed by {interaction.user}")
        await interaction.response.send_message(f"Role {role.mention} dihapus dari {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal menghapus role: {exc}", ephemeral=True)


@tree.command(name="role_set", description="Set role member (hapus role lama, sisakan @everyone + role baru)")
async def role_set(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not is_admin(interaction):
        await interaction.response.send_message("Hanya admin yang bisa memakai command ini.", ephemeral=True)
        return
    if not can_manage_target(interaction.user, member):
        await interaction.response.send_message("Kamu tidak bisa mengatur role user ini (hierarchy role).", ephemeral=True)
        return
    if not can_bot_manage_role(interaction.guild, role):
        await interaction.response.send_message("Bot tidak bisa mengatur role itu. Naikkan posisi role bot.", ephemeral=True)
        return

    try:
        new_roles = [interaction.guild.default_role, role]
        await member.edit(roles=new_roles, reason=f"Roles set by {interaction.user}")
        await interaction.response.send_message(f"Role {member.mention} diset menjadi {role.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal set role: {exc}", ephemeral=True)


@tree.command(name="role_clear", description="Hapus semua role member (kecuali @everyone)")
async def role_clear(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not is_admin(interaction):
        await interaction.response.send_message("Hanya admin yang bisa memakai command ini.", ephemeral=True)
        return
    if not can_manage_target(interaction.user, member):
        await interaction.response.send_message("Kamu tidak bisa mengatur role user ini (hierarchy role).", ephemeral=True)
        return

    try:
        await member.edit(roles=[interaction.guild.default_role], reason=f"Roles cleared by {interaction.user}")
        await interaction.response.send_message(f"Semua role {member.mention} berhasil dihapus.")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal clear role: {exc}", ephemeral=True)


@tree.command(name="role_create", description="Buat role baru")
@app_commands.describe(name="Nama role", color_hex="Contoh: #ff0000")
async def role_create(
    interaction: discord.Interaction,
    name: str,
    color_hex: str = "#5865F2",
    hoist: bool = False,
    mentionable: bool = False
):
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not is_admin(interaction):
        await interaction.response.send_message("Hanya admin yang bisa memakai command ini.", ephemeral=True)
        return

    try:
        color = discord.Color.from_str(color_hex)
    except ValueError:
        await interaction.response.send_message("Format color salah. Contoh benar: `#ff0000`.", ephemeral=True)
        return

    try:
        role = await interaction.guild.create_role(
            name=name,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
            reason=f"Role created by {interaction.user}"
        )
        await interaction.response.send_message(f"Role baru berhasil dibuat: {role.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal membuat role: {exc}", ephemeral=True)


@tree.command(name="role_delete", description="Hapus role")
async def role_delete(interaction: discord.Interaction, role: discord.Role):
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return
    if not is_admin(interaction):
        await interaction.response.send_message("Hanya admin yang bisa memakai command ini.", ephemeral=True)
        return
    if role == interaction.guild.default_role:
        await interaction.response.send_message("Role @everyone tidak bisa dihapus.", ephemeral=True)
        return
    if not can_bot_manage_role(interaction.guild, role):
        await interaction.response.send_message("Bot tidak bisa menghapus role itu. Naikkan posisi role bot.", ephemeral=True)
        return

    role_name = role.name
    try:
        await role.delete(reason=f"Role deleted by {interaction.user}")
        await interaction.response.send_message(f"Role `{role_name}` berhasil dihapus.")
    except discord.Forbidden:
        await interaction.response.send_message("Bot tidak punya izin `Manage Roles`.", ephemeral=True)
    except Exception as exc:
        await interaction.response.send_message(f"Gagal menghapus role: {exc}", ephemeral=True)


@tree.command(name="role_list", description="Lihat daftar role milik member")
async def role_list(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya untuk server.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Role Member",
        description=f"Daftar role untuk {member.mention}",
        color=0x3498DB
    )
    embed.add_field(name="Roles", value=role_list_text(member), inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="role_manage_help", description="Panduan command role manager")
async def role_manage_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Role Manager Commands",
        color=0x5865F2
    )
    embed.add_field(
        name="Admin Commands",
        value=(
            "`/role_add member role`\n"
            "`/role_remove member role`\n"
            "`/role_set member role`\n"
            "`/role_clear member`\n"
            "`/role_create name color_hex hoist mentionable`\n"
            "`/role_delete role`"
        ),
        inline=False
    )
    embed.add_field(name="Public Command", value="`/role_list member`", inline=False)
    embed.add_field(
        name="Requirements",
        value="Bot butuh permission `Manage Roles` dan posisi role bot harus di atas role target.",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.event
async def on_ready():
    print(f"Role manager online sebagai {client.user}")
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs")
    )
    try:
        await tree.sync()
        print("Slash command role manager berhasil di-sync.")
    except Exception as exc:
        print(f"Gagal sync command: {exc}")


if __name__ == "__main__":
    if TOKEN == "ISI_TOKEN_BOT_KAMU_DI_SINI":
        print("Isi token bot dulu di variabel TOKEN atau env DISCORD_BOT_TOKEN.")
    else:
        client.run(TOKEN)
