import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timedelta
from env_loader import load_env_file


load_env_file()

BOT_TOKEN = os.getenv("PANEL_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("PANEL_BOT_TOKEN belum di-set. Set env var PANEL_BOT_TOKEN dulu.")
WHITELIST_FILE = "whitelist.json"
KEYS_FILE = "keys.json"
DEVELOPER_CONTACT = "https://discord.com/users/975269168184168539"

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
    
    keys = load_keys()
    now = datetime.now()
    key_info = keys.get(key, {})
    duration_days = get_duration_days_from_key_info(key_info)
    access_started_at = now.isoformat()
    access_expires_at = (now + timedelta(days=duration_days)).isoformat() if duration_days else None

    if key in keys:
        keys[key]["used"] = True
        keys[key]["used_by"] = str(user_id)
        keys[key]["used_at"] = access_started_at
        save_keys(keys)
    
    for w in whitelist:
        if str(w['user_id']) == str(user_id):
            if key not in w['keys']:
                w['keys'].append(key)
            w['username'] = username
            w['access_started_at'] = access_started_at
            w['access_expires_at'] = access_expires_at
            w['last_updated'] = access_started_at
            save_whitelist(whitelist)
            return False
    
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

SCRIPT_CONTENT = ""

def get_valid_keys():
    """Get valid keys from keys.json file"""
    keys = load_keys()
    valid_keys = {}
    for key, info in keys.items():
        if not info.get("used", False):
            valid_keys[key] = {
                "name": info.get("name", "Premium Access"),
                "uses": info.get("uses", 1)
            }
    return valid_keys

redeemed_keys = {}
persistent_views = []

intents = discord.Intents.default()
intents.message_content = True

print("Creating script panel bot...")
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def get_code_block(script_content):
    """Helper function to create code block string"""
    bt = chr(96)
    return bt + bt + bt + "python\n" + script_content + "\n" + bt + bt + bt

_script_panel_view = None

class ScriptPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Contact Developer", style=discord.ButtonStyle.gray, url=DEVELOPER_CONTACT))
        
    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.blurple, custom_id="redeem_key_btn")
    async def redeem_key_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = KeyRedeemModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Get Stats", style=discord.ButtonStyle.green, custom_id="get_stats_btn")
    async def get_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        username = str(interaction.user)
        whitelist = load_whitelist()
        user_data = None
        for w in whitelist:
            if str(w['user_id']) == str(user_id):
                user_data = w
                break
        
        embed = discord.Embed(
            title="📊 Your Stats",
            description=f"Stats for: **{username}**",
            color=0x0099FF
        )
        
        if user_data:
            keys = user_data.get('keys', [])
            whitelisted_at = user_data.get('whitelisted_at', 'N/A')
            last_updated = user_data.get('last_updated', 'N/A')
            
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
            embed.add_field(
                name="🔄 Last Updated",
                value=last_updated,
                inline=True
            )
            usage_info = []
            for key in keys:
                used_count = redeemed_keys.get(key, 0)
                keys_data = load_keys()
                if key in keys_data:
                    max_uses = keys_data[key].get('uses', 1)
                    usage_info.append(f"`{key}`: {used_count}/{max_uses}")
            
            if usage_info:
                embed.add_field(
                    name="📈 Key Usage",
                    value="\n".join(usage_info),
                    inline=False
                )
        else:
            embed.add_field(
                name="❌ Status",
                value="Not Whitelisted",
                inline=True
            )
            embed.add_field(
                name="ℹ️ Info",
                value="Anda belum mereedeem key apapun.\nGunakan tombol Redeem Key untuk mengaktifkan akses.",
                inline=False
            )
        
        embed.set_footer(text="Script Panel | Powered by DrxDvs")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="How to Get Key", style=discord.ButtonStyle.red, custom_id="how_to_get_key_btn")
    async def how_to_get_key_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Cara Mendapatkan Akses Bot",
            description="Ikuti langkah berikut untuk mendapatkan akses bot:",
            color=0x0099FF
        )
        embed.add_field(
            name="Langkah-langkah:",
            value="1. Create ticket di <#1478197304950521989> untuk membeli key\n"
                  "2. Klik tombol **Redeem Key** di <#1478215925005156362> ini\n"
                  "3. Masukkan key Anda pada form redeem\n"
                  "4. Setelah redeem berhasil, Anda akan otomatis di-whitelist",
            inline=False
        )
        embed.add_field(
            name="Perhatian:",
            value="• Key hanya bisa digunakan sekali\n"
                  "• Setelah diredeem, Anda akan di-whitelist otomatis\n"
                  "• Hubungi admin jika ada masalah",
            inline=False
        )
        embed.set_footer(text=f"Script Panel | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class KeyRedeemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Redeem Key", custom_id="key_redeem_modal")
        
        self.key_input = discord.ui.TextInput(
            label="Masukkan Key",
            placeholder="Contoh: KEY-1",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.key_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            key = self.key_input.value.upper().strip()
            VALID_KEYS = get_valid_keys()
            
            if key in VALID_KEYS:
                key_info = VALID_KEYS[key]
                
                if key in redeemed_keys:
                    used_count = redeemed_keys[key]
                    if used_count >= key_info["uses"]:
                        error_embed = discord.Embed(
                            title="Key Sudah Digunakan",
                            description="Key " + key + " sudah mencapai batas penggunaan!",
                            color=0xFF0000
                        )
                        await interaction.response.send_message(embed=error_embed, ephemeral=True)
                        return
                
                if key in redeemed_keys:
                    redeemed_keys[key] += 1
                else:
                    redeemed_keys[key] = 1
                
                success_embed = discord.Embed(
                    title="Redeem Berhasil",
                    description="Key " + f"`{key}`" + " berhasil diredeem!",
                    color=0x00ff88
                )
                success_embed.add_field(
                    name="Item",
                    value=chr(96) + key_info["name"] + chr(96),
                    inline=False
                )
                success_embed.add_field(
                    name="Penggunaan",
                    value=str(redeemed_keys[key]) + "/" + str(key_info["uses"]),
                    inline=False
                )
                
                user_id = interaction.user.id
                username = str(interaction.user)
                add_to_whitelist(user_id, username, key)
                
                success_embed.add_field(
                    name="Whitelist Status",
                    value="✅ Anda sudah di-whitelist untuk menggunakan bot!",
                    inline=False
                )
                success_embed.set_footer(text=f"Customer Panel | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
                
            else:
                error_embed = discord.Embed(
                    title="Key Tidak Valid",
                    description="Key " + key + " tidak ditemukan atau tidak valid!",
                    color=0xFF0000
                )
                error_embed.add_field(
                    name="Catatan",
                    value="Pastikan Anda memasukkan key yang benar.\nContoh key yang valid: KEY-1, KEY-2, KEY-3",
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


@tree.command(name="panel", description="Buka Script Panel")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="DrxHub Script Panel",
        description="This panel is for the project: DrxHub\n\nIf you're a buyer, click on the buttons below to redeem your key",
        color=0x0099FF
    )
    embed.set_footer(text=f"Customer Panel | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    global _script_panel_view
    if _script_panel_view is None:
        _script_panel_view = ScriptPanelView()
        client.add_view(_script_panel_view)
    
    await interaction.response.send_message(embed=embed, view=_script_panel_view)


@tree.command(name="redeem", description="Tukarkan key Anda")
async def redeem(interaction: discord.Interaction, key: str):
    key = key.upper().strip()
    VALID_KEYS = get_valid_keys()
    
    if key in VALID_KEYS:
        key_info = VALID_KEYS[key]
        
        if key in redeemed_keys:
            used_count = redeemed_keys[key]
            if used_count >= key_info["uses"]:
                error_embed = discord.Embed(
                    title="Key Sudah Digunakan",
                    description="Key " + key + " sudah mencapai batas penggunaan!",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=error_embed)
                return
        
        if key in redeemed_keys:
            redeemed_keys[key] += 1
        else:
            redeemed_keys[key] = 1
        
        user_id = interaction.user.id
        username = str(interaction.user)
        add_to_whitelist(user_id, username, key)
        
        success_embed = discord.Embed(
            title="Redeem Berhasil",
            description="Key " + key + " berhasil diredeem!",
            color=0x00ff88
        )
        success_embed.add_field(
            name="Item",
            value=chr(96) + key_info["name"] + chr(96),
            inline=False
        )
        success_embed.add_field(
            name="Penggunaan",
            value=str(redeemed_keys[key]) + "/" + str(key_info["uses"]),
            inline=False
        )
        success_embed.add_field(
            name="Whitelist Status",
            value="✅ Anda sudah di-whitelist untuk menggunakan bot!",
            inline=False
        )
        success_embed.set_footer(text=f"Customer Panel | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        await interaction.response.send_message(embed=success_embed)
        
    else:
        error_embed = discord.Embed(
            title="Key Tidak Valid",
            description="Key " + key + " tidak ditemukan!",
            color=0xFF0000
        )
        error_embed.add_field(
            name="Catatan",
            value="Hubungi admin untuk mendapatkan key yang valid.",
            inline=False
        )
        await interaction.response.send_message(embed=error_embed)


@tree.command(name="keylist", description="Lihat daftar key yang tersedia")
async def keylist(interaction: discord.Interaction):
    VALID_KEYS = get_valid_keys()
    
    embed = discord.Embed(
        title="Daftar Key Valid",
        description="Berikut adalah daftar key yang dapat digunakan:",
        color=0x0099FF
    )
    
    for key, info in VALID_KEYS.items():
        used = redeemed_keys.get(key, 0)
        embed.add_field(
            name=key,
            value=chr(96) + info["name"] + chr(96) + " (Used: " + str(used) + "/" + str(info["uses"]) + ")",
            inline=False
        )
    
    embed.set_footer(text=f"Customer Panel | Powered by DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    await interaction.response.send_message(embed=embed)


@client.event
async def on_ready():
    print(f"Bot {client.user} sudah online!")
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs")
    )
    global _script_panel_view
    _script_panel_view = ScriptPanelView()
    client.add_view(_script_panel_view)
    print("Persistent view added!")
    
    print("Syncing commands...")
    try:
        await tree.sync()
        print("Commands synced successfully!")
    except Exception as e:
        print(f"Error syncing commands: {e}")
        try:
            tree.add_command(panel)
            tree.add_command(redeem)
            tree.add_command(keylist)
            await tree.sync()
            print("Commands synced successfully after re-registration!")
        except Exception as e2:
            print(f"Error re-syncing commands: {e2}")
    
    
    print("Ketik /panel, /redeem, atau /keylist di Discord")


if __name__ == "__main__":
    print("Starting script panel bot...")
    client.run(BOT_TOKEN)
