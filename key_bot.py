import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
import random
import string

BOT_TOKEN = os.getenv("KEY_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("KEY_BOT_TOKEN belum di-set. Set env var KEY_BOT_TOKEN dulu.")
WHITELIST_FILE = "whitelist.json"
KEYS_FILE = "keys.json"

def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_whitelist(whitelist):
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(whitelist, f, indent=4)

def parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except:
        return None

def get_duration_days_from_key_info(key_info):
    days = key_info.get("duration_days")
    if isinstance(days, int) and days > 0:
        return days
    category = str(key_info.get("category", "")).lower().strip()
    if category == "week":
        return 7
    if category == "month":
        return 30
    return None

def is_whitelisted(user_id):
    whitelist = load_whitelist()
    now = datetime.now()
    active_whitelist = []
    changed = False

    for entry in whitelist:
        expires_at = parse_iso_datetime(entry.get("access_expires_at"))
        if expires_at is not None and now >= expires_at:
            changed = True
            continue
        active_whitelist.append(entry)

    if changed:
        save_whitelist(active_whitelist)

    return str(user_id) in [str(w['user_id']) for w in active_whitelist]

def load_keys():
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=4)

def add_to_whitelist(user_id, username, key):
    whitelist = load_whitelist()
    keys_data = load_keys()
    now = datetime.now()
    key_info = keys_data.get(key, {})
    duration_days = get_duration_days_from_key_info(key_info)
    access_started_at = now.isoformat()
    access_expires_at = (now + timedelta(days=duration_days)).isoformat() if duration_days else None

    for w in whitelist:
        if str(w['user_id']) == str(user_id):
            if key not in w['keys']:
                w['keys'].append(key)
            w['username'] = username
            w['access_started_at'] = access_started_at
            w['access_expires_at'] = access_expires_at
            w['last_updated'] = access_started_at
            save_whitelist(whitelist)
            return True

    new_entry = {
        "user_id": str(user_id),
        "username": username,
        "keys": [key],
        "whitelisted_at": access_started_at,
        "access_started_at": access_started_at,
        "access_expires_at": access_expires_at,
        "last_updated": access_started_at
    }
    whitelist.append(new_entry)
    save_whitelist(whitelist)
    return True

def redeem_key(key, user_id, username):
    keys = load_keys()
    key = key.upper().strip()
    
    if key not in keys:
        return False, "Key tidak ditemukan!"
    
    key_info = keys[key]
    
    if key_info.get("used", False):
        return False, "Key sudah digunakan!"
    
    keys[key]["used"] = True
    keys[key]["used_by"] = str(user_id)
    keys[key]["used_at"] = datetime.now().isoformat()
    save_keys(keys)
 
    add_to_whitelist(user_id, username, key)
    
    return True, f"Key {key} berhasil diredeem!"

def generate_key(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


intents = discord.Intents.default()
intents.message_content = True

print("Creating key bot...")
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
_key_panel_view = None

def create_keys_for_plan(jumlah, plan_key):
    plan_map = {
        "lifetime": ("Lifetime", None),
        "week": ("Week", 7),
        "month": ("Month", 30),
    }
    plan_name, days = plan_map[plan_key]
    now = datetime.now()
    expires_at = (now + timedelta(days=days)).isoformat() if days is not None else None

    keys = load_keys()
    generated_keys = []
    for _ in range(jumlah):
        new_key = f"KEY-{generate_key(6)}"
        while new_key in keys:
            new_key = f"KEY-{generate_key(6)}"
        keys[new_key] = {
            "name": f"Premium Access ({plan_name})",
            "available": True,
            "used": False,
            "category": plan_name,
            "duration_days": days,
            "created_at": now.isoformat(),
            "expires_at": expires_at
        }
        generated_keys.append(new_key)

    save_keys(keys)
    return plan_name, expires_at, generated_keys


class GenerateKeyAmountModal(discord.ui.Modal):
    def __init__(self, plan_key):
        super().__init__(title="Generate Key", custom_id=f"generate_key_amount_{plan_key}")
        self.plan_key = plan_key
        self.jumlah_input = discord.ui.TextInput(
            label="Jumlah Key (1-50)",
            placeholder="Contoh: 5",
            style=discord.TextStyle.short,
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.jumlah_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw_jumlah = self.jumlah_input.value.strip()
        if not raw_jumlah.isdigit():
            await interaction.response.send_message("Jumlah harus berupa angka (1-50).", ephemeral=True)
            return

        jumlah = int(raw_jumlah)
        if jumlah < 1 or jumlah > 50:
            await interaction.response.send_message("Jumlah key harus antara 1 sampai 50.", ephemeral=True)
            return

        plan_name, expires_at, generated_keys = create_keys_for_plan(jumlah, self.plan_key)

        embed = discord.Embed(
            title="Key Berhasil Dihasilkan",
            description=f"Berhasil membuat **{jumlah}** key dengan kategori **{plan_name}**.",
            color=0x00FF00
        )
        embed.add_field(name="Kategori", value=plan_name, inline=True)
        embed.add_field(name="Jumlah", value=str(jumlah), inline=True)
        embed.add_field(name="Expired", value=expires_at if expires_at else "Never (Lifetime)", inline=False)
        embed.add_field(name="Keys", value="\n".join([f"`{k}`" for k in generated_keys]), inline=False)
        embed.set_footer(text=f"Key Master | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GenerateCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Lifetime", value="lifetime", description="Akses permanen"),
            discord.SelectOption(label="Week", value="week", description="Aktif 7 hari"),
            discord.SelectOption(label="Month", value="month", description="Aktif 30 hari"),
        ]
        super().__init__(
            placeholder="Pilih kategori key...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="generate_category_select"
        )

    async def callback(self, interaction: discord.Interaction):
        plan_key = self.values[0]
        await interaction.response.send_modal(GenerateKeyAmountModal(plan_key))


class GenerateCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(GenerateCategorySelect())



class KeyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Generate Key", style=discord.ButtonStyle.blurple, custom_id="generate_key_btn")
    async def generate_key_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ADMIN_IDS = [975269168184168539]
        if interaction.user.id in ADMIN_IDS:
            embed = discord.Embed(
                title="Generate Key",
                description="Pilih kategori key terlebih dahulu, lalu isi jumlah key.",
                color=0x0099FF
            )
            await interaction.response.send_message(embed=embed, view=GenerateCategoryView(), ephemeral=True)
        else:
            # Show instructions for regular users
            embed = discord.Embed(
                title="🎫 Cara Mendapatkan Key",
                description="Ikuti langkah berikut untuk mendapatkan key:",
                color=0x0099FF
            )
            embed.add_field(
                name="📝 Langkah-langkah:",
                value="1. Hubungi admin untuk membeli key\n"
                      "2. Setelah mendapatkan key, buka **Script Panel**\n"
                      "3. Gunakan perintah `/redeem` diikuti dengan key Anda\n"
                      "4. Contoh: `/redeem KEY-XXXXXX`\n"
                      "5. Setelah redeem berhasil, Anda akan otomatis di-whitelist",
                inline=False
            )
            embed.add_field(
                name="⚠️ Perhatian:",
                value="• Key hanya bisa digunakan sekali\n"
                      "• Setelah diredeem di Script Panel, Anda akan di-whitelist otomatis\n"
                      "• Hubungi admin jika ada masalah",
                inline=False
            )
            embed.set_footer(text=f"Key Master | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="My Key Info", style=discord.ButtonStyle.green, custom_id="my_key_info_btn")
    async def my_key_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        whitelist = load_whitelist()
        
        user_data = None
        for w in whitelist:
            if str(w['user_id']) == str(user_id):
                user_data = w
                break
        
        embed = discord.Embed(
            title="🔑 Your Key Info",
            description=f"Information for: **{interaction.user}**",
            color=0x0099FF
        )
        
        if user_data:
            keys = user_data.get('keys', [])
            whitelisted_at = user_data.get('whitelisted_at', 'N/A')
            
            embed.add_field(
                name="✅ Status",
                value="Whitelisted",
                inline=True
            )
            embed.add_field(
                name="🔑 Keys Redeemed",
                value=str(len(keys)),
                inline=True
            )
            embed.add_field(
                name="📝 Key Details",
                value=", ".join([f"`{k}`" for k in keys]) if keys else "No keys",
                inline=False
            )
            embed.add_field(
                name="📅 Whitelisted At",
                value=whitelisted_at,
                inline=True
            )
        else:
            embed.add_field(
                name="❌ Status",
                value="Not Whitelisted",
                inline=True
            )
            embed.add_field(
                name="ℹ️ Info",
                value="Anda belum mereedeem key apapun.\nGunakan tombol **Generate Key** untuk melihat cara mendapatkan akses.",
                inline=False
            )
        
        embed.set_footer(text="Key Bot | Powered by DrxDvs")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="User List", style=discord.ButtonStyle.gray, custom_id="user_list_btn")
    async def user_list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ADMIN_IDS = [975269168184168539]
        if interaction.user.id not in ADMIN_IDS:
            embed = discord.Embed(
                title="Akses Ditolak",
                description="Tombol ini hanya bisa digunakan admin.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        whitelist = load_whitelist()
        embed = discord.Embed(
            title="User List",
            description=f"Total whitelisted users: **{len(whitelist)}**",
            color=0x0099FF
        )
        
        if not whitelist:
            embed.add_field(
                name="Info",
                value="Belum ada user di whitelist.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        chunk_size = 25
        for index in range(0, len(whitelist), chunk_size):
            chunk = whitelist[index:index + chunk_size]
            lines = []
            for row in chunk:
                username = row.get("username", "Unknown")
                user_id = row.get("user_id", "N/A")
                keys = ", ".join(row.get("keys", [])) if row.get("keys") else "-"
                lines.append(f"• {username} (`{user_id}`) | keys: {keys}")
            embed.add_field(
                name=f"Users {index + 1}-{index + len(chunk)}",
                value="\n".join(lines),
                inline=False
            )
        
        embed.set_footer(text=f"Key Bot | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    

class KeyRedeemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Redeem Key", custom_id="key_redeem_modal")
        
        self.key_input = discord.ui.TextInput(
            label="Masukkan Key",
            placeholder="Contoh: KEY-ABC123",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.key_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            key = self.key_input.value.upper().strip()
            keys = load_keys()
            
            if key in keys:
                key_info = keys[key]
                
                if key_info.get("used", False):
                    error_embed = discord.Embed(
                        title="Key Sudah Digunakan",
                        description="Key " + key + " sudah digunakan sebelumnya!",
                        color=0xFF0000
                    )
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                    return

                keys[key]["used"] = True
                keys[key]["used_by"] = str(interaction.user.id)
                keys[key]["used_at"] = datetime.now().isoformat()
                save_keys(keys)

                user_id = interaction.user.id
                username = str(interaction.user)
                add_to_whitelist(user_id, username, key)
                
                success_embed = discord.Embed(
                    title="✅ Redeem Berhasil",
                    description="Key " + f"`{key}`" + " berhasil diredeem!",
                    color=0x00ff88
                )
                success_embed.add_field(
                    name="Item",
                    value=chr(96) + key_info.get("name", "Premium Access") + chr(96),
                    inline=False
                )
                success_embed.add_field(
                    name="Whitelist Status",
                    value="✅ Anda sudah di-whitelist untuk menggunakan bot!",
                    inline=False
                )
                success_embed.set_footer(text=f"Key Bot | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
                
            else:
                error_embed = discord.Embed(
                    title="❌ Key Tidak Valid",
                    description="Key " + key + " tidak ditemukan atau tidak valid!",
                    color=0xFF0000
                )
                error_embed.add_field(
                    name="Catatan",
                    value="Pastikan Anda memasukkan key yang benar.\nHubungi admin untuk mendapatkan key yang valid.",
                    inline=False
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except Exception as e:
            print(f"Error in on_submit: {e}")
            import traceback
            traceback.print_exc()
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan saat memproses redeem: {str(e)}",
                color=0xFF0000
            )
            try:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except:
                try:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                except:
                    pass


@tree.command(name="genkey", description="Generate key baru (Admin Only)")
async def genkey(interaction: discord.Interaction, jumlah: int = 1):
    ADMIN_IDS = [975269168184168539] 
    
    if ADMIN_IDS and interaction.user.id not in ADMIN_IDS:
        embed = discord.Embed(
            title="❌ Akses Ditolak",
            description="Anda tidak memiliki akses untuk menggunakan perintah ini!",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if jumlah < 1 or jumlah > 50:
        embed = discord.Embed(
            title="❌ Error",
            description="Jumlah key yang dihasilkan harus antara 1-50!",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)
        return

    keys = load_keys()
    generated_keys = []
    
    for i in range(jumlah):
        new_key = f"KEY-{generate_key(6)}"
        keys[new_key] = {
            "name": "Premium Access",
            "available": True,
            "used": False,
            "created_at": datetime.now().isoformat()
        }
        generated_keys.append(new_key)
    
    save_keys(keys)
    
    embed = discord.Embed(
        title="✅ Key Berhasil Dihasilkan!",
        description=f"Berhasil membuat **{jumlah}** key baru:",
        color=0x00FF00
    )
    
    keys_text = "\n".join([f"`{k}`" for k in generated_keys])
    embed.add_field(
        name="🔑 Keys:",
        value=keys_text,
        inline=False
    )
    embed.add_field(
        name="📝 Catatan:",
        value="• Berikan key ini kepada customer Anda\n"
              "• Customer perlu redeem key di **Customer Panel** dengan perintah `/redeem KEY`\n"
              "• Setelah redeem, customer akan otomatis masuk whitelist",
        inline=False
    )
    embed.set_footer(text="DrxDvs Key System")
    
    await interaction.response.send_message(embed=embed)


@tree.command(name="getkey", description="Cara mendapatkan akses bot")
async def getkey(interaction: discord.Interaction):
    user_id = interaction.user.id

    if is_whitelisted(user_id):
        embed = discord.Embed(
            title="❌ Anda Sudah Memiliki Akses",
            description="Anda sudah di-whitelist dan bisa menggunakan bot!",
            color=0xFFAA00
        )
        embed.add_field(
            name="Cara Penggunaan:",
            value="Gunakan perintah `/locating` di server Discord bot.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎫 Cara Mendapatkan Akses Bot",
        description="Ikuti langkah berikut untuk mendapatkan akses bot:",
        color=0x0099FF
    )
    embed.add_field(
        name="📝 Langkah-langkah:",
        value="1. Beli key dari admin kami\n"
              "2. Buka **Script Panel** bot (bukan key bot ini)\n"
              "3. Gunakan perintah `/redeem` followed by your key\n"
              "4. Contoh: `/redeem KEY-XXXXXX`\n"
              "5. Setelah redeem berhasil, Anda akan otomatis di-whitelist",
        inline=False
    )
    embed.add_field(
        name="⚠️ Perhatian:",
        value="• Key hanya bisa digunakan sekali\n"
              "• Setelah diredeem di Script Panel, Anda akan di-whitelist otomatis\n"
              "• Hubungi admin jika ada masalah",
        inline=False
    )
    embed.set_footer(text="DrxDvs Key System")
    
    await interaction.response.send_message(embed=embed)


@tree.command(name="keyinfo", description="Cek informasi key")
async def keyinfo(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if is_whitelisted(user_id):
        whitelist = load_whitelist()
        user_data = None
        for w in whitelist:
            if str(w['user_id']) == str(user_id):
                user_data = w
                break
        
        embed = discord.Embed(
            title="✅ Status Akses",
            description="Anda sudah memiliki akses ke bot!",
            color=0x00FF00
        )
        embed.add_field(
            name="👤 Username:",
            value=f"└ `{user_data['username']}`",
            inline=False
        )
        embed.add_field(
            name="🔑 Keys yang Dimiliki:",
            value=f"└ `{', '.join(user_data.get('keys', []))}`",
            inline=False
        )
        embed.add_field(
            name="📅 Tanggal Whitelist:",
            value=f"└ `{user_data.get('whitelisted_at', 'N/A')}`",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="❌ Belum Memiliki Akses",
            description="Anda belum memiliki akses ke bot.",
            color=0xFF0000
        )
        embed.add_field(
            name="💡 Cara Mendapatkan Akses:",
            value="Redeem key yang sudah Anda beli dengan klik tombol `Redeem Key`!",
            inline=False
        )
    
    embed.set_footer(text="DrxDvs Key System")
    await interaction.response.send_message(embed=embed)


@tree.command(name="panel", description="Buka Key Panel")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="DrxHub Key Panel",
        description="This panel is for the project: DrxHub\n\nIf you're an Admin, click on the buttons below to Get key",
        color=0x0099FF
    )
    embed.set_footer(text=f"Key Panel | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    global _key_panel_view
    if _key_panel_view is None:
        _key_panel_view = KeyPanelView()
        client.add_view(_key_panel_view)
    
    await interaction.response.send_message(embed=embed, view=_key_panel_view)


@client.event
async def on_ready():
    print(f"Bot {client.user} sudah online!")
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs")
    )
    global _key_panel_view
    _key_panel_view = KeyPanelView()
    client.add_view(_key_panel_view)
    print("Persistent view added!")
    
    print("Syncing commands...")
    try:
        tree.clear_commands(guild=None)
        tree.add_command(genkey)
        tree.add_command(getkey)
        tree.add_command(keyinfo)
        tree.add_command(panel)
        await tree.sync()
        print("Commands synced successfully!")
    except Exception as e:
        print(f"Error syncing commands: {e}")
        try:
            tree.add_command(panel)
            await tree.sync()
            print("Commands synced successfully after re-registration!")
        except Exception as e2:
            print(f"Error re-syncing commands: {e2}")
    
    print("Ketik /panel, /genkey, /getkey, atau /keyinfo di Discord")


if __name__ == "__main__":
    print("Starting key bot...")
    client.run(BOT_TOKEN)
