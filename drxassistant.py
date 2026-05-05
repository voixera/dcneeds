import os
import re
import json
from datetime import datetime
from io import BytesIO
import discord
from discord import app_commands
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
WHITELIST_FILE = "whitelist.json"
WELCOME_BANNER_URL = os.getenv(
    "WELCOME_BANNER_URL",
    "https://images.unsplash.com/photo-1511497584788-876760111969?auto=format&fit=crop&w=1200&q=80"
)

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
_panel_view = None


def build_products_embed() -> discord.Embed:
    embed = discord.Embed(
        title="DrxDvs Access Plans",
        description=(
            "Pilih paket akses sesuai kebutuhan Anda. "
            "Semua paket memberikan fitur inti yang sama, berbeda di durasi akses."
        ),
        color=0x0099FF
    )
    embed.add_field(
        name="Weekly",
        value=(
            "Cocok untuk percobaan singkat.\n"
            "- Akses penuh fitur\n"
            "- Aktivasi cepat\n"
            "- Durasi 7 hari"
        ),
        inline=False
    )
    embed.add_field(
        name="Monthly",
        value=(
            "Pilihan paling seimbang untuk penggunaan rutin.\n"
            "- Akses penuh fitur\n"
            "- Durasi 30 hari\n"
            "- Value terbaik untuk user aktif"
        ),
        inline=False
    )
    embed.add_field(
        name="Lifetime",
        value=(
            "Akses permanen untuk penggunaan jangka panjang.\n"
            "- Sekali bayar\n"
            "- Tanpa perpanjangan\n"
            "- Investasi terbaik jangka panjang"
        ),
        inline=False
    )
    embed.add_field(
        name="Included in Every Plan",
        value=(
            "- Full feature access\n"
            "- Priority updates\n"
            "- Fast support response"
        ),
        inline=False
    )
    embed.add_field(
        name="Quick Recommendation",
        value=(
            "- Pilih **Weekly** untuk trial\n"
            "- Pilih **Monthly** untuk kebutuhan rutin\n"
            "- Pilih **Lifetime** untuk value maksimal"
        ),
        inline=False
    )
    embed.set_footer(text="DrxDvs Assistant | Professional Product Overview")
    return embed


def build_pricing_embed(ticket_channel: discord.TextChannel | None = None) -> discord.Embed:
    purchase_text = "Open a ticket and we will assist you."
    if ticket_channel is not None:
        purchase_text = f"open a ticket in {ticket_channel.mention} and we will assist you."

    embed = discord.Embed(
        title="DrxDvs Pricelist",
        description="Below are the available access plans. All are one-time payments unless noted.",
        color=0x00AA66
    )
    embed.add_field(name="Weekly", value="IDR: Rp20,000", inline=False)
    embed.add_field(name="Monthly", value="IDR: Rp45,000", inline=False)
    embed.add_field(name="Lifetime", value="IDR: Rp100,000", inline=False)
    embed.add_field(name="Payment Methods", value="QRIS With name **DRAX STORE** only", inline=False)
    embed.add_field(name="How to Purchase", value=purchase_text, inline=False)
    return embed


def build_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="DrxDvs Assistant Panel",
        description="Gunakan tombol di bawah untuk mengirim pesan penting ke channel target.",
        color=0x5865F2
    )
    embed.add_field(
        name="Actions",
        value="- Developer Logs Message\n- TOS Message\n- Developer Message (Custom)",
        inline=False
    )
    embed.add_field(
        name="Channel Target",
        value=(
            "- Developer logs: #developer-logs / #dev-logs / #logs / #update-logs\n"
            "- TOS: #tos / #terms / #rules\n"
            "- Developer Message: isi channel tujuan dari modal (#mention / ID / nama)\n"
            "Jika tidak ada, bot akan kirim ke channel tempat panel diklik."
        ),
        inline=False
    )
    return embed


def build_peraturan_embed(guild_name: str) -> discord.Embed:
    embed = discord.Embed(
        title="Peraturan Server",
        description=f"Harap baca dan patuhi peraturan di **{guild_name}**.",
        color=0xF1C40F
    )
    embed.add_field(
        name="Aturan Utama",
        value=(
            "1. Dilarang spam, flood, atau mengganggu member lain.\n"
            "2. Dilarang toxic, SARA, pornografi, dan konten ilegal.\n"
            "3. Dilarang promosi tanpa izin staff/admin.\n"
            "4. Hormati keputusan staff dan ikuti arahan moderator.\n"
            "5. Gunakan channel sesuai topik."
        ),
        inline=False
    )
    embed.add_field(
        name="Sanksi",
        value="Pelanggaran aturan dapat berujung mute, kick, atau ban sesuai kebijakan staff.",
        inline=False
    )
    embed.set_footer(text="DrxDvs Assistant | Server Rules")
    return embed


def build_developer_logs_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Atomicals Script Update Logs",
        description="@Free Users",
        color=0x2B2D31
    )
    embed.add_field(
        name="Release Info",
        value=(
            "- Place: MALS X ATOMIC\n"
            "- Version: v.3.1.7\n"
            "- Developer Notes:\n"
            "  Found any bugs or issues? Feel free to report them to the developers.\n"
            "  Got ideas or suggestions for new scripts? We'd love to hear them!"
        ),
        inline=False
    )
    embed.add_field(
        name="Added",
        value=(
            "[+] New Mode: TRAP - Logic filter kata akhiran sulit agar akur.\n"
            "[+] Dual Dictionary Support - Pilih database GEOVEDI (KBBI Inggris) atau MALS HUB.\n"
            "[+] Auto Join (Walk Mode) - Mode jalan otomatis agar lebih natural.\n"
            "[+] Anti-Nganggur System - Jika meja kosong >15 detik, pindah meja otomatis."
        ),
        inline=False
    )
    embed.add_field(
        name="Deleted",
        value="[-] Hide ID removed karena memicu UI error, glitch teks, dan performa tidak stabil.",
        inline=False
    )
    embed.add_field(
        name="Improved",
        value=(
            "[/] Improved Killer Mode - Filter kata akhiran sulit (X, Z, Q, F, V, W, P) lebih akurat.\n"
            "[/] Enhanced UI - Tambahan INDEX dan statistik sisa kata real-time."
        ),
        inline=False
    )
    embed.set_footer(text="DrxDvs Assistant | Developer Logs")
    return embed


def build_tos_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Terms of Service (TOS)",
        description="Dengan menggunakan layanan ini, Anda setuju dengan ketentuan berikut:",
        color=0xE74C3C
    )
    embed.add_field(
        name="Ketentuan Utama",
        value=(
            "1. Dilarang menyalahgunakan layanan untuk aktivitas ilegal.\n"
            "2. Dilarang share akses/key tanpa izin.\n"
            "3. Pelanggaran dapat berujung suspend/ban tanpa refund."
        ),
        inline=False
    )
    embed.add_field(
        name="Catatan",
        value="Ketentuan dapat berubah sewaktu-waktu sesuai kebijakan developer.",
        inline=False
    )
    embed.set_footer(text="DrxDvs Assistant | TOS")
    return embed


def normalize_channel_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def load_whitelist() -> list[dict]:
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
    for row in load_whitelist():
        if str(row.get("user_id")) != str(user_id):
            continue
        expires_at = parse_iso_datetime(row.get("access_expires_at"))
        if expires_at is None:
            return True
        return now < expires_at
    return False


def find_channel_by_aliases(guild: discord.Guild, aliases: list[str]) -> discord.TextChannel | None:
    normalized_aliases = {normalize_channel_name(alias) for alias in aliases}
    for channel in guild.text_channels:
        if normalize_channel_name(channel.name) in normalized_aliases:
            return channel
    return None


def find_role_by_aliases(guild: discord.Guild, aliases: list[str]) -> discord.Role | None:
    normalized_aliases = {normalize_channel_name(alias) for alias in aliases}
    for role in guild.roles:
        if normalize_channel_name(role.name) in normalized_aliases:
            return role
    return None


def build_ticket_button_view(ticket_channel: discord.TextChannel | None) -> discord.ui.View | None:
    if ticket_channel is None:
        return None
    channel_url = f"https://discord.com/channels/{ticket_channel.guild.id}/{ticket_channel.id}"
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Open Ticket", style=discord.ButtonStyle.link, url=channel_url))
    return view


def build_welcome_embed(member: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="Thanks For Joining!!!",
        description=f"**{member.name}**\n{member.display_name}",
        color=0x00B0F4
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_image(url=WELCOME_BANNER_URL)
    embed.set_footer(text="DrxDvs Assistant | Welcome System")
    return embed


async def create_premium_welcome_card(member: discord.Member) -> bytes | None:
    if not PIL_AVAILABLE:
        return None

    width, height = 1200, 420
    img = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(height):
        r = 8 + int((28 - 8) * (y / height))
        g = 13 + int((35 - 13) * (y / height))
        b = 30 + int((63 - 30) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Accent glow shapes
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse((-150, -130, 520, 420), fill=(14, 165, 233, 80))
    gdraw.ellipse((700, 10, 1320, 620), fill=(59, 130, 246, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(55))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Main glass panel
    panel = (40, 40, width - 40, height - 40)
    draw.rounded_rectangle(panel, radius=26, fill=(9, 15, 35), outline=(14, 165, 233), width=3)

    # Avatar
    avatar_bytes = await member.display_avatar.with_size(256).read()
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((170, 170))
    mask = Image.new("L", (170, 170), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 169, 169), fill=255)
    avatar.putalpha(mask)
    avatar_x, avatar_y = 900, 110
    img.paste(avatar, (avatar_x, avatar_y), avatar)
    draw.ellipse(
        (avatar_x - 6, avatar_y - 6, avatar_x + 176, avatar_y + 176),
        outline=(56, 189, 248),
        width=4
    )

    def get_font(size: int) -> ImageFont.ImageFont:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            try:
                return ImageFont.truetype("DejaVuSans.ttf", size)
            except Exception:
                return ImageFont.load_default()

    title_font = get_font(56)
    body_font = get_font(32)
    small_font = get_font(24)

    draw.text((90, 95), "Thanks For Joining!!!", font=title_font, fill=(255, 255, 255))
    draw.text((92, 175), member.name, font=body_font, fill=(186, 230, 253))
    draw.text((92, 220), member.display_name, font=body_font, fill=(125, 211, 252))
    draw.text(
        (92, 310),
        f"Welcome to {member.guild.name} | Member #{member.guild.member_count}",
        font=small_font,
        fill=(148, 163, 184)
    )

    out = BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return out.read()


def find_panel_target_channel(
    guild: discord.Guild,
    action: str,
    fallback_channel: discord.abc.Messageable
) -> discord.abc.Messageable:
    if action == "developer_logs":
        target = find_channel_by_aliases(
            guild,
            ["developer-logs", "dev-logs", "logs", "update-logs", "changelog"]
        )
        return target or fallback_channel

    if action == "tos":
        target = find_channel_by_aliases(guild, ["tos", "terms", "rules", "termsofservice"])
        return target or fallback_channel

    return fallback_channel


def is_panel_authorized(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    return interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id


def resolve_text_channel_from_input(guild: discord.Guild, raw_target: str) -> discord.TextChannel | None:
    value = raw_target.strip()
    if not value:
        return None

    mention_match = re.fullmatch(r"<#(\d+)>", value)
    if mention_match:
        ch = guild.get_channel(int(mention_match.group(1)))
        return ch if isinstance(ch, discord.TextChannel) else None

    if value.isdigit():
        ch = guild.get_channel(int(value))
        return ch if isinstance(ch, discord.TextChannel) else None

    normalized = normalize_channel_name(value.replace("#", ""))
    for ch in guild.text_channels:
        if normalize_channel_name(ch.name) == normalized:
            return ch
    return None


def _format_section(text: str) -> str:
    raw = text.strip()
    if not raw:
        return "-"
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return "-"
    formatted = []
    for line in lines:
        if line.startswith(("-", "•", "[", "1.", "2.", "3.", "4.", "5.")):
            formatted.append(line)
        else:
            formatted.append(f"- {line}")
    return "\n".join(formatted)


class DeveloperLogsModal(discord.ui.Modal, title="Developer Logs Message"):
    description_input = discord.ui.TextInput(
        label="Description",
        placeholder="Contoh: @Free Users",
        required=False,
        max_length=200,
        default=""
    )
    release_info_input = discord.ui.TextInput(
        label="Release Info",
        placeholder="Place, Version, Developer Notes...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        default=""
    )
    added_input = discord.ui.TextInput(
        label="Added",
        placeholder="Tuliskan fitur yang ditambahkan...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        default=""
    )
    deleted_input = discord.ui.TextInput(
        label="Deleted",
        placeholder="Tuliskan fitur/perubahan yang dihapus...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        default=""
    )

    improved_input = discord.ui.TextInput(
        label="Improved",
        placeholder="Tuliskan peningkatan/perbaikan...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        default=""
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Channel tidak valid.", ephemeral=True)
            return

        target_channel = find_panel_target_channel(interaction.guild, "developer_logs", interaction.channel)
        me = interaction.guild.me
        if isinstance(target_channel, discord.TextChannel) and me is not None:
            perms = target_channel.permissions_for(me)
            if not (perms.send_messages and perms.embed_links):
                await interaction.response.send_message(
                    f"Bot tidak punya izin `Send Messages`/`Embed Links` di {target_channel.mention}.",
                    ephemeral=True
                )
                return

        embed = discord.Embed(
            title="DrxDvs Update Logs",
            description=self.description_input.value.strip(),
            color=0x2B2D31
        )
        embed.add_field(name="Release Info", value=_format_section(self.release_info_input.value), inline=False)
        embed.add_field(name="Added", value=_format_section(self.added_input.value), inline=False)
        embed.add_field(name="Deleted", value=_format_section(self.deleted_input.value), inline=False)
        embed.add_field(name="Improved", value=_format_section(self.improved_input.value), inline=False)
        embed.set_footer(text="DrxDvs Assistant | Developer Logs")

        try:
            await target_channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Bot tidak punya izin kirim pesan di channel target.",
                ephemeral=True
            )
            return
        except Exception as exc:
            await interaction.response.send_message(
                f"Gagal mengirim Developer Logs: {exc}",
                ephemeral=True
            )
            return

        if isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                f"Developer Logs message berhasil dikirim ke {target_channel.mention}.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Developer Logs message berhasil dikirim.", ephemeral=True)


class TOSModal(discord.ui.Modal, title="TOS Message"):
    title_input = discord.ui.TextInput(
        label="Title",
        placeholder="Contoh: Terms of Service (TOS)",
        required=True,
        max_length=100,
        default=""
    )
    description_input = discord.ui.TextInput(
        label="Description",
        placeholder="Tulis deskripsi TOS di sini...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        default=""
    )
    rules_input = discord.ui.TextInput(
        label="Rules",
        placeholder="1. ...\n2. ...\n3. ...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        default=""
    )
    notes_input = discord.ui.TextInput(
        label="Notes",
        placeholder="Catatan tambahan...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
        default=""
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Channel tidak valid.", ephemeral=True)
            return

        target_channel = find_panel_target_channel(interaction.guild, "tos", interaction.channel)
        me = interaction.guild.me
        if isinstance(target_channel, discord.TextChannel) and me is not None:
            perms = target_channel.permissions_for(me)
            if not (perms.send_messages and perms.embed_links):
                await interaction.response.send_message(
                    f"Bot tidak punya izin `Send Messages`/`Embed Links` di {target_channel.mention}.",
                    ephemeral=True
                )
                return

        embed = discord.Embed(
            title=self.title_input.value.strip() or "Terms of Service (TOS)",
            description=self.description_input.value.strip(),
            color=0xE74C3C
        )

        if self.rules_input.value.strip():
            embed.add_field(name="Rules", value=self.rules_input.value.strip(), inline=False)
        if self.notes_input.value.strip():
            embed.add_field(name="Notes", value=self.notes_input.value.strip(), inline=False)
        if not embed.fields and not embed.description:
            embed.add_field(name="Message", value="(Kosong) Silakan isi konten TOS.", inline=False)

        try:
            await target_channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Bot tidak punya izin kirim pesan di channel target.",
                ephemeral=True
            )
            return
        except Exception as exc:
            await interaction.response.send_message(
                f"Gagal mengirim TOS message: {exc}",
                ephemeral=True
            )
            return

        if isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                f"TOS message berhasil dikirim ke {target_channel.mention}.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("TOS message berhasil dikirim.", ephemeral=True)


class DeveloperBroadcastModal(discord.ui.Modal, title="Developer Message"):
    message_input = discord.ui.TextInput(
        label="Pesan",
        placeholder="Tulis pesan dari developer...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1800
    )
    target_channel_input = discord.ui.TextInput(
        label="Tujuan Channel",
        placeholder="Contoh: #announcements atau 123456789012345678 atau nama-channel",
        style=discord.TextStyle.short,
        required=True,
        max_length=120
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
            return

        target_channel = resolve_text_channel_from_input(
            interaction.guild, self.target_channel_input.value
        )
        if target_channel is None:
            await interaction.response.send_message(
                "Channel tujuan tidak ditemukan. Pakai format #mention, ID channel, atau nama channel.",
                ephemeral=True
            )
            return

        me = interaction.guild.me
        if me is not None:
            perms = target_channel.permissions_for(me)
            if not perms.send_messages:
                await interaction.response.send_message(
                    f"Bot tidak punya izin `Send Messages` di {target_channel.mention}.",
                    ephemeral=True
                )
                return

        embed = discord.Embed(
            title="Developer Message",
            description=self.message_input.value.strip(),
            color=0x5865F2,
            timestamp=datetime.now()
        )
        if isinstance(interaction.user, discord.Member):
            embed.set_footer(text=f"Dikirim oleh {interaction.user.display_name}")
        else:
            embed.set_footer(text=f"Dikirim oleh {interaction.user}")

        try:
            await target_channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Bot tidak punya izin kirim pesan di channel target.",
                ephemeral=True
            )
            return
        except Exception as exc:
            await interaction.response.send_message(
                f"Gagal mengirim pesan developer: {exc}",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Developer message berhasil dikirim ke {target_channel.mention}.",
            ephemeral=True
        )


class AssistantPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Developer Logs Message",
        style=discord.ButtonStyle.secondary,
        custom_id="assistant_panel_developer_logs"
    )
    async def developer_logs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_panel_authorized(interaction):
            await interaction.response.send_message("Hanya owner/admin yang bisa menggunakan panel ini.", ephemeral=True)
            return
        await interaction.response.send_modal(DeveloperLogsModal())

    @discord.ui.button(
        label="TOS Message",
        style=discord.ButtonStyle.danger,
        custom_id="assistant_panel_tos_message"
    )
    async def tos_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_panel_authorized(interaction):
            await interaction.response.send_message("Hanya owner/admin yang bisa menggunakan panel ini.", ephemeral=True)
            return
        await interaction.response.send_modal(TOSModal())

    @discord.ui.button(
        label="Developer Message",
        style=discord.ButtonStyle.primary,
        custom_id="assistant_panel_developer_message"
    )
    async def developer_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_panel_authorized(interaction):
            await interaction.response.send_message("Hanya owner/admin yang bisa menggunakan panel ini.", ephemeral=True)
            return
        await interaction.response.send_modal(DeveloperBroadcastModal())


@tree.command(name="products", description="Tampilkan embed jenis product")
async def products(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_products_embed())


@tree.command(name="pricing", description="Tampilkan embed harga product")
async def pricing(interaction: discord.Interaction):
    ticket_channel = None
    if interaction.guild is not None:
        ticket_channel = find_channel_by_aliases(interaction.guild, ["ticket", "tickets", "tiket"])
    await interaction.response.send_message(
        embed=build_pricing_embed(ticket_channel),
        view=build_ticket_button_view(ticket_channel)
    )


@tree.command(name="setup_products_pricing", description="Kirim embed ke #products dan #pricing")
async def setup_products_pricing(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
        return

    products_channel = find_channel_by_aliases(interaction.guild, ["products", "product", "produk"])
    pricing_channel = find_channel_by_aliases(interaction.guild, ["pricing", "price", "harga"])
    ticket_channel = find_channel_by_aliases(interaction.guild, ["ticket", "tickets", "tiket"])

    if products_channel is None or pricing_channel is None:
        missing = []
        if products_channel is None:
            missing.append("#products")
        if pricing_channel is None:
            missing.append("#pricing")
        await interaction.response.send_message(
            f"Channel tidak ditemukan: {', '.join(missing)}. "
            "Pastikan channel mengandung kata products/product atau pricing/price.",
            ephemeral=True
        )
        return

    await products_channel.send(embed=build_products_embed())
    await pricing_channel.send(
        embed=build_pricing_embed(ticket_channel),
        view=build_ticket_button_view(ticket_channel)
    )
    await interaction.response.send_message("Embed berhasil dikirim ke #products dan #pricing.", ephemeral=True)


@tree.command(name="panel", description="Kirim panel tombol Developer Logs dan TOS")
async def panel(interaction: discord.Interaction):
    global _panel_view
    if _panel_view is None:
        _panel_view = AssistantPanelView()
        client.add_view(_panel_view)
    await interaction.response.send_message(embed=build_panel_embed(), view=_panel_view)


@tree.command(name="peraturan_server", description="Kirim embed peraturan ke channel peraturan server")
async def peraturan_server(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Command ini hanya bisa dipakai di server.", ephemeral=True)
        return
    if not is_panel_authorized(interaction):
        await interaction.response.send_message("Hanya owner/admin yang bisa menggunakan command ini.", ephemeral=True)
        return

    rules_channel = find_channel_by_aliases(
        interaction.guild,
        ["peraturan-server", "peraturan", "rules", "rule", "server-rules", "aturan"]
    )
    if rules_channel is None:
        await interaction.response.send_message(
            "Channel peraturan tidak ditemukan. Buat channel `peraturan-server` atau `rules`.",
            ephemeral=True
        )
        return

    target_channel = rules_channel
    embed = build_peraturan_embed(interaction.guild.name)
    me = interaction.guild.me
    if isinstance(target_channel, discord.TextChannel) and me is not None:
        perms = target_channel.permissions_for(me)
        if not (perms.send_messages and perms.embed_links):
            await interaction.response.send_message(
                f"Bot tidak punya izin `Send Messages`/`Embed Links` di {target_channel.mention}.",
                ephemeral=True
            )
            return

    try:
        await target_channel.send(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            "Bot tidak punya izin kirim pesan di channel target.",
            ephemeral=True
        )
        return
    except Exception as exc:
        await interaction.response.send_message(
            f"Gagal mengirim embed peraturan: {exc}",
            ephemeral=True
        )
        return

    if isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message(
            f"Embed peraturan berhasil dikirim ke {target_channel.mention}.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("Embed peraturan berhasil dikirim.", ephemeral=True)

@client.event
async def on_member_join(member: discord.Member):
    welcome_channel = find_channel_by_aliases(
        member.guild,
        ["welcome", "welcoming", "selamat-datang", "selamatdatang"]
    )
    if welcome_channel is None:
        return
    customer_role = find_role_by_aliases(member.guild, ["customer", "cust", "buyer"])
    premium_role = find_role_by_aliases(member.guild, ["premium user", "premium", "vip", "premiumuser"])
    bot_member = member.guild.me
    can_manage_roles = bot_member is not None and bot_member.guild_permissions.manage_roles

    if can_manage_roles:
        target_is_premium = is_user_whitelisted_active(member.id)
        to_add = []
        to_remove = []

        if target_is_premium:
            if premium_role and premium_role not in member.roles and bot_member.top_role > premium_role:
                to_add.append(premium_role)
            if customer_role and customer_role in member.roles and bot_member.top_role > customer_role:
                to_remove.append(customer_role)
        else:
            if customer_role and customer_role not in member.roles and bot_member.top_role > customer_role:
                to_add.append(customer_role)
            if premium_role and premium_role in member.roles and bot_member.top_role > premium_role:
                to_remove.append(premium_role)

        try:
            if to_add:
                await member.add_roles(*to_add, reason="Auto role assignment by join/whitelist status")
            if to_remove:
                await member.remove_roles(*to_remove, reason="Auto role assignment by join/whitelist status")
        except Exception as exc:
            print(f"Gagal auto-manage role member baru: {exc}")

    try:
        card_bytes = await create_premium_welcome_card(member)
        if card_bytes is not None:
            file = discord.File(BytesIO(card_bytes), filename="welcome-premium.png")
            embed = discord.Embed(color=0x00B0F4)
            embed.set_image(url="attachment://welcome-premium.png")
            await welcome_channel.send(
                content=f"Welcome {member.mention} to {member.guild.name}!",
                embed=embed,
                file=file
            )
        else:
            await welcome_channel.send(
                content=f"Welcome {member.mention} to {member.guild.name}!",
                embed=build_welcome_embed(member)
            )
    except discord.Forbidden:
        pass
    except Exception as exc:
        print(f"Gagal kirim welcome message: {exc}")


@client.event
async def on_ready():
    global _panel_view
    print(f"Bot online sebagai {client.user}")
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs-1")
    )
    if _panel_view is None:
        _panel_view = AssistantPanelView()
        client.add_view(_panel_view)
    try:
        await tree.sync()
        print("Slash command berhasil di-sync.")
    except Exception as exc:
        print(f"Gagal sync command: {exc}")


if __name__ == "__main__":
    if TOKEN == "ISI_TOKEN_BOT_KAMU_DI_SINI":
        print("Isi token bot dulu di variabel TOKEN atau env DISCORD_BOT_TOKEN.")
    else:
        client.run(TOKEN)
