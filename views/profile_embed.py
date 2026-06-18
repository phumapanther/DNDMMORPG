# profile_embed.py
import discord

# ─── 🧬 คลังข้อมูลเผ่าพันธุ์ (สลักชื่อตรงตามยศในเซิร์ฟเวอร์ดิสคอร์ด 100%) ───
GAME_RACES = [
    "、👲🏻 • มนุษย์",
    "、 🧝🏻‍♂️ • เอลฟ์",
    "、👹 • ยักษ์",     
    "、🚶🏽 • คนแคระ",
    "、🐉 • มังกร",
    "、🧚 • ภูติ",
    "、🧜🏼‍♀️ • เงือก",
    "、🐾 • เผ่ามิ้ง"
]

# 👹 คลังยศฝ่ายปีศาจ/มอนสเตอร์ (อ้างอิงตรงตามยศในเซิร์ฟเวอร์ดิสคอร์ด 100%)
MONSTER_RACES = [
    "• Dragon 🐉",
    "• Unicon 🦄",
    "•  Slime 🪼⋆",
    "• Ogre 👹",
    "• Orc 🧌",
    "• Goblins🧝",
    "• Lich 🧙🏽‍♂️",
    "•  Skeleton 🦴",
    "•  Zombie🧟"
]

GAME_CLASSES = ["Warrior", "Mage", "Rogue", "Cleric"]

TEAMWORK_CLASSES = ["꒰ PL ꒱ อัศวิน ⚔️", "꒰ DT ꒱ นักบวช .⋆♱", "꒰ PR ꒱ ผู้ส่งสาร", "꒰ EN ꒱ นักกวี 𝄞⋆"]
# บัพพาสซีพทีมงาน 
# อัศวิน ลูกเต่าเพิ่ม 2 ลูก 
# นักบวช เลอดต่ำกว่า 50 % เพิ่มเลือด 25%
# ผู้ส่งสาร เพิ่มโอกาสหลบหลีก 15% และเพิ่ม gold ที่ได้รับจากการพิมแชท 100%
# นักกวี เพิ่มโอกาสหลบหลีก 15% และเพิ่ม EXP ที่ได้รับจากการพูดคุยในห้องเสียงอีก 100%

CLASS_SKILLS = {
    "Warrior": ["🛡️ Shield Bash", "⚔️ Heavy Strike"],
    "Mage": ["🔥 Fireball", "❄️ Frostbolt"],
    "Rogue": ["🗡️ Backstab", "💨 Evasion"],
    "Cleric": ["✨ Heal", "🛡️ Holy Aura"],
    "Unknown": ["❓ ไม่มีสกิล (กรุณารับยศคลาสอาชีพก่อน)"]
}

# ข้อมูลเกราะ (เพิ่ม Visibility และ Max Durability)
ARMOR_STATS = {
    "None":      {"name": "👕 เสื้อผ้าธรรมดา", "hp": 0,   "eva": 85, "dur": 100, "vis": 1},
    "Leather_L": {"name": "🟫 เกราะหนังเบา",   "hp": 20,  "eva": 70, "dur": 150, "vis": 3},
    "Leather_H": {"name": "🟫 เกราะหนังหนัก",  "hp": 30,  "eva": 60, "dur": 200, "vis": 5},
    "Steel_L":   {"name": "⬜ เกราะเหล็กเบา",  "hp": 50,  "eva": 40, "dur": 300, "vis": 7},
    "Steel_H":   {"name": "⬜ เกราะเหล็กหนัก", "hp": 100, "eva": 20, "dur": 500, "vis": 9}
}

# ข้อมูลอาวุธ
WEAPON_STATS = {
    "Wooden_Weapon": {"name": "🪵 อาวุธไม้",     "atk": 10, "dur": 50},
    "Iron_Weapon":   {"name": "⚔️ อาวุธเหล็ก",   "atk": 30, "dur": 150},
    "Legen_Weapon":  {"name": "🗡️ อาวุธในตำนาน", "atk": 60, "dur": 300}
}

ITEM_CONFIG = {
    "1": {"name": "🧪 ยาฮีล", "buy": 500, "sell": 250},
    "2": {"name": "🛠️ ใบซ่อมแซม", "buy": 800, "sell": 400}
}

def create_profile_embed(target_member, player_data):
    player_level = player_data.get("level", 1)
    rank = player_data.get("rank", "None")
    
    # 🛡️ ดึงข้อมูลอุปกรณ์
    armor_key = player_data.get("armor", "None")
    weapon_key = player_data.get("weapon", "Wooden_Weapon")
    
    # ตรวจสอบความถูกต้องของ Key
    armor_info = ARMOR_STATS.get(armor_key, ARMOR_STATS["None"])
    weapon_info = WEAPON_STATS.get(weapon_key, WEAPON_STATS["Wooden_Weapon"])
    
    # คำนวณ HP รวม (ใช้ค่า 'hp' จากตารางใหม่)
    total_max_hp = player_data.get("max_hp", 100)
    current_hp = min(player_data.get("hp", 100), total_max_hp)

    detected_race = "ไม่ระบุเผ่า"
    detected_class = "ไม่ระบุอาชีพ"
    player_faction = "⏳ กำลังระบุฝ่าย"
    
    # ➕ เพิ่มตัวแปรสำหรับเก็บรายชื่อเผ่าที่เจอ และตัวนับจำนวนเผ่า
    found_races = []

    # 🔍 ลูปเช็กยศของสมาชิกเพื่อระบุ เผ่าพันธุ์, อาชีพ และ ฝ่าย สังกัด
    for role in target_member.roles:
        if role.name in GAME_RACES:
            found_races.append(role.name)
            # เซ็ตค่าเริ่มต้นกรณีเจอเผ่าเดียวก่อน
            if len(found_races) == 1:
                detected_race = role.name
                player_faction = "🔵 ฝ่ายมนุษย์"
        elif role.name in MONSTER_RACES:
            found_races.append(role.name)
            # เซ็ตค่าเริ่มต้นกรณีเจอเผ่าเดียวก่อน
            if len(found_races) == 1:
                detected_race = role.name
                player_faction = "🔴 ฝ่ายปีศาจ"
        elif role.name in GAME_CLASSES:
            detected_class = role.name

    # 🧬 [ระบบคำนวณลูกผสม] ถ้าเช็กแล้วพบว่ามียศเผ่าพันธุ์รวมกันตั้งแต่ 2 เผ่าขึ้นไป
    if len(found_races) >= 2:
        # ดึงเฉพาะชื่อสั้นมาโชว์คู่กัน เช่น เอลฟ์ + Slime
        short_names = [r.replace("、", "").replace("•", "").strip() for r in found_races]
        detected_race = f"ลูกผสม ({' + '.join(short_names)})"
        player_faction = "🟣 ฝ่ายอิสระ (ลูกผสม)"

    skills = CLASS_SKILLS.get(detected_class, CLASS_SKILLS["Unknown"])
    skills_text = "\n".join(skills)

    embed = discord.Embed(title=f"👤 ข้อมูลตัวละคร: {target_member.display_name}", color=0x9b59b6)
    embed.set_thumbnail(url=target_member.display_avatar.url)
    
    # 📊 สเตตัสหลัก
    embed.add_field(name="🎯 เลเวล", value=f"⭐ Lv. {player_level} ({rank})", inline=True)
    embed.add_field(name="🩸 พลังชีวิตรวม", value=f"❤️ {current_hp}/{total_max_hp} *(+{armor_info['hp']})*", inline=True)
    embed.add_field(name="💰 เงินสด", value=f"🪙 {player_data.get('cash', 0)} ทอง", inline=True)
    
    # 🧬 เผ่าพันธุ์ & อาชีพ
    embed.add_field(name="🧬 เผ่าพันธุ์", value=f"🟢 {detected_race}\n\n\n\n👑 **{player_faction}**", inline=True)
    embed.add_field(name="⚔️ คลาสอาชีพ", value=f"🔵 {detected_class}", inline=True)
    embed.add_field(name="​", value="​", inline=False) 

    # 🛡️ อุปกรณ์ & ความทนทาน (เพิ่มอาวุธและความทนทาน)
    embed.add_field(name="⚔️ อาวุธที่ถือ", value=f"**{weapon_info['name']}**\nความทนทาน: `{player_data.get('weapon_dur', 0)}/{weapon_info['dur']}`", inline=True)
    embed.add_field(name="🛡️ เกราะที่สวม", value=f"**{armor_info['name']}**\nความทนทาน: `{player_data.get('armor_dur', 0)}/{armor_info['dur']}`", inline=True)
    
    # 💨 สถานะการป้องกัน/การซ่อนตัว
    embed.add_field(name="💨 หลบหลีก / 👁️ มองเห็น", value=f"🏃 {armor_info['eva']}% / ⚠️ ระดับ: {armor_info['vis']}", inline=False)
    
    # 🔥 สกิล
    embed.add_field(name="🔥 สกิลประจำคลาส", value=f"```\n{skills_text}\n```", inline=False)
    
    return embed
    
    return embed