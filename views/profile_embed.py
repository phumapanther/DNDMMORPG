import discord

GAME_RACES = ["Human", "Elf", "Orc", "Dwarf", "Demon"]
GAME_CLASSES = ["Warrior", "Mage", "Rogue", "Cleric"]

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
    if current_armor_key not in ARMOR_STATS: current_armor_key = "None"
    
    armor_info = ARMOR_STATS[current_armor_key]
    total_max_hp = player_data["max_hp"] + armor_info["hp_bonus"]
    current_hp = min(player_data["hp"], total_max_hp)

    detected_race = "ไม่ระบุเผ่า"
    detected_class = "ไม่ระบุอาชีพ"
    for role in target_member.roles:
        if role.name in GAME_RACES: detected_race = role.name
        elif role.name in GAME_CLASSES: detected_class = role.name

    skills = CLASS_SKILLS.get(detected_class, CLASS_SKILLS["Unknown"])
    skills_text = "\n".join(skills)

    embed = discord.Embed(title=f"👤 ข้อมูลตัวละคร: {target_member.display_name}", color=0x9b59b6)
    embed.set_thumbnail(url=target_member.display_avatar.url)
    
    embed.add_field(name="🎯 เลเวล", value=f"⭐ Lv. {player_level}", inline=True)
    embed.add_field(name="🩸 พลังชีวิตรวม", value=f"❤️ {current_hp}/{total_max_hp} *(+{armor_info['hp_bonus']})*", inline=False)
    embed.add_field(name="💰 เงินสดกลาง", value=f"🪙 {player_data['cash']} ทอง", inline=True)
    embed.add_field(name="🧬 เผ่าพันธุ์", value=f"🟢 {detected_race}", inline=True)
    embed.add_field(name="⚔️ คลาสอาชีพ", value=f"🔵 {detected_class}", inline=True)
    embed.add_field(name="🛡️ ชุดเกราะที่สวมใส่", value=f"**{armor_info['name']}**", inline=False)
    embed.add_field(name="💨 อัตราการหลบหนี", value=f"🏃 {armor_info['evasion']}%", inline=True)
    embed.add_field(name="👁️ มอนสเตอร์มองเห็น", value=f"⚠️ ระดับ: {armor_info['visibility']}", inline=True)
    embed.add_field(name="🔥 สกิลประจำคลาส", value=f"```\n{skills_text}\n```", inline=False)
    
    return embed