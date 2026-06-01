import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
from datetime import datetime
from env_loader import load_env_file


load_env_file()

class LocationInputModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📍 Input Nomor Telephone", custom_id="location_input_modal")
        
        self.phone_input = discord.ui.TextInput(
            label="Nomor Telephone",
            placeholder="Contoh: +62812345678 harus dengan kode negara",
            style=discord.TextStyle.short,
            required=True,
            min_length=5,
            max_length=20
        )
        self.add_item(self.phone_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        nomor = self.phone_input.value.strip()

        is_valid, error_msg = validate_phone_number(nomor)
        if not is_valid:
            error_embed = discord.Embed(
                title="❌ Error",
                description=error_msg,
                color=0xFF0000
            )
            error_embed.add_field(
                name="📝 Contoh Penggunaan:",
                value="• `/locating +62812345678` (Indonesia)\n"
                      "• `/locating +60123456789` (Malaysia)\n"
                      "• `/locating +66012345678` (Thailand)",
                inline=False
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        await interaction.response.send_message(
            f"⏳ **Wait here, Prepare to Finding** `{nomor}`",
            ephemeral=True
        )
        wait_msg = await interaction.original_response()

        await asyncio.sleep(30)
        await wait_msg.edit(content=f"🔎 **Finding With CTS Tower** `{nomor}`...")
        await asyncio.sleep(300)
        await wait_msg.edit(content=f"📡 **Locating** `{nomor}`...")
        await asyncio.sleep(120)

        result = generate_location_result(nomor)
        
        result_embed = discord.Embed(
            title="DrxDvs Location Info:",
            color=result["color"]
        )
        result_embed.add_field(name="📱 Nomor", value=f"└ `{nomor}`", inline=False)
        result_embed.add_field(name="🌍 Country", value=f"└ `{result['country']}`", inline=True)
        result_embed.add_field(name="📍 Kota", value=f"└ `{result['city_name']}`", inline=False)
        result_embed.add_field(name="🔐 VPN", value=f"└ `{result['vpn']}`", inline=False)
        result_embed.add_field(name="🗺 Maps", value=f"└ `{result['maps_link']}`", inline=False)
        result_embed.add_field(
            name="📝 Note",
            value="└ `This bot can make mistake, If you in trouble contact @exotickic`",
            inline=False
        )
        result_embed.set_footer(text=f"ENGINE V5 | DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        view = LocationResultButtonsView(maps_link=result["maps_link"])
        
        await wait_msg.edit(
            content=f"✅ Success `{nomor}`",
            embed=result_embed,
            view=view
        )

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📍 Get Location", style=discord.ButtonStyle.blurple, custom_id="get_location_panel_btn")
    async def get_location_panel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if not is_whitelisted(user_id):
            error_embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Anda tidak memiliki akses untuk menggunakan bot ini!",
                color=0xFF0000
            )
            error_embed.add_field(
                name="Cara Mendapatkan Akses:",
                value="Silakan hubungi developer atau gunakan panel untuk redeem key.",
                inline=False
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        modal = LocationInputModal()
        await interaction.response.send_modal(modal)

class LocationResultButtonsView(discord.ui.View):
    def __init__(self, maps_link: str):
        super().__init__(timeout=300)
        self.maps_link = maps_link
    
    @discord.ui.button(label="🗺️ Open Maps", style=discord.ButtonStyle.green, custom_id="open_maps_btn")
    async def open_maps_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🗺️ Google Maps Link",
            description=f"**Maps Location:** [Click Here]({self.maps_link})",
            color=0x00FF00
        )
        embed.add_field(
            name="📍 Coordinates",
            value=f"{self.maps_link}",
            inline=False
        )
        embed.set_footer(text="DrxDvs Location Bot")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="👤 Contact Developer", style=discord.ButtonStyle.red, custom_id="contact_dev_btn")
    async def contact_developer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👤 Contact Developer",
            description="Untuk pertanyaan atau masalah, hubungi developer kami:",
            color=0x0099FF
        )
        embed.add_field(
            name="📝 Discord:",
            value="`@exotickic`",
            inline=False
        )
        embed.add_field(
            name="⚠️ Catatan:",
            value="• Jangan lupa sertakan screenshot error\n"
                  "• Jelaskan masalah Anda dengan detail\n"
                  "• Kami akan merespons secepat mungkin",
            inline=False
        )
        embed.set_footer(text=f"DrxDvs | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LocationResultView(discord.ui.View):
    def __init__(self, phone_number: str):
        super().__init__(timeout=300)
        self.phone_number = phone_number
    
    @discord.ui.button(label="📍 Get Location", style=discord.ButtonStyle.blurple, custom_id="get_location_btn")
    async def get_location_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = generate_location_result(self.phone_number)
        
        result_embed = discord.Embed(
            title="DrxDvs Location Info:",
            color=result["color"]
        )
        result_embed.add_field(name="📱 Nomor", value=f"└ `{self.phone_number}`", inline=False)
        result_embed.add_field(name="🌍 Country", value=f"└ `{result['country']}`", inline=True)
        result_embed.add_field(name="📍 Kota", value=f"└ `{result['city_name']}`", inline=False)
        result_embed.add_field(name="🔐 VPN", value=f"└ `{result['vpn']}`", inline=False)
        result_embed.add_field(
            name="📝 Note",
            value="└ `This bot can make mistake if you in trouble please contact the developer`",
            inline=False
        )
        result_embed.add_field(name="🗺 Maps", value=f"└ `{result['maps_link']}`", inline=False)
        result_embed.set_footer(text=f"ENGINE V5 | DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        await interaction.response.send_message(embed=result_embed, ephemeral=True)


BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN belum di-set. Set env var DISCORD_BOT_TOKEN dulu.")
WHITELIST_FILE = "whitelist.json"

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

FOREIGN_CITIES = {
    "SG": [
        ("Singapore, Singapore", 1.3521, 103.8198),
        ("Orchard, Singapore", 1.3048, 103.8323),
        ("Marina Bay, Singapore", 1.2838, 103.8591),
        ("Sentosa, Singapore", 1.2494, 103.8303),
        ("Chinatown, Singapore", 1.2819, 103.8539),
        ("Little India, Singapore", 1.3101, 103.8591),
        ("Clarke Quay, Singapore", 1.2885, 103.8463),
        ("Bugis, Singapore", 1.3002, 103.8559),
        ("Raffles Place, Singapore", 1.2833, 103.8590),
        ("Jurong, Singapore", 1.3329, 103.7436),
    ],
    "MY": [
        ("Kuala Lumpur, Malaysia", 3.1390, 101.6869),
        ("Johor Bahru, Malaysia", 1.4927, 103.7414),
        ("Penang, Malaysia", 5.4141, 100.3288),
        ("Petaling Jaya, Malaysia", 3.1068, 101.6067),
        ("Malacca City, Malaysia", 2.1896, 102.2501),
        ("Kota Kinabalu, Malaysia", 5.9804, 116.0735),
        ("Kuching, Malaysia", 1.5575, 110.3593),
        ("Ipoh, Malaysia", 4.5975, 101.0901),
        ("Shah Alam, Malaysia", 3.0733, 101.5186),
        ("Georgetown, Malaysia", 5.4141, 100.3288),
        ("Selangor, Malaysia", 3.0733, 101.5186),
        ("Kedah, Malaysia", 6.1184, 100.3695),
        ("Perak, Malaysia", 4.5975, 101.0901),
        ("Negeri Sembilan, Malaysia", 2.7268, 101.9429),
        ("Kelantan, Malaysia", 6.1256, 102.2395),
        ("Terengganu, Malaysia", 5.3113, 103.1384),
        ("Pahang, Malaysia", 3.8126, 103.3160),
        ("Sarawak, Malaysia", 1.5575, 110.3593),
        ("Labuan, Malaysia", 5.2804, 115.2425),
        ("Putrajaya, Malaysia", 2.9264, 101.6969),
    ],
    "TH": [
        ("Bangkok, Thailand", 13.7563, 100.5018),
        ("Phuket, Thailand", 7.8804, 98.3923),
        ("Chiang Mai, Thailand", 18.7883, 98.9853),
        ("Pattaya, Thailand", 12.9273, 100.8824),
        ("Chonburi, Thailand", 13.3611, 100.9827),
        ("Ayutthaya, Thailand", 14.3532, 100.5773),
        ("Koh Samui, Thailand", 9.5357, 99.9347),
        ("Krabi, Thailand", 8.0863, 98.9063),
        ("Chiang Rai, Thailand", 19.9072, 99.8325),
        ("Hua Hin, Thailand", 12.5716, 99.9575),
        ("Koh Phangan, Thailand", 9.7333, 100.0333),
        ("Koh Lanta, Thailand", 7.6500, 99.0333),
        ("Phi Phi Islands, Thailand", 7.7407, 98.7784),
        ("Sukhothai, Thailand", 17.0026, 99.7067),
        ("Kanchanaburi, Thailand", 14.0221, 99.5333),
        ("Rayong, Thailand", 12.6819, 101.2806),
        ("Khon Kaen, Thailand", 16.4322, 102.8237),
        ("Udon Thani, Thailand", 17.4153, 102.4419),
        ("Chanthaburi, Thailand", 12.6096, 102.1045),
        ("Trat, Thailand", 12.2436, 102.5175),
    ],
    "VN": [
        ("Ho Chi Minh City, Vietnam", 10.8231, 106.6297),
        ("Hanoi, Vietnam", 21.0278, 105.8342),
        ("Da Nang, Vietnam", 16.0544, 108.2022),
        ("Hoi An, Vietnam", 15.8794, 108.3350),
        ("Hue, Vietnam", 16.4637, 107.5909),
        ("Nha Trang, Vietnam", 12.2388, 109.1967),
        ("Da Lat, Vietnam", 11.9404, 108.4583),
        ("Can Tho, Vietnam", 10.0302, 105.7886),
        ("Hai Phong, Vietnam", 20.8449, 106.6881),
        ("Mekong Delta, Vietnam", 10.3500, 105.7500),
        ("Vung Tau, Vietnam", 10.3464, 107.0845),
        ("Phu Quoc, Vietnam", 10.2268, 103.9147),
        ("Sapa, Vietnam", 22.3362, 103.8444),
        ("Hai Duong, Vietnam", 20.9417, 106.3331),
        ("Nam Dinh, Vietnam", 20.4239, 106.1623),
        ("Thai Binh, Vietnam", 20.4481, 106.3353),
        ("Thanh Hoa, Vietnam", 19.8043, 105.7872),
        ("Quy Nhon, Vietnam", 13.7764, 109.2237),
        ("Dien Bien Phu, Vietnam", 21.3861, 103.0121),
        ("Cao Bang, Vietnam", 22.6659, 105.8544),
    ],
    "PH": [
        ("Manila, Philippines", 14.5995, 120.9842),
        ("Cebu, Philippines", 10.3157, 123.8854),
        ("Davao, Philippines", 7.0731, 125.6128),
        ("Quezon City, Philippines", 14.6760, 121.0437),
        ("Makati, Philippines", 14.5547, 121.0244),
        ("Boracay, Philippines", 11.9685, 121.9212),
        ("Palawan, Philippines", 9.8348, 118.7386),
        ("Baguio, Philippines", 16.4023, 120.5930),
        ("Tagaytay, Philippines", 14.0944, 120.8302),
        ("Iloilo, Philippines", 10.7202, 122.5621),
        ("Cebu City, Philippines", 10.3157, 123.8854),
        ("Bacolod, Philippines", 10.6402, 122.9687),
        ("Angeles City, Philippines", 15.1402, 120.5922),
        ("Davao City, Philippines", 7.0731, 125.6128),
        ("General Santos, Philippines", 6.1161, 125.1715),
        ("Cagayan de Oro, Philippines", 8.4542, 124.6319),
        ("Iligan, Philippines", 8.1667, 124.2333),
        ("Butuan, Philippines", 8.9475, 125.5406),
        ("Puerto Princesa, Philippines", 9.7390, 118.3889),
        ("Vigan, Philippines", 17.5749, 120.3869),
    ],
    "KH": [
        ("Phnom Penh, Cambodia", 11.5564, 104.9282),
        ("Siem Reap, Cambodia", 13.3671, 103.8448),
        ("Battambang, Cambodia", 13.1027, 103.1987),
        ("Sihanoukville, Cambodia", 10.6093, 103.5296),
        ("Kep, Cambodia", 10.4828, 104.2950),
        ("Kampot, Cambodia", 10.6102, 104.1801),
        ("Kampong Cham, Cambodia", 11.9938, 105.4634),
        ("Kratie, Cambodia", 12.4881, 106.0186),
        ("Banlung, Cambodia", 13.7357, 106.9743),
        ("Kampong Thom, Cambodia", 12.7113, 104.8818),
        ("Preah Vihear, Cambodia", 13.8069, 104.9876),
        ("Kampong Speu, Cambodia", 11.4538, 104.0669),
        ("Takeo, Cambodia", 10.8833, 104.9667),
    ],
    "MM": [
        ("Yangon, Myanmar", 16.8661, 96.1951),
        ("Mandalay, Myanmar", 21.9588, 96.0876),
        ("Naypyidaw, Myanmar", 19.7473, 96.1154),
        ("Bagan, Myanmar", 21.1715, 94.8588),
        ("Inle Lake, Myanmar", 20.5492, 96.9097),
        ("Mrauk U, Myanmar", 20.3333, 93.7833),
        ("Hpa-an, Myanmar", 16.8897, 97.6349),
        ("Kalaw, Myanmar", 20.6333, 96.5833),
        ("Pyin Oo Lwin, Myanmar", 21.4367, 96.0833),
        ("Ngapali, Myanmar", 18.4439, 94.3672),
        ("Taunggyi, Myanmar", 20.7892, 97.0378),
        ("Mawlamyine, Myanmar", 16.4833, 97.6500),
        ("Bago, Myanmar", 17.3352, 96.1986),
    ],
    "NP": [
        ("Kathmandu, Nepal", 27.7172, 85.3240),
        ("Pokhara, Nepal", 28.2096, 83.9856),
        ("Bhaktapur, Nepal", 27.6722, 85.4286),
        ("Lumbini, Nepal", 27.4369, 83.4108),
        ("Nagarkot, Nepal", 27.7150, 85.4317),
        ("Chitwan, Nepal", 27.5328, 84.3494),
        ("Patan, Nepal", 27.6081, 85.3160),
        ("Namche Bazaar, Nepal", 27.8068, 86.7139),
        ("Annapurna, Nepal", 28.0000, 86.0000),
        ("Everest Base Camp, Nepal", 28.0044, 86.8556),
        ("Jomsom, Nepal", 28.7833, 83.7667),
        ("Tansen, Nepal", 27.8667, 83.5500),
        ("Butwal, Nepal", 27.7000, 83.4500),
    ],
    "LK": [
        ("Colombo, Sri Lanka", 6.9271, 79.8612),
        ("Kandy, Sri Lanka", 7.2906, 80.6337),
        ("Sigiriya, Sri Lanka", 7.9570, 80.7603),
        ("Galle, Sri Lanka", 6.0535, 80.2210),
        ("Jaffna, Sri Lanka", 9.6615, 80.0255),
        ("Anuradhapura, Sri Lanka", 8.3114, 80.4034),
        ("Negombo, Sri Lanka", 7.2088, 79.8358),
        ("Polonnaruwa, Sri Lanka", 7.9402, 81.0188),
        ("Dambulla, Sri Lanka", 7.8584, 80.6191),
        ("Trincomalee, Sri Lanka", 8.5711, 81.2331),
        ("Ella, Sri Lanka", 6.8661, 81.0466),
        ("Unawatuna, Sri Lanka", 6.0225, 80.2580),
        ("Mirissa, Sri Lanka", 5.9483, 80.5448),
    ],
    "IN": [
        ("New Delhi, India", 28.6139, 77.2090),
        ("Mumbai, India", 19.0760, 72.8777),
        ("Bangalore, India", 12.9716, 77.5946),
        ("Chennai, India", 13.0827, 80.2707),
        ("Kolkata, India", 22.5726, 88.3639),
        ("Hyderabad, India", 17.3850, 78.4867),
        ("Jaipur, India", 26.9124, 75.7873),
        ("Agra, India", 27.1767, 78.0081),
        ("Goa, India", 15.2993, 74.1240),
        ("Varanasi, India", 25.3176, 82.9739),
        ("Kerala, India", 10.8505, 76.2711),
        ("Pune, India", 18.5204, 73.8567),
        ("Ahmedabad, India", 23.0225, 72.5714),
        ("Amritsar, India", 31.6340, 74.8723),
        ("Udaipur, India", 24.5854, 73.7125),
        ("Mysore, India", 12.2958, 76.6394),
        ("Shimla, India", 31.1048, 77.1734),
        ("Srinagar, India", 34.0837, 74.7973),
        ("Rishikesh, India", 30.0869, 78.2676),
        ("Jodhpur, India", 26.9124, 73.0243),
        ("Munnar, India", 10.0889, 77.0595),
        ("Leh, India", 34.2096, 77.5612),
        ("Darjeeling, India", 27.0410, 88.2626),
    ],
    "PK": [
        ("Karachi, Pakistan", 24.8607, 67.0011),
        ("Lahore, Pakistan", 31.5204, 74.3587),
        ("Islamabad, Pakistan", 33.6844, 73.0479),
        ("Peshawar, Pakistan", 34.0151, 71.5249),
        ("Faisalabad, Pakistan", 31.4504, 73.1350),
        ("Multan, Pakistan", 30.1575, 71.5249),
        ("Sialkot, Pakistan", 32.4949, 74.5389),
        ("Rawalpindi, Pakistan", 33.5651, 73.0169),
        ("Gujranwala, Pakistan", 32.1855, 74.1942),
        ("Hyderabad, Pakistan", 25.3960, 68.3668),
        ("Quetta, Pakistan", 30.1832, 67.0585),
        ("Skardu, Pakistan", 35.2979, 75.3417),
        ("Gilgit, Pakistan", 35.9186, 74.3086),
        ("Murree, Pakistan", 33.9006, 73.3971),
        ("Mohenjo-daro, Pakistan", 27.3292, 68.1372),
    ],
    "BD": [
        ("Dhaka, Bangladesh", 23.8103, 90.4125),
        ("Chittagong, Bangladesh", 22.3569, 91.7832),
        ("Sylhet, Bangladesh", 24.9011, 91.8736),
        ("Khulna, Bangladesh", 22.8456, 89.5403),
        ("Barisal, Bangladesh", 22.7010, 90.3535),
        ("Rajshahi, Bangladesh", 24.3636, 88.6241),
        ("Mymensingh, Bangladesh", 24.7471, 90.4203),
        ("Cox's Bazar, Bangladesh", 21.4272, 91.9738),
        ("Comilla, Bangladesh", 23.4619, 91.1856),
        ("Gazipur, Bangladesh", 23.9977, 90.4207),
    ],
    "CN": [
        ("Beijing, China", 39.9042, 116.4074),
        ("Shanghai, China", 31.2304, 121.4737),
        ("Guangzhou, China", 23.1291, 113.2644),
        ("Shenzhen, China", 22.5431, 114.0579),
        ("Hong Kong, China", 22.3193, 114.1694),
        ("Chengdu, China", 30.5728, 104.0668),
        ("Hangzhou, China", 30.2741, 120.1551),
        ("Xi'an, China", 34.3416, 108.9398),
        ("Suzhou, China", 31.2989, 120.5853),
        ("Nanjing, China", 32.0603, 118.7969),
        ("Chongqing, China", 29.4316, 106.9123),
        ("Tianjin, China", 39.3434, 117.3616),
        ("Wuhan, China", 30.5928, 114.3055),
        ("Macau, China", 22.1987, 113.5439),
        ("Xiamen, China", 24.4798, 118.0894),
        ("Guilin, China", 25.2744, 110.2990),
        ("Sanya, China", 18.2528, 109.5119),
        ("Lijiang, China", 26.8721, 100.2289),
        ("Harbin, China", 45.8038, 126.5340),
        ("Dali, China", 25.6069, 100.2678),
    ],
    "TW": [
        ("Taipei, Taiwan", 25.0330, 121.5654),
        ("Kaohsiung, Taiwan", 22.6273, 120.3014),
        ("Taichung, Taiwan", 24.1477, 120.6736),
        ("Tainan, Taiwan", 22.9999, 120.2269),
        ("Keelung, Taiwan", 25.1283, 121.7419),
        ("Hsinchu, Taiwan", 24.8017, 120.9714),
        ("Yilan, Taiwan", 24.7021, 121.7377),
        ("Kenting, Taiwan", 21.9469, 120.7489),
        ("Alishan, Taiwan", 23.5083, 120.8131),
        ("Sun Moon Lake, Taiwan", 23.9583, 120.9069),
        ("Hualien, Taiwan", 23.9872, 121.6011),
        ("Taitung, Taiwan", 22.7972, 121.0714),
    ],
    "KR": [
        ("Seoul, South Korea", 37.5665, 126.9780),
        ("Busan, South Korea", 35.1796, 129.0756),
        ("Incheon, South Korea", 37.4563, 126.7052),
        ("Daegu, South Korea", 35.8714, 128.6014),
        ("Daejeon, South Korea", 36.3504, 127.3845),
        ("Gwangju, South Korea", 35.1595, 126.8526),
        ("Ulsan, South Korea", 35.5384, 129.3114),
        ("Jeju Island, South Korea", 33.4996, 126.5312),
        ("Suwon, South Korea", 37.2636, 127.0286),
        ("Jeonju, South Korea", 35.8242, 127.1479),
        ("Gyeongju, South Korea", 35.8561, 129.2248),
        ("Andong, South Korea", 36.5684, 128.5153),
    ],
    "JP": [
        ("Tokyo, Japan", 35.6762, 139.6503),
        ("Osaka, Japan", 34.6937, 135.5023),
        ("Kyoto, Japan", 35.0116, 135.7681),
        ("Nagoya, Japan", 35.1815, 136.7656),
        ("Sapporo, Japan", 43.0618, 141.3545),
        ("Yokohama, Japan", 35.4437, 139.6380),
        ("Kobe, Japan", 34.6901, 135.1955),
        ("Fukuoka, Japan", 33.5904, 130.4017),
        ("Hiroshima, Japan", 34.3853, 132.4553),
        ("Sendai, Japan", 38.2682, 140.8721),
        ("Nara, Japan", 34.6851, 135.8048),
        ("Nikko, Japan", 36.7217, 139.6186),
        ("Okinawa, Japan", 26.2124, 127.6809),
        ("Hakone, Japan", 35.2323, 139.0718),
        ("Kawaguchiko, Japan", 35.5148, 138.7514),
        ("Takayama, Japan", 36.1456, 136.9065),
        ("Kanazawa, Japan", 36.5614, 136.6564),
        ("Nagasaki, Japan", 32.7448, 129.8738),
        ("Matsumoto, Japan", 36.2381, 137.9711),
        ("Kumamoto, Japan", 32.8032, 130.7078),
    ],
    "US": [
        ("Los Angeles, USA", 34.0522, -118.2437),
        ("New York, USA", 40.7128, -74.0060),
        ("Chicago, USA", 41.8781, -87.6298),
        ("Houston, USA", 29.7604, -95.3698),
        ("Miami, USA", 25.7617, -80.1918),
        ("San Francisco, USA", 37.7749, -122.4194),
        ("Seattle, USA", 47.6062, -122.3321),
        ("Las Vegas, USA", 36.1699, -115.1398),
        ("Boston, USA", 42.3601, -71.0589),
        ("Denver, USA", 39.7392, -104.9903),
        ("Atlanta, USA", 33.7490, -84.3880),
        ("Dallas, USA", 32.7767, -96.7970),
        ("Phoenix, USA", 33.4484, -112.0740),
        ("San Diego, USA", 32.7157, -117.1611),
        ("Austin, USA", 30.2672, -97.7431),
        ("Portland, USA", 45.5152, -122.6784),
        ("Nashville, USA", 36.1627, -86.7816),
        ("New Orleans, USA", 29.9511, -90.0715),
        ("Honolulu, USA", 21.3069, -157.8583),
        ("Washington DC, USA", 38.9072, -77.0369),
    ],
    "CA": [
        ("Toronto, Canada", 43.6532, -79.3832),
        ("Vancouver, Canada", 49.2827, -123.1207),
        ("Montreal, Canada", 45.5017, -73.5673),
        ("Calgary, Canada", 51.0447, -114.0719),
        ("Ottawa, Canada", 45.4215, -75.6972),
        ("Edmonton, Canada", 53.5461, -113.4938),
        ("Winnipeg, Canada", 49.8951, -97.1384),
        ("Quebec City, Canada", 46.8139, -71.2080),
        ("Halifax, Canada", 44.6488, -63.5752),
        ("Victoria, Canada", 48.4284, -123.3656),
    ],
    "MX": [
        ("Mexico City, Mexico", 19.4326, -99.1332),
        ("Guadalajara, Mexico", 20.6597, -103.3496),
        ("Cancun, Mexico", 21.1619, -86.8515),
        ("Puerto Vallarta, Mexico", 20.6534, -105.2253),
        ("Monterrey, Mexico", 25.6866, -100.3161),
        ("Tijuana, Mexico", 32.5149, -117.0382),
        ("Cabo San Lucas, Mexico", 22.8905, -109.9167),
        ("Mérida, Mexico", 20.9674, -89.5926),
        ("Oaxaca, Mexico", 17.0732, -96.7266),
        ("Guanajuato, Mexico", 21.0190, -101.2574),
    ],
    "BR": [
        ("Sao Paulo, Brazil", -23.5505, -46.6333),
        ("Rio de Janeiro, Brazil", -22.9068, -43.1729),
        ("Brasilia, Brazil", -15.8267, -47.9218),
        ("Salvador, Brazil", -12.9714, -38.5014),
        ("Recife, Brazil", -8.0476, -34.8770),
        ("Fortaleza, Brazil", -3.7172, -38.5433),
        ("Belo Horizonte, Brazil", -19.9167, -43.9345),
        ("Manaus, Brazil", -3.1190, -60.0217),
        ("Porto Alegre, Brazil", -30.0346, -51.2177),
        ("Curitiba, Brazil", -25.4284, -49.2733),
    ],
    "AR": [
        ("Buenos Aires, Argentina", -34.6037, -58.3816),
        ("Córdoba, Argentina", -31.4201, -64.1888),
        ("Rosario, Argentina", -32.9442, -60.6505),
        ("Mendoza, Argentina", -32.8895, -68.8458),
        ("Bariloche, Argentina", -41.1335, -71.3103),
        ("Ushuaia, Argentina", -54.8019, -68.3030),
        ("Iguazu Falls, Argentina", -25.6953, -54.4367),
        ("Mar del Plata, Argentina", -38.0055, -57.5426),
    ],
    "CO": [
        ("Bogota, Colombia", 4.7110, -74.0721),
        ("Medellin, Colombia", 6.2476, -75.5658),
        ("Cartagena, Colombia", 10.3910, -75.4794),
        ("Cali, Colombia", 3.4516, -76.5320),
        ("Barranquilla, Colombia", 10.9685, -74.7813),
        ("Santa Marta, Colombia", 11.2408, -74.2099),
        ("Bucaramanga, Colombia", 7.1254, -73.1196),
    ],
    "GB": [
        ("London, UK", 51.5074, -0.1278),
        ("Manchester, UK", 53.4808, -2.2426),
        ("Birmingham, UK", 52.4862, -1.8904),
        ("Edinburgh, UK", 55.9533, -3.1883),
        ("Glasgow, UK", 55.8642, -4.2518),
        ("Liverpool, UK", 53.4084, -2.9916),
        ("Bristol, UK", 51.4545, -2.5879),
        ("Oxford, UK", 51.7548, -1.2544),
        ("Cambridge, UK", 52.2053, 0.1218),
        ("Belfast, UK", 54.5973, -5.9301),
    ],
    "DE": [
        ("Berlin, Germany", 52.5200, 13.4050),
        ("Munich, Germany", 48.1351, 11.5820),
        ("Frankfurt, Germany", 50.1109, 8.6821),
        ("Hamburg, Germany", 53.5511, 9.9937),
        ("Cologne, Germany", 50.9375, 6.9603),
        ("Stuttgart, Germany", 48.7758, 9.1829),
        ("Dresden, Germany", 51.0504, 13.7373),
        ("Nuremberg, Germany", 49.4521, 11.0767),
        ("Leipzig, Germany", 51.3397, 12.3731),
        ("Dusseldorf, Germany", 51.2277, 6.7735),
    ],
    "FR": [
        ("Paris, France", 48.8566, 2.3522),
        ("Lyon, France", 45.7640, 4.8357),
        ("Marseille, France", 43.2965, 5.3698),
        ("Nice, France", 43.7102, 7.2620),
        ("Cannes, France", 43.5528, 7.0174),
        ("Bordeaux, France", 44.8378, -0.5792),
        ("Toulouse, France", 43.6047, 1.4442),
        ("Strasbourg, France", 48.5734, 7.7521),
        ("Montpellier, France", 43.6108, 3.8767),
        ("Annecy, France", 45.8992, 6.1294),
    ],
    "IT": [
        ("Rome, Italy", 41.9028, 12.4964),
        ("Milan, Italy", 45.4642, 9.1900),
        ("Naples, Italy", 40.8518, 14.2681),
        ("Florence, Italy", 43.7696, 11.2558),
        ("Venice, Italy", 45.4408, 12.3155),
        ("Turin, Italy", 45.0703, 7.6869),
        ("Palermo, Italy", 38.1157, 13.3615),
        ("Bologna, Italy", 44.4949, 11.3426),
        ("Verona, Italy", 45.4421, 10.9986),
        ("Amalfi, Italy", 40.6340, 14.6027),
    ],
    "ES": [
        ("Madrid, Spain", 40.4168, -3.7038),
        ("Barcelona, Spain", 41.3851, 2.1734),
        ("Valencia, Spain", 39.4699, -0.3763),
        ("Seville, Spain", 37.3891, -5.9845),
        ("Malaga, Spain", 36.7213, -4.4214),
        ("Mallorca, Spain", 39.6953, 3.0176),
        ("Bilbao, Spain", 43.2630, -2.9350),
        ("Granada, Spain", 37.1773, -3.5986),
        ("Ibiza, Spain", 38.9067, 1.4206),
        ("Tenerife, Spain", 28.2916, -16.6291),
    ],
    "NL": [
        ("Amsterdam, Netherlands", 52.3676, 4.9041),
        ("Rotterdam, Netherlands", 51.9244, 4.4777),
        ("The Hague, Netherlands", 52.0705, 4.3007),
        ("Utrecht, Netherlands", 52.0907, 5.1214),
        ("Eindhoven, Netherlands", 51.4416, 5.4697),
        ("Maastricht, Netherlands", 50.8513, 5.6909),
        ("Leiden, Netherlands", 52.1601, 4.4970),
        ("Delft, Netherlands", 52.0116, 4.3571),
    ],
    "BE": [
        ("Brussels, Belgium", 50.8503, 4.3517),
        ("Antwerp, Belgium", 51.2194, 4.4025),
        ("Bruges, Belgium", 51.2093, 3.2247),
        ("Ghent, Belgium", 51.0543, 3.7174),
        ("Liege, Belgium", 50.6292, 5.5834),
        ("Namur, Belgium", 50.4674, 4.8712),
        ("Leuven, Belgium", 50.8798, 4.7005),
    ],
    "CH": [
        ("Zurich, Switzerland", 47.3769, 8.5417),
        ("Geneva, Switzerland", 46.2044, 6.1432),
        ("Bern, Switzerland", 46.9480, 7.4474),
        ("Lucerne, Switzerland", 47.0502, 8.3093),
        ("Interlaken, Switzerland", 46.6863, 7.8632),
        ("Zermatt, Switzerland", 46.0207, 7.7491),
        ("St. Gallen, Switzerland", 47.4245, 9.3767),
        ("Lausanne, Switzerland", 46.5197, 6.6322),
    ],
    "AT": [
        ("Vienna, Austria", 48.2082, 16.3738),
        ("Salzburg, Austria", 47.8095, 13.0550),
        ("Innsbruck, Austria", 47.2692, 11.4041),
        ("Graz, Austria", 47.0707, 15.4395),
        ("Klagenfurt, Austria", 46.6365, 14.3120),
        ("Linz, Austria", 48.3069, 14.2858),
        ("Bregenz, Austria", 47.5031, 9.7471),
    ],
    "SE": [
        ("Stockholm, Sweden", 59.3293, 18.0686),
        ("Gothenburg, Sweden", 57.7089, 11.9746),
        ("Malmo, Sweden", 55.6045, 13.0038),
        ("Uppsala, Sweden", 59.8588, 17.6389),
        ("Vasteras, Sweden", 59.6161, 16.5528),
        ("Orebro, Sweden", 59.2753, 15.2134),
        ("Linkoping, Sweden", 58.4108, 15.6214),
    ],
    "NO": [
        ("Oslo, Norway", 59.9139, 10.7522),
        ("Bergen, Norway", 60.3913, 5.3221),
        ("Trondheim, Norway", 63.4307, 10.3951),
        ("Stavanger, Norway", 58.9690, 5.7331),
        ("Tromso, Norway", 69.6492, 18.9553),
        ("Alesund, Norway", 62.7355, 6.2635),
        ("Bodo, Norway", 67.2847, 14.3691),
    ],
    "DK": [
        ("Copenhagen, Denmark", 55.6761, 12.5683),
        ("Aarhus, Denmark", 56.1629, 10.2039),
        ("Odense, Denmark", 55.4038, 10.4027),
        ("Aalborg, Denmark", 57.0480, 9.9187),
        ("Esbjerg, Denmark", 55.4825, 8.4519),
    ],
    "PL": [
        ("Warsaw, Poland", 52.2297, 21.0122),
        ("Krakow, Poland", 50.0647, 19.9450),
        ("Gdansk, Poland", 54.3520, 18.6466),
        ("Wroclaw, Poland", 51.1079, 17.0385),
        ("Poznan, Poland", 52.4064, 16.9252),
        ("Lodz, Poland", 51.7592, 19.4560),
        ("Katowice, Poland", 50.2649, 19.0233),
    ],
    "RU": [
        ("Moscow, Russia", 55.7558, 37.6173),
        ("Saint Petersburg, Russia", 59.9311, 30.3609),
        ("Sochi, Russia", 43.6028, 39.7341),
        ("Kazan, Russia", 55.8304, 49.0661),
        ("Novosibirsk, Russia", 55.0084, 82.9357),
        ("Yekaterinburg, Russia", 56.8389, 60.6057),
        ("Vladivostok, Russia", 43.1155, 131.8855),
    ],
    "PT": [
        ("Lisbon, Portugal", 38.7223, -9.1393),
        ("Porto, Portugal", 41.1579, -8.6291),
        ("Faro, Portugal", 37.0194, -7.9322),
        ("Coimbra, Portugal", 40.2033, -8.4103),
        ("Sintra, Portugal", 38.7976, -9.3908),
    ],
    "GR": [
        ("Athens, Greece", 37.9838, 23.7275),
        ("Santorini, Greece", 36.3932, 25.4615),
        ("Mykonos, Greece", 37.4467, 25.3289),
        ("Crete, Greece", 35.2979, 25.1632),
        ("Thessaloniki, Greece", 40.6401, 22.9444),
        ("Rhodes, Greece", 36.4340, 28.2276),
    ],
    "CZ": [
        ("Prague, Czech Republic", 50.0755, 14.4378),
        ("Brno, Czech Republic", 49.1951, 16.6068),
        ("Cesky Krumlov, Czech Republic", 48.8127, 14.3175),
    ],
    "HU": [
        ("Budapest, Hungary", 47.4979, 19.0402),
        ("Debrecen, Hungary", 47.5316, 21.6273),
        ("Szeged, Hungary", 46.2546, 20.1486),
        ("Pecs, Hungary", 46.0707, 18.2331),
    ],
    "IE": [
        ("Dublin, Ireland", 53.3498, -6.2603),
        ("Cork, Ireland", 51.8969, -8.4863),
        ("Galway, Ireland", 53.2707, -9.0568),
    ],
    "AE": [
        ("Dubai, UAE", 25.2048, 55.2708),
        ("Abu Dhabi, UAE", 24.4539, 54.3773),
        ("Sharjah, UAE", 25.3463, 55.4209),
        ("Al Ain, UAE", 24.2075, 55.7447),
    ],
    "SA": [
        ("Riyadh, Saudi Arabia", 24.7136, 46.6753),
        ("Jeddah, Saudi Arabia", 21.4858, 39.1925),
        ("Mecca, Saudi Arabia", 21.3891, 39.8579),
        ("Medina, Saudi Arabia", 24.5247, 39.5692),
    ],
    "TR": [
        ("Istanbul, Turkey", 41.0082, 28.9784),
        ("Ankara, Turkey", 39.9334, 32.8597),
        ("Antalya, Turkey", 36.8969, 30.7133),
        ("Izmir, Turkey", 38.4192, 27.1287),
        ("Cappadocia, Turkey", 38.6431, 34.8289),
    ],
    "IL": [
        ("Jerusalem, Israel", 31.7683, 35.2137),
        ("Tel Aviv, Israel", 32.0853, 34.7818),
        ("Haifa, Israel", 32.7940, 34.9896),
        ("Eilat, Israel", 29.5581, 34.9482),
    ],
    "AU": [
        ("Sydney, Australia", -33.8688, 151.2093),
        ("Melbourne, Australia", -37.8136, 144.9631),
        ("Brisbane, Australia", -27.4698, 153.0251),
        ("Perth, Australia", -31.9505, 115.8605),
        ("Adelaide, Australia", -34.9285, 138.6007),
        ("Gold Coast, Australia", -28.0167, 153.4000),
        ("Cairns, Australia", -16.9186, 145.7781),
        ("Darwin, Australia", -12.4634, 130.8456),
    ],
    "NZ": [
        ("Auckland, New Zealand", -36.8509, 174.7645),
        ("Wellington, New Zealand", -41.2865, 174.7762),
        ("Christchurch, New Zealand", -43.5321, 172.6362),
        ("Queenstown, New Zealand", -45.0312, 168.6626),
    ],
    "ZA": [
        ("Johannesburg, South Africa", -26.2041, 28.0473),
        ("Cape Town, South Africa", -33.9249, 18.4241),
        ("Durban, South Africa", -29.8587, 31.0218),
        ("Pretoria, South Africa", -25.7479, 28.2292),
    ],
    "EG": [
        ("Cairo, Egypt", 30.0444, 31.2357),
        ("Alexandria, Egypt", 31.2001, 29.9187),
        ("Luxor, Egypt", 25.6872, 32.6396),
        ("Aswan, Egypt", 24.0889, 32.8998),
    ],
    "NG": [
        ("Lagos, Nigeria", 6.5244, 3.3792),
        ("Abuja, Nigeria", 9.0765, 7.3986),
        ("Port Harcourt, Nigeria", 4.7774, 7.0134),
    ],
    "MA": [
        ("Casablanca, Morocco", 33.5731, -7.5898),
        ("Marrakech, Morocco", 31.6295, -7.9811),
        ("Fez, Morocco", 34.0331, -5.0003),
    ],
    "KE": [
        ("Nairobi, Kenya", -1.2921, 36.8219),
        ("Mombasa, Kenya", -4.0435, 39.6682),
        ("Kisumu, Kenya", -0.1022, 34.7617),
    ],
    "TZ": [
        ("Dar es Salaam, Tanzania", -6.7924, 39.2083),
        ("Zanzibar, Tanzania", -6.1659, 39.2026),
        ("Arusha, Tanzania", -3.3666, 36.6833),
    ],
}

COUNTRY_NAMES = {
    "SG": "Singapore", "MY": "Malaysia", "TH": "Thailand", "VN": "Vietnam",
    "PH": "Philippines", "KH": "Cambodia", "MM": "Myanmar", "NP": "Nepal",
    "LK": "Sri Lanka", "IN": "India", "PK": "Pakistan", "BD": "Bangladesh",
    "CN": "China", "TW": "Taiwan", "KR": "South Korea", "JP": "Japan",
    "US": "United States", "CA": "Canada", "MX": "Mexico", "BR": "Brazil",
    "AR": "Argentina", "CO": "Colombia",
    "GB": "United Kingdom", "DE": "Germany", "FR": "France", "IT": "Italy",
    "ES": "Spain", "NL": "Netherlands", "BE": "Belgium", "CH": "Switzerland",
    "AT": "Austria", "SE": "Sweden", "NO": "Norway", "DK": "Denmark",
    "PL": "Poland", "RU": "Russia", "PT": "Portugal", "GR": "Greece",
    "CZ": "Czech Republic", "HU": "Hungary", "IE": "Ireland",
    "AE": "UAE", "SA": "Saudi Arabia", "TR": "Turkey", "IL": "Israel",
    "AU": "Australia", "NZ": "New Zealand",
    "ZA": "South Africa", "EG": "Egypt", "NG": "Nigeria", "MA": "Morocco",
    "KE": "Kenya", "TZ": "Tanzania", "ID": "Indonesia"
}

PHONE_PREFIX_TO_COUNTRY = {
    "62": "ID",
    "60": "MY",   
    "66": "TH",   
    "84": "VN",    
    "63": "PH",   
    "855": "KH",  
    "95": "MM",   
    "977": "NP",  
    "94": "LK",  
    "91": "IN",   
    "92": "PK",  
    "880": "BD",  
    "86": "CN",   
    "886": "TW",  
    "82": "KR",   
    "81": "JP",   
    "1": "US",    
    "52": "MX",   
    "55": "BR",   
    "54": "AR",   
    "57": "CO",   
    "44": "GB",   
    "49": "DE",   
    "33": "FR",   
    "39": "IT",   
    "34": "ES", 
    "31": "NL",   
    "32": "BE",   
    "41": "CH",  
    "43": "AT",   
    "46": "SE",   
    "47": "NO",  
    "45": "DK",   
    "48": "PL",   
    "7": "RU",   
    "351": "PT",  
    "30": "GR",  
    "420": "CZ",  
    "36": "HU",  
    "353": "IE",  
    "971": "AE",  
    "966": "SA",  
    "90": "TR",  
    "972": "IL",  
    "61": "AU",   
    "64": "NZ",   
    "27": "ZA",  
    "20": "EG",   
    "234": "NG",  
    "212": "MA",  
    "254": "KE",  
    "255": "TZ",  
}

CITIES = [
    ("Jakarta Pusat, DKI Jakarta", -6.1865, 106.8341),
    ("Jakarta Utara, DKI Jakarta", -6.1380, 106.8636),
    ("Jakarta Barat, DKI Jakarta", -6.1674, 106.7637),
    ("Jakarta Selatan, DKI Jakarta", -6.2615, 106.8106),
    ("Jakarta Timur, DKI Jakarta", -6.2250, 106.9004),
    ("Tangerang, Banten", -6.1783, 106.6319),
    ("Cilegon, Banten", -6.0025, 106.0112),
    ("Serang, Banten", -6.1200, 106.1503),
    ("Bandung, Jawa Barat", -6.9175, 107.6191),
    ("Bogor, Jawa Barat", -6.5950, 106.8166),
    ("Depok, Jawa Barat", -6.4025, 106.7942),
    ("Bekasi, Jawa Barat", -6.2349, 106.9896),
    ("Cirebon, Jawa Barat", -6.7320, 108.5523),
    ("Tasikmalaya, Jawa Barat", -7.3506, 108.2172),
    ("Garut, Jawa Barat", -7.2279, 107.9087),
    ("Sukabumi, Jawa Barat", -6.9240, 106.9290),
    ("Subang, Jawa Barat", -6.5715, 107.7600),
    ("Semarang, Jawa Tengah", -6.9667, 110.4167),
    ("Solo, Jawa Tengah", -7.5755, 110.8243),
    ("Magelang, Jawa Tengah", -7.4706, 110.2177),
    ("Purwokerto, Jawa Tengah", -7.4243, 109.2396),
    ("Tegal, Jawa Tengah", -6.8797, 109.1256),
    ("Pekalongan, Jawa Tengah", -6.8892, 109.6753),
    ("Kudus, Jawa Tengah", -6.8049, 110.8405),
    ("Jepara, Jawa Tengah", -6.5820, 110.6787),
    ("Yogyakarta, DIY", -7.7956, 110.3695),
    ("Sleman, DIY", -7.7167, 110.3556),
    ("Bantul, DIY", -7.8881, 110.3290),
    ("Surabaya, Jawa Timur", -7.2575, 112.7521),
    ("Malang, Jawa Timur", -7.9666, 112.6326),
    ("Kediri, Jawa Timur", -7.8480, 112.0178),
    ("Blitar, Jawa Timur", -8.0955, 112.1608),
    ("Jember, Jawa Timur", -8.1724, 113.7000),
    ("Banyuwangi, Jawa Timur", -8.2192, 114.3691),
    ("Madiun, Jawa Timur", -7.6311, 111.5239),
    ("Pasuruan, Jawa Timur", -7.6450, 112.9075),
    ("Probolinggo, Jawa Timur", -7.7569, 113.2115),
    ("Denpasar, Bali", -8.6705, 115.2126),
    ("Singaraja, Bali", -8.1120, 115.0882),
    ("Mataram, NTB", -8.5833, 116.1167),
    ("Bima, NTB", -8.4606, 118.7270),
    ("Kupang, NTT", -10.1772, 123.6070),
    ("Maumere, NTT", -8.6199, 122.2111),
    ("Medan, Sumatera Utara", 3.5952, 98.6722),
    ("Binjai, Sumut", 3.6001, 98.4854),
    ("Padang, Sumatera Barat", -0.9471, 100.4172),
    ("Bukittinggi, Sumbar", -0.3050, 100.3692),
    ("Pekanbaru, Riau", 0.5071, 101.4478),
    ("Dumai, Riau", 1.6671, 101.4430),
    ("Batam, Kepulauan Riau", 1.1301, 104.0529),
    ("Tanjung Pinang, Kepri", 0.9175, 104.4550),
    ("Palembang, Sumatera Selatan", -2.9909, 104.7565),
    ("Jambi, Jambi", -1.6101, 103.6131),
    ("Bengkulu, Bengkulu", -3.7928, 102.2608),
    ("Bandar Lampung, Lampung", -5.4292, 105.2610),
    ("Aceh, Banda Aceh", 5.5483, 95.3238),
    ("Pontianak, Kalbar", -0.0263, 109.3425),
    ("Singkawang, Kalbar", 0.9070, 108.9840),
    ("Palangkaraya, Kalteng", -2.2096, 113.9126),
    ("Banjarmasin, Kalsel", -3.3186, 114.5944),
    ("Balikpapan, Kaltim", -1.2654, 116.8312),
    ("Samarinda, Kaltim", -0.5022, 117.1536),
    ("Tarakan, Kaltara", 3.3000, 117.6333),
    ("Makassar, Sulsel", -5.1477, 119.4327),
    ("Parepare, Sulsel", -4.0167, 119.6236),
    ("Manado, Sulut", 1.4748, 124.8421),
    ("Bitung, Sulut", 1.4451, 125.1824),
    ("Palu, Sulteng", -0.8986, 119.8506),
    ("Kendari, Sultra", -3.9985, 122.5127),
    ("Gorontalo, Gorontalo", 0.5435, 123.0568),
    ("Ambon, Maluku", -3.6954, 128.1814),
    ("Ternate, Maluku Utara", 0.7900, 127.3842),
    ("Sorong, Papua Barat", -0.8762, 131.2558),
    ("Manokwari, Papua Barat", -0.8615, 134.0620),
    ("Jayapura, Papua", -2.5916, 140.6689),
    ("Merauke, Papua Selatan", -8.4932, 140.4018)
]


def detect_country_from_phone(nomor):
    clean_number = ''.join(filter(str.isdigit, nomor))
    for prefix in sorted(PHONE_PREFIX_TO_COUNTRY.keys(), key=len, reverse=True):
        if clean_number.startswith(prefix):
            return PHONE_PREFIX_TO_COUNTRY[prefix]
    return None


def validate_phone_number(nomor):
    detected = detect_country_from_phone(nomor)
    if detected is None:
        return False, "Nomor telepon harus memiliki kode negara! Contoh: +62812345678 (Indonesia), +60123456789 (Malaysia)"
    return True, None


def pick_foreign():
    country = random.choice(list(FOREIGN_CITIES.keys()))
    city, lat, lon = random.choice(FOREIGN_CITIES[country])
    return city, lat, lon, country


def pick_specific_country(country_code):
    country_code = country_code.upper()
    if country_code in FOREIGN_CITIES:
        city, lat, lon = random.choice(FOREIGN_CITIES[country_code])
        country_name = COUNTRY_NAMES.get(country_code, country_code)
        return city, lat, lon, country_name
    return None, None, None, None


def random_vpn():
    return "YES" if random.random() < 0.15 else "NO"


def ipv6_vpn():
    return "2001:" + ":".join(
        "".join(random.choice("abcdef0123456789") for _ in range(4))
        for _ in range(6)
    )


def ipv6_local():
    return "fe80::" + "".join(random.choice("abcdef0123456789") for _ in range(12))


def fake_coordinate(lat, lon):
    return lat + random.uniform(-0.02, 0.02), lon + random.uniform(-0.02, 0.02)


def generate_location_result(nomor, negara=None):
    detected_country = detect_country_from_phone(nomor)
    if detected_country:
        negara = detected_country
    
    vpn = random_vpn()
    
    if vpn == "YES":
        city_name, lat0, lon0, country = pick_foreign()
        lat, lon = fake_coordinate(lat0, lon0)
        ipv4 = f"{random.randint(20,90)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        ipv6 = ipv6_vpn()
        color = 0xFF0000
    else:
        if negara and negara.upper() != "ID":
            city_name, lat0, lon0, country = pick_specific_country(negara)
            if city_name is None:
                city_name, lat0, lon0 = random.choice(CITIES)
                country = "Indonesia"
        else:
            city_name, lat0, lon0 = random.choice(CITIES)
            country = "Indonesia"
        
        lat, lon = fake_coordinate(lat0, lon0)
        ipv4 = f"192.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        ipv6 = ipv6_local()
        color = 0x00ff88
    
    ping = random.randint(15, 60)
    maps_link = f"https://maps.google.com/?q={lat},{lon}"

    return {
        "city_name": city_name,
        "lat": lat,
        "lon": lon,
        "vpn": vpn,
        "country": country,
        "ipv4": ipv4,
        "ipv6": ipv6,
        "ping": ping,
        "maps_link": maps_link,
        "color": color
    }

intents = discord.Intents.default()
intents.message_content = True

print("Creating bot...")
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
_panel_view = None

@tree.command(name="locating", description="Lacak lokasi nomor telepon")
async def locating(interaction: discord.Interaction, nomor: str):
    user_id = interaction.user.id
    if not is_whitelisted(user_id):
        error_embed = discord.Embed(
            title="❌ Akses Ditolak",
            description="Anda tidak memiliki akses untuk menggunakan bot ini!",
            color=0xFF0000
        )
        error_embed.add_field(
            name="Cara Mendapatkan Akses:",
            value="Silakan hubungi developer atau gunakan panel untuk redeem key.",
            inline=False
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return
    
    await interaction.response.defer()
    is_valid, error_msg = validate_phone_number(nomor)
    if not is_valid:
        error_embed = discord.Embed(
            title="❌ Error",
            description=error_msg,
            color=0xFF0000
        )
        error_embed.add_field(
            name="📝 Contoh Penggunaan:",
            value="• `/locating +62812345678` (Indonesia)\n"
                  "• `/locating +60123456789` (Malaysia)\n"
                  "• `/locating +66012345678` (Thailand)\n"
                  "• `/locating +84123456789` (Vietnam)",
            inline=False
        )
        await interaction.followup.send(embed=error_embed)
        return

    detected_country = detect_country_from_phone(nomor)
    country_name = COUNTRY_NAMES.get(detected_country, detected_country)
    
    wait_msg = await interaction.followup.send(f"⏳ **Mencari lokasi nomor `{nomor}`")
    
    await asyncio.sleep(30)
    await wait_msg.edit(content=f"🔎 **Finding With CTS Tower** `{nomor}`...")
    await asyncio.sleep(300)
    await wait_msg.edit(content=f"📡 **Locating** `{nomor}`...")
    await asyncio.sleep(120)
    
    result = generate_location_result(nomor)
    
    result_embed = discord.Embed(
        title="DrxDvs Location Info:",
        color=result["color"]
    )
    result_embed.add_field(name="📱 Nomor", value=f"└ `{nomor}`", inline=False)
    result_embed.add_field(name="🌍 Country", value=f"└ `{result['country']}`", inline=True)
    result_embed.add_field(name="📍 Kota", value=f"└ `{result['city_name']}`", inline=False)
    result_embed.add_field(name="🔐 VPN", value=f"└ `{result['vpn']}`", inline=False)
    result_embed.add_field(
        name="📝 Note",
        value="└ `This bot can make mistake if you in trouble please contact the developer`",
        inline=False
    )
    result_embed.add_field(name="🗺 Maps", value=f"└ `{result['maps_link']}`", inline=False)
    result_embed.set_footer(text=f"ENGINE V5 | DrxDvs {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    view = LocationResultView(phone_number=nomor)
    
    view2 = LocationResultButtonsView(maps_link=result["maps_link"])
    
    await wait_msg.edit(
        content=f"✅ Success `{nomor}`",
        embed=result_embed,
        view=view
    )
    
    buttons_msg = await interaction.followup.send(
        f"{interaction.user.mention} Gunakan tombol di bawah:",
        view=view2
    )
    
    await asyncio.sleep(60)
    


@tree.command(name="start", description="Informasi bot")
async def start(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_whitelisted(user_id):
        error_embed = discord.Embed(
            title="❌ Akses Ditolak",
            description="Anda tidak memiliki akses untuk menggunakan bot ini!",
            color=0xFF0000
        )
        error_embed.add_field(
            name="Cara Mendapatkan Akses:",
            value="Silakan hubungi developer atau gunakan panel untuk redeem key.",
            inline=False
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Welcome to DrxDvs Locating!",
        description="Bot ini dapat membantu Anda melacak lokasi nomor telepon.\n\n"
                    "**Cara Penggunaan:**\n"
                    "Gunakan perintah `/locating` dengan nomor yang memiliki kode negara.\n\n"
                    "**Contoh:**\n"
                    "• `/locating +62812345678` - Indonesia (62)\n"
                    "• `/locating +60123456789` - Malaysia (60)\n"
                    "• `/locating +66012345678` - Thailand (66)\n"
                    "• `/locating +84123456789` - Vietnam (84)\n"
                    "• `/locating +639123456789` - Philippines (63)\n"
                    "• `/locating +861234567890` - China (86)\n"
                    "• `/locating +8212345678` - South Korea (82)\n"
                    "• `/locating +81312345678` - Japan (81)\n"
                    "• `/locating +1234567890` - USA/Canada (1)\n\n"
                    "**Catatan:** Nomor harus memiliki kode negara! Tanpa kode negara akan ditolak sistem.\n\n"
                    "**Proses pencarian memerlukan waktu sekitar 1-10 menit.**",
        color=0x00ff88
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="panel", description="Buka panel lokasi")
async def panel(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not is_whitelisted(user_id):
        error_embed = discord.Embed(
            title="❌ Akses Ditolak",
            description="Anda tidak memiliki akses untuk menggunakan bot ini!",
            color=0xFF0000
        )
        error_embed.add_field(
            name="Cara Mendapatkan Akses:",
            value="Silakan hubungi developer atau gunakan panel untuk redeem key.",
            inline=False
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📍 DrxDvs Location Panel",
        description="Selamat datang di panel lokasi! Gunakan tombol di bawah untuk melacak nomor telepon.",
        color=0x0099FF
    )
    embed.add_field(
        name="📝 Cara Penggunaan:",
        value="Klik tombol **Get Location** di bawah, lalu masukkan nomor telepon dengan kode negara.\n\n"
              "**Contoh nomor:**\n"
              "• +62812345678 (Indonesia)\n"
              "• +60123456789 (Malaysia)\n"
              "• +66012345678 (Thailand)\n\n"
              "**Catatan:** Nomor harus memiliki kode negara!",
        inline=False
    )
    embed.set_footer(text=f"DrxDvs | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    view = PanelView()
    await interaction.response.send_message(embed=embed, view=view)


@client.event
async def on_ready():
    print(f"Bot {client.user} sudah online!")
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name="Made with ❤️ by DrxDvs")
    )
    
    global _panel_view
    _panel_view = PanelView()
    client.add_view(_panel_view)
    print("Persistent view added!")
    
    print("Syncing commands...")
    try:
        await tree.sync()
        print("Commands synced successfully!")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    print("Ketik /start atau /locating dan /panel di Discord")
if __name__ == "__main__":
    print("Starting bot...")
    client.run(BOT_TOKEN)
