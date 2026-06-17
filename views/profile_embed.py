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

ARMOR_STATS = {
    "None":        {"name": "👕 เสื้อผ้าธรรมดา", "hp_bonus": 0,   "evasion": 85, "visibility": "ต่ำ"},
    "Leather_L":   {"name": "🟫 เกราะหนังเบา",   "hp_bonus": 20,  "evasion": 70,  "visibility": "ปานกลาง-ต่ำ"},
    "Leather_H":   {"name": "🟫 เกราะหนังหนัก",  "hp_bonus": 30,  "evasion": 60,  "visibility": "ปานกลาง"},
    "Steel_L":     {"name": "⬜ เกราะเหล็กเบา",   "hp_bonus": 50,  "evasion": 40,  "visibility": "ปานกลาง-สูง"},
    "Steel_H":     {"name": "⬜ เกราะเหล็กหนัก",  "hp_bonus": 100, "evasion": 20,  "visibility": "สูงมาก"}
}

def create_profile_embed(target_member, player_data):
    player_level = player_data.get("level", 1)
    current_armor_key = player_data.get("armor", "None")
    rank = player_data.get("rank", "None")
    if current_armor_key not in ARMOR_STATS: current_armor_key = "None"
    
    armor_info = ARMOR_STATS[current_armor_key]
    total_max_hp = player_data["max_hp"] + armor_info["hp_bonus"]
    current_hp = min(player_data["hp"], total_max_hp)

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
    
    # 📊 [โซนสเตตัสหลัก]
    embed.add_field(name="🎯 เลเวล", value=f"⭐ Lv. {player_level} (Rack : {rank})", inline=True)
    embed.add_field(name="🩸 พลังชีวิตรวม", value=f"❤️ {current_hp}/{total_max_hp} *(+{armor_info['hp_bonus']})*", inline=False)
    embed.add_field(name="💰 เงินสดกลาง", value=f"🪙 {player_data['cash']} ทอง", inline=True)
    

    # 🧬 [โซนเผ่าพันธุ์ & อาชีพ]
    embed.add_field(name="🧬 เผ่าพันธุ์ (สังกัด)", value=f"🟢 {detected_race}\n\n\n👑 **{player_faction}**", inline=True)
    embed.add_field(name="⚔️ คลาสอาชีพ", value=f"🔵 {detected_class}", inline=True)
    
    # 🌌 [ย้ายมาตรงนี้!] สั่งเว้นบรรทัดตัดลงมาด้านล่าง ใต้เผ่าพันธุ์และอาชีพทันที
    embed.add_field(name="​", value="​", inline=False) 

    # 🛡️ [โซนอุปกรณ์ & สกิล]
    embed.add_field(name="🛡️ ชุดเกราะที่สวมใส่", value=f"**{armor_info['name']}**", inline=False)
    embed.add_field(name="💨 อัตราการหลบหนี", value=f"🏃 {armor_info['evasion']}%", inline=True)
    embed.add_field(name="👁️ มอนสเตอร์มองเห็น", value=f"⚠️ ระดับ: {armor_info['visibility']}", inline=True)
    embed.add_field(name="🔥 สกิลประจำคลาส", value=f"```\n{skills_text}\n```", inline=False)
    
    return embed