import discord
from discord.ui import View
import random
import models.player_model as player_model
from views.profile_embed import ARMOR_STATS, GAME_CLASSES ,WEAPON_STATS,ITEM_CONFIG

# ==========================================================
# 📊 [SKILL BALANCE CONFIG] คลังศูนย์กลางคุมบาลานซ์สกิลแบบละเอียด 100%
# ==========================================================
SKILL_CONFIG = {
    "Warrior": {
        "heavy_strike": {
            "chance_base": 80,          # โอกาสติดพื้นฐาน (%)
            "chance_lvl_scale": 1,      # โอกาสติดเพิ่มขึ้นต่อเลเวล (เช่น +1% ต่อ 1 เลเวล)
            "damage_multiplier": 2      # ตัวคูณความเสียหายเมื่อสำเร็จ
        },
        "shield_bash": {
            "duration": 3,              # ระยะเวลาติดสถานะ (เทิร์น)
            "reduction_base": 0.50,     # อัตราลดดาเมจพื้นฐาน (50%)
            "reduction_lvl_scale": 0.005 # อัตราลดดาเมจเพิ่มขึ้นต่อเลเวล (+0.5% ต่อ 1 เลเวล)
        }
    },
    "Mage": {
        "fireball": {
            "duration": 2,              # ระยะเวลาติดไฟ (เทิร์น)
            "burn_base": 0.05,          # พลังเผาไหม้พื้นฐานอิงตาม HP บอส (5%)
            "burn_lvl_scale": 0.002     # พลังเผาเพิ่มขึ้นต่อเลเวล (+0.2% ต่อ 1 เลเวล)
        },
        "frostbolt": {
            "duration_base": 1,         # ระยะเวลาแช่แข็งพื้นฐาน (เทิร์น)
            "duration_lvl_scale": 0.05,  # ระยะเวลาแช่แข็งเพิ่มขึ้นต่อเลเวล (เช่น ทุก 20 เลเวลเพิ่ม 1 เทิร์น)
            "damage_reduce": 0.75       # อัตราหักล้างดาเมจของบอส (75%)
        }
    },
    "Rogue": {
        "backstab": {
            "chance_base": 50,          # โอกาสติดพื้นฐาน (%)
            "chance_lvl_scale": 0.5,      # โอกาสติดเพิ่มขึ้นต่อเลเวล (+0.5% ต่อ 1 เลเวล)
            "damage_reflect_mult": 1.5  # ตัวคูณดาเมจคริติคอลสะท้อนสวนกลับบอส
        },
        "evasion": {
            "chance_base": 100,          # โอกาสวิ่งหนีสำเร็จพื้นฐาน (%)
            "chance_lvl_scale": 0.0       # โอกาสวิ่งหนีสำเร็จเพิ่มขึ้นต่อเลเวล (+0.5% ต่อ 1 เลเวล)
        }
    },
    "Cleric": {
        "heal": {
            "heal_percent_base": 0.40,  # อัตราฮีลพื้นฐานอิงจาก Max HP (40%)
            "heal_lvl_scale": 0.01      # อัตราฮีลเพิ่มขึ้นต่อเลเวล (+1% ต่อ 1 เลเวล)
        },
        "holy_aura": {
            "chance_base": 50,          # โอกาสบล็อกดาเมจเป็น 0 พืนฐาน (%)
            "chance_lvl_scale": 1       # โอกาสบล็อกดาเมจเพิ่มขึ้นต่อเลเวล (+1% ต่อ 1 เลเวล)
        }
    }
}

# ตารางสัดส่วนน้ำหนักเหตุการณ์ (อ้างอิงจาก last_event)
EVENT_WEIGHTS = {
    "village":            [2,   0,        3,      1,       90,       4],
    "dungeon_inside":     [45,  5,        35,     0,       5,        10],
    "monster":            [25,  25,       20,     10,      10,       10],
    "treasure":           [30,  20,       10,     15,      15,       10],
    "npc":                [20,  40,       15,     10,      5,        10],
    "trap":               [35,  15,       15,     10,      10,       15],
    "none":               [25,  25,       20,     15,      10,       5]
}
EVENT_LIST = ["monster", "village", "treasure", "dungeon", "npc", "trap"]

# โครงสร้างข้อมูลระดับความโหดของมอนสเตอร์
MONSTER_RANKS = {
    "Common":      {"name": "🟢 มอนสเตอร์ทั่วไป (Common)",      "dice_count": 1, "hp_range": (40, 100),   "flee_chance": 85,  "gold_mult": 5,   "exp_reward": 25},
    "Mini-Boss":   {"name": "🟡 มินิบอส (Mini-Boss)",          "dice_count": 2, "hp_range": (100, 500),  "flee_chance": 60,  "gold_mult": 12,  "exp_reward": 80},
    "Main-Boss":   {"name": "🔴 บอสหลัก (Main-Boss)",          "dice_count": 3, "hp_range": (500, 1000), "flee_chance": 30,  "gold_mult": 30,  "exp_reward": 250},
    "Secret":      {"name": "🟣 มอนสเตอร์ลับ (Secret)",          "dice_count": 2, "hp_range": (100, 1000), "flee_chance": 50,  "gold_mult": 25,  "exp_reward": 200},
    "Unbeatable":  {"name": "💀 ไร้พ่าย (Unbeatable)",         "dice_count": 5, "hp_range": (1000, 2000), "flee_chance": 5,   "gold_mult": 100, "exp_reward": 1000}
}


# ==========================================================
# 🎮 INTERACTIVE VIEWS
# ==========================================================

class MonsterEventView(View):
    def __init__(self, user_id, member_roles, monster_rank=None, monster_hp=None, active_buffs=None, turn_count=1):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.member_roles = member_roles
        self.active_buffs = active_buffs if active_buffs else {}
        self.turn_count = turn_count
        
        if monster_rank is None:
            rank_keys = list(MONSTER_RANKS.keys())
            self.monster_rank = random.choices(rank_keys, weights=[60, 23, 10, 5, 2], k=1)[0]
            self.m_stats = MONSTER_RANKS[self.monster_rank]
            self.monster_hp = random.randint(self.m_stats["hp_range"][0], self.m_stats["hp_range"][1])
        else:
            self.monster_rank = monster_rank
            self.m_stats = MONSTER_RANKS[self.monster_rank]
            self.monster_hp = monster_hp

        self.player_class = "Unknown"
        for role in self.member_roles:
            if role.name in GAME_CLASSES:
                self.player_class = role.name
                break

        self.add_skill_buttons()

    def add_skill_buttons(self):
        skills_map = {
            "Warrior": [("🛡️ Shield Bash", "skill_shield_bash"), ("⚔️ Heavy Strike", "skill_heavy_strike")],
            "Mage":    [("🔥 Fireball", "skill_fireball"),       ("❄️ Frostbolt", "skill_frostbolt")],
            "Rogue":   [("🗡️ Backstab", "skill_backstab"),       ("💨 Evasion", "skill_evasion")],
            "Cleric":  [("✨ Heal", "skill_heal"),               ("🛡️ Holy Aura", "skill_holy_aura")]
        }

        if self.player_class in skills_map:
            for label, custom_id in skills_map[self.player_class]:
                btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id, row=1)
                btn.callback = self.skill_callback 
                self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ นี่ไม่ใช่การต่อสู้ของคุณ! พิมพ์ `!play` เพื่อเปิดบอร์ดตัวเองนะจ๊ะ", ephemeral=True)
            return False
        return True

    async def process_turn(self, interaction: discord.Interaction, skill_used=None):
        player = player_model.get_player(self.user_id)
        p_lvl = player.get("level", 1)
        
        # 1. 🛡️ ดึงข้อมูลอุปกรณ์
        w_id = player.get("weapon", "Wooden_Weapon")
        a_id = player.get("armor", "None")
        w_stat = WEAPON_STATS.get(w_id, WEAPON_STATS["Wooden_Weapon"])
        a_stat = ARMOR_STATS.get(a_id, ARMOR_STATS["None"])
        
        # 2. 🛡️ คำนวณพลังโจมตี (ถ้าความทนทานเป็น 0 พลังโจมตีหาย)
        curr_atk = w_stat["atk"] if player.get("weapon_dur", 0) > 0 else 0
        
        # 3. 🛠️ กำหนดค่าความทนทานเริ่มต้นเป็น 0 เพื่อป้องกันบั๊ก
        durability_lost_w = 3 if skill_used else 1 
        damage_to_armor = 0 
        
        player_roll = random.randint(1, 20)
        monster_roll = sum(random.randint(1, 20) for _ in range(self.m_stats["dice_count"]))
        
        skill_log = ""
        combat_log = ""
        db_updates = {}
        
        enrage_bonus = 0
        if self.turn_count > 3:
            rank_danger = {"Common": 2, "Mini-Boss": 5, "Main-Boss": 10, "Secret": 8, "Unbeatable": 25}
            enrage_bonus = (self.turn_count - 3) * rank_danger.get(self.monster_rank, 2)
            skill_log += f"😡 **{self.m_stats['name']} กำลังคลั่ง!** บอสสะสมความโกรธเพิ่มพลังโจมตีเด็ดขาด `+{enrage_bonus}` หน่วยในเทิร์นนี้!\n"

        damage_multiplier = 1

        # ─── ⚔️ ระบบคำนวณสกิลช่วงต้นเทิร์น (ดึงลอจิกสเกลจาก Config 100%) ───
        if skill_used == "skill_heavy_strike":
            w_cfg = SKILL_CONFIG["Warrior"]["heavy_strike"]
            chance = w_cfg["chance_base"] + (p_lvl * w_cfg["chance_lvl_scale"])
            if random.randint(1, 100) <= chance:
                damage_multiplier = w_cfg["damage_multiplier"]
                skill_log += f"✨ **Heavy Strike สำเร็จ!** การโจมตีในเทิร์นนี้จะแรงขึ้น {damage_multiplier} เท่า!\n"
            else:
                skill_log += "💨 **Heavy Strike ล้มเหลว!** ทอยเต๋าพลาดสมาธิหลุด\n"

        elif skill_used == "skill_evasion":
            r_cfg = SKILL_CONFIG["Rogue"]["evasion"]
            chance = r_cfg["chance_base"] + (p_lvl * r_cfg["chance_lvl_scale"])
            if random.randint(1, 100) <= chance:
                player_model.update_player_field(self.user_id, "current_state", "idle")
                await interaction.response.edit_message(content=f"💨 **Evasion สำเร็จ!** คุณม้วนตัวหนีออกจากสู้กับ **{self.m_stats['name']}** ได้สำเร็จ!", view=AdventureView(author_id=self.user_id))
                return
            else:
                skill_log += "⚠️ **Evasion ล้มเหลว!** มอนสเตอร์ดักทางเท้าไว้ได้\n"

        elif skill_used == "skill_heal":
            c_cfg = SKILL_CONFIG["Cleric"]["heal"]
            heal_percent = c_cfg["heal_percent_base"] + (p_lvl * c_cfg["heal_lvl_scale"])
            heal_amount = int(player["max_hp"] * heal_percent)
            
            if self.monster_rank in ["Main-Boss", "Unbeatable"]:
                stolen_heal = int(heal_amount * 0.3)
                heal_amount -= stolen_heal
                self.monster_hp = min(self.m_stats["hp_range"][1], self.monster_hp + stolen_heal)
                skill_log += f"💔 **คำสาปบอสทำงาน!** บอสสูบกลืนแสงฮีลของคุณไป `+{stolen_heal}` HP! "
            
            new_hp = min(player["max_hp"], player["hp"] + heal_amount)
            player["hp"] = new_hp 
            skill_log += f"✨ **Heal!** พลังชีวิตของคุณฟื้นฟู `+ {heal_amount}` หน่วย (❤️ HP: {new_hp})\n"

        # แจกสถานะเทิร์นบัฟอิงตามระยะเวลาใน Config
        if skill_used == "skill_shield_bash": 
            self.active_buffs["shield_bash"] = SKILL_CONFIG["Warrior"]["shield_bash"]["duration"]
        elif skill_used == "skill_fireball": 
            self.active_buffs["fireball"] = SKILL_CONFIG["Mage"]["fireball"]["duration"]
        elif skill_used == "skill_frostbolt": 
            f_cfg = SKILL_CONFIG["Mage"]["frostbolt"]
            self.active_buffs["frostbolt"] = f_cfg["duration_base"] + int(p_lvl * f_cfg["duration_lvl_scale"])
        elif skill_used == "skill_holy_aura": 
            self.active_buffs["holy_aura"] = 3
        elif skill_used == "skill_backstab":
            r_b_cfg = SKILL_CONFIG["Rogue"]["backstab"]
            if random.randint(1, 100) <= (r_b_cfg["chance_base"] + (p_lvl * r_b_cfg["chance_lvl_scale"])): 
                self.active_buffs["backstab"] = 1

        # 🔥 คิดเอฟเฟกต์เผาไหม้ของ Fireball
        if self.active_buffs.get("fireball", 0) > 0:
            m_cfg = SKILL_CONFIG["Mage"]["fireball"]
            burn_percent = m_cfg["burn_base"] + (p_lvl * m_cfg["burn_lvl_scale"])
            burn_damage = int(self.m_stats["hp_range"][1] * burn_percent)
            self.monster_hp = max(0, self.monster_hp - burn_damage)
            combat_log += f"🔥 *เอฟเฟกต์เผาไหม้:* บอสโดนไฟบอลเผาเสีย HP `- {burn_damage}` หน่วย (บอสเหลือ HP: {self.monster_hp})\n"
            self.active_buffs["fireball"] -= 1

        # ⚔ คุณทอยได้เต๋าชนะบอส
        if player_roll >= monster_roll:
            damage_to_monster = int((player_roll + curr_atk) * 5 * damage_multiplier)
            self.monster_hp = max(0, self.monster_hp - damage_to_monster)
            combat_log += f"⚔️ คุณทอยได้ **🎲 {player_roll}** (+{curr_atk} ดาบ) สร้างความเสียหายใส่บอส `- {damage_to_monster}` หน่วย\n"
        
        # 👾 บอสทอยได้เต๋าชนะ
        else:
            damage_to_player = random.randint(10, 25) + enrage_bonus
            
            # 5. 🛡️ [จุดที่ต้องเพิ่ม] เกราะลดตามความแรงของมอนสเตอร์ (หาร 10)
            # คำนวณความเสียหายเกราะ (ถ้ามีเกราะและยังไม่พัง)
            if player.get("armor_dur", 0) > 0:
                damage_to_armor = max(1, int(damage_to_player / 10))
                # เกราะช่วยลดดาเมจ (ตัวเลือกเสริม: ลดดาเมจให้ผู้เล่น 20%)
                reduction = int(damage_to_player * 0.2)
                damage_to_player -= reduction
                combat_log += f"🛡️ เกราะรับดาเมจแทนคุณ `- {reduction}` หน่วย!\n"
            
            # ❄ สเตตัส Frostbolt
            if self.active_buffs.get("frostbolt", 0) > 0:
                f_reduce = SKILL_CONFIG["Mage"]["frostbolt"]["damage_reduce"]
                damage_to_player = int(damage_to_player * (1 - f_reduce))
                combat_log += f"❄️ *น้ำแข็งเกาะ:* บอสติดแช่แข็ง พลังโจมตีลดลง {int(f_reduce*100)}%! (โดนดาเมจเบา ๆ `- {damage_to_player}`)\n"
                
            elif self.active_buffs.get("holy_aura", 0) > 0 and random.randint(1, 100) <= (SKILL_CONFIG["Cleric"]["holy_aura"]["chance_base"] + (p_lvl * SKILL_CONFIG["Cleric"]["holy_aura"]["chance_lvl_scale"])):
                damage_to_player = 0
                combat_log += "✨ *Holy Aura ทำงาน:* ร่างกายส่องแสงบล็อคพลังโจมตีของบอสกลายเป็น 0!\n"
                
            # 🗡 สเตตัส Backstab (บัฟโรกคริสะท้อน)
            elif self.active_buffs.get("backstab", 0) > 0:
                damage_to_player = int(damage_to_player * 0.2)
                rogue_reflect = int(player_roll * 5 * SKILL_CONFIG["Rogue"]["backstab"]["damage_reflect_mult"])
                self.monster_hp = max(0, self.monster_hp - rogue_reflect)
                combat_log += f"🗡️ *Backstab คุมเชิง:* ดาเมจสวนกลับลดลง 80% (โดนแค่ `- {damage_to_player}`) พร้อมวาร์ปตลบหลังแทงบอสสวนกลับหงายหลังฟาด `- {rogue_reflect}` หน่วย! (บอสเหลือ HP: {self.monster_hp})\n"
                
            elif self.active_buffs.get("shield_bash", 0) > 0:
                s_b_cfg = SKILL_CONFIG["Warrior"]["shield_bash"]
                reduction = s_b_cfg["reduction_base"] + (p_lvl * s_b_cfg["reduction_lvl_scale"])
                damage_to_player = int(damage_to_player * (1 - min(0.9, reduction)))
                combat_log += f"🛡️ *Shield Bash บล็อก:* ดาเมจลดลงครอบคลุมเกราะ (โดนแค่ `- {damage_to_player}`)\n"

            if damage_to_player > 0:
                player["hp"] = max(0, player["hp"] - damage_to_player)
                combat_log += f"💥 บอสโจมตีสวน! เสีย HP `- {damage_to_player}` (เกราะเสื่อมสภาพ `- {damage_to_armor}`)\n"

       # 6. 💾 คำนวณค่าทนทานใหม่ (ถ้าไม่มีการโจมตีสวน ค่า damage_to_armor ก็จะเป็น 0)
        new_w_dur = max(0, player.get("weapon_dur", 0) - durability_lost_w)
        new_a_dur = max(0, player.get("armor_dur", 0) - damage_to_armor)

        db_updates["weapon_dur"] = new_w_dur
        db_updates["armor_dur"] = new_a_dur
        db_updates["hp"] = player["hp"]

        # 7. 🚨 แจ้งเตือนของพัง
        if new_w_dur == 0 and player.get("weapon_dur", 0) > 0:
            combat_log += "🚨 **อาวุธของคุณพังแตกหัก!**\n"
        if new_a_dur == 0 and player.get("armor_dur", 0) > 0:
            combat_log += "🚨 **ชุดเกราะของคุณพังยับเยิน!**\n"

        # หักเทิร์นสถานะบัฟ
        if self.active_buffs.get("frostbolt", 0) > 0: self.active_buffs["frostbolt"] -= 1
        if self.active_buffs.get("holy_aura", 0) > 0: self.active_buffs["holy_aura"] -= 1
        if self.active_buffs.get("shield_bash", 0) > 0: self.active_buffs["shield_bash"] -= 1
        if self.active_buffs.get("backstab", 0) > 0: self.active_buffs["backstab"] -= 1

        db_updates["hp"] = player["hp"]

        # [ลอจิกแพ้ชนะ เช็กเลเวลอัปคงเดิมตามโค้ดของคุณอาเธอร์...]
        if self.monster_hp <= 0:
            reward = random.randint(30, 70) * self.m_stats["gold_mult"]
            gained_exp = self.m_stats["exp_reward"] + random.randint(5, 15)
            db_updates["cash"] = player["cash"] + reward
            db_updates["last_event"] = "monster"
            db_updates["current_state"] = "idle"
            
            if player.get("current_state") == "dungeon_choice" or player.get("dungeon_steps", 0) > 0:
                next_view = AdventureView(author_id=self.user_id) 
                battle_end_log = f"\n⚔️ มอนสเตอร์ในชั้นนี้ถูกกำจัดแล้ว! เตรียมตัวเดินทางลึกเข้าไปในดันเจี้ยนขั้นถัดไป..."
            else:
                next_view = AdventureView(author_id=self.user_id)
                battle_end_log = ""

            current_exp = player.get("exp", 0) + gained_exp
            current_level = player.get("level", 1)
            max_hp = player.get("max_hp", 100)
            is_lv_up = False
            
            while True:
                if current_level >= 100:
                    current_exp = 0
                    break
                required_exp = (current_level ** 2) * 70
                if current_exp >= required_exp:
                    current_exp -= required_exp
                    current_level += 1
                    max_hp += 20
                    is_lv_up = True
                else:
                    break
            
            db_updates["exp"] = current_exp
            db_updates["level"] = current_level
            if is_lv_up:
                db_updates["max_hp"] = max_hp
                db_updates["hp"] = max_hp 

            rank_msg = ""
            old_rank = player.get("rank", "F")
            
            if current_level >= 100: new_rank = "SSS"
            elif current_level >= 80: new_rank = "A"
            elif current_level >= 50: new_rank = "B"
            elif current_level >= 20: new_rank = "C"
            elif current_level >= 10: new_rank = "D"
            elif current_level >= 5: new_rank = "E"
            else: new_rank = "F"
            
            if old_rank != new_rank:
                db_updates["rank"] = new_rank
            
            player_model.update_player_fields(self.user_id, db_updates)
            
            if old_rank != new_rank:
                guild = interaction.guild
                member = interaction.user
                if guild and isinstance(member, discord.Member):
                    role_name = f"นักผจญภัยแรงค์ {new_rank}"
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        try:
                            await member.add_roles(role)
                            rank_msg = f"\n🎖️ **สมาคมนักผจญภัยได้เลื่อนขั้นให้คุณเป็น: {role_name}!**"
                        except Exception as e:
                            print(f"⚠️ ระบบปรับบทบาทดิสคอร์ดขัดข้อง: {e}")

            lv_up_msg = f"\n✨🎉 **LEVEL UP!! คุณเลเวลเพิ่มขึ้นเป็น Lv.{current_level}** พลังชีวิตสูงสุดเพิ่มขึ้น เลือดฟื้นฟูเต็มเปี่ยม! ✨🎉" if is_lv_up else ""
            required_xp_display = (current_level ** 2) * 70
            
            await interaction.response.edit_message(
                content=f"{skill_log}{combat_log}🎉 **ยินดีด้วย! คุณสามารถโค่น {self.m_stats['name']} ลงได้สำเร็จ!**\n💰 ได้รับเงินรางวัล `{reward}` ทอง\n🔷 ได้รับค่าประสบการณ์ `+{gained_exp}` EXP *(สะสมปัจจุบัน: {current_exp}/{required_xp_display} XP)*{lv_up_msg}{rank_msg}{battle_end_log}", 
                view=next_view
            )
            
        elif player["hp"] <= 0:
            db_updates["current_state"] = "dead"
            player_model.update_player_fields(self.user_id, db_updates)
            
            await interaction.response.edit_message(
                content=f"{skill_log}{combat_log}💀 **คุณหมดสติลงกลางสนามรบเนื่องจากทนความโกรธของบอสไม่ไหว...**", 
                view=RespawnView(self.user_id)
            )
        else:
            player_model.update_player_fields(self.user_id, db_updates)
            next_turn = self.turn_count + 1
            await interaction.response.edit_message(
                content=f"⚔️ **[เทิร์นที่ {self.turn_count}] การต่อสู้ทวีความรุนแรง!**\n👾 ศัตรู: **{self.m_stats['name']}** (🩸 HP คงเหลือ: **{self.monster_hp}**)\n❤️ เลือดร่างกายของคุณ: **{player['hp']}/{player['max_hp']}**\n\n{skill_log}{combat_log}----------------------------------------\nบอสจะแกร่งขึ้นเรื่อยๆ เลือกแอคชั่นหรือสกิลที่จะใช้ถัดไป:",
                view=MonsterEventView(self.user_id, self.member_roles, self.monster_rank, self.monster_hp, self.active_buffs, turn_count=next_turn)
            )

    @discord.ui.button(label="⚔️ สู้ต่อ (ทอยเต๋าปกติ)", style=discord.ButtonStyle.danger, row=0)
    async def fight_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_turn(interaction)

    @discord.ui.button(label="🏃 วิ่งหนี!", style=discord.ButtonStyle.secondary, row=0)
    async def flee(self, interaction: discord.Interaction, button: discord.ui.Button):
        flee_roll = random.randint(1, 100)
        
        # ถ้าหนีสำเร็จ
        if flee_roll <= self.m_stats["flee_chance"]:
            player_model.update_player_field(self.user_id, "current_state", "idle")
            await interaction.response.edit_message(content=f"💨 **หนีสำเร็จ!** สลัดหลุดจากมอนสเตอร์สำเร็จ!", view=AdventureView(author_id=self.user_id))
        
        # ถ้าหนีไม่สำเร็จ (โดนโจมตีสวน)
        else:
            player = player_model.get_player(self.user_id)
            damage = random.randint(15, 30)
            new_hp = max(0, player["hp"] - damage)
            
            # 🛡️ คำนวณความเสียหายของเกราะ (โดนตี = เกราะลด)
            if player.get("armor_dur", 0) > 0:
                damage_to_armor = max(1, int(damage / 10))
                new_armor_dur = max(0, player.get("armor_dur", 0) - damage_to_armor)
            else:
                # ถ้าเกราะพังอยู่แล้ว ก็ไม่ต้องลด และไม่ต้องแสดงค่าความเสื่อมสภาพ
                damage_to_armor = 0
                new_armor_dur = 0
            
            # อัปเดตข้อมูลทั้งหมดในรอบเดียว
            db_updates = {
                "hp": new_hp,
                "armor_dur": new_armor_dur,
                "current_state": "fighting"
            }
            
            if new_hp <= 0:
                db_updates["current_state"] = "dead"
                player_model.update_player_fields(self.user_id, db_updates)
                await interaction.response.edit_message(content="💥 หนีไม่พ้นและโดนตบตายคาที่!", view=RespawnView(self.user_id))
            else:
                player_model.update_player_fields(self.user_id, db_updates)
                next_turn = self.turn_count + 1
                msg = f"💥 หนีไม่พ้น! โดนสวนหลังฟาดกระอักเลือด `- {damage}`! (เกราะเสียหาย `- {damage_to_armor}`)"
                
                # เพิ่มข้อความแจ้งเตือนถ้าเกราะพัง
                if new_armor_dur == 0 and player.get("armor_dur", 0) > 0:
                    msg += "\n🚨 **ชุดเกราะของคุณพังยับเยิน!**"
                    
                await interaction.response.edit_message(content=msg, view=MonsterEventView(self.user_id, self.member_roles, self.monster_rank, self.monster_hp, self.active_buffs, turn_count=next_turn))

    async def skill_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        await self.process_turn(interaction, skill_used=interaction.data["custom_id"])

# 2. เหตุการณ์ หมู่บ้าน (Village)
class VillageEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ คุณไม่ใช่เจ้าของแผงพักแรมนี้! พิมพ์ `!play` เพื่อสั่งงานบอร์ดตัวเองน้า", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🛏️ พักแรม (2500 ทอง)", style=discord.ButtonStyle.primary)
    async def rest(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = player_model.get_player(self.user_id)
        if player["cash"] < 2500:
            await interaction.response.send_message("❌ เงินสดกลางไม่พอจ่ายค่าห้องนอน!", ephemeral=True)
            return
        
        # ดึงข้อมูลจากฐานข้อมูล
        armor_key = player.get("armor", "None")
        current_dur = player.get("armor_dur", 0) # ดึงค่าความคงทนมาเช็กด้วย
        # ดึงข้อมูล Config เกราะ
        armor_info = ARMOR_STATS.get(armor_key, ARMOR_STATS["None"])
        armor_hp_bonus = armor_info.get("hp", 0)
        # 🛡️ เงื่อนไขพิเศษ: ถ้าความคงทนเป็น 0 ให้โบนัส HP เป็น 0
        if current_dur <= 0:
            effective_hp_bonus = 0
            # print(f"DEBUG: เกราะ {armor_key} พัง (Dur: {current_dur}) -> โบนัส HP: 0")
        else:
            effective_hp_bonus = armor_hp_bonus
            # print(f"DEBUG: เกราะ {armor_key} ปกติ (Dur: {current_dur}) -> โบนัส HP: {effective_hp_bonus}")
        # คำนวณ HP รวม
        max_hp_total = player["max_hp"] + effective_hp_bonus
            
        player_model.update_player_field(self.user_id, "cash", player["cash"] - 2500)
        player_model.update_player_field(self.user_id, "hp", max_hp_total)
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "village")
        
        await interaction.response.edit_message(
            content="💤 คุณนอนพักผ่อนอย่างเต็มอิ่ม ฟื้นฟู HP จนเต็ม!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView(author_id=self.user_id)
        )

    @discord.ui.button(label="🏪 ร้านค้าประจำ", style=discord.ButtonStyle.primary)
    async def shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        # เปลี่ยนหน้าจาก Village ไปยัง Shop
        await interaction.response.edit_message(
            content="🏪 ยินดีต้อนรับสู่ร้านค้าประจำหมู่บ้าน! คุณต้องการซื้อหรือขายไอเทมอะไรดี?",
            view=ShopEventView(self.user_id) # เรียกใช้ View ร้านค้าที่ผมร่างให้ก่อนหน้านี้
        )

    @discord.ui.button(label="🚶 ออกเดินทางต่อ", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "village")
        
        await interaction.response.edit_message(
            content="🚶 คุณก้าวเท้าเดินออกจากหมู่บ้านมุ่งสู่เส้นทางหลัก...\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView(author_id=self.user_id)
        )

# ระบบร้านค้า      
class ShopEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    # --- หน้าหลัก ---
    @discord.ui.button(label="💰 ซื้อไอเทม", style=discord.ButtonStyle.green)
    async def buy_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 🛠️ กรองแสดงเฉพาะของที่ตั้งค่า purchasable ไม่เท่ากับ False
        content = "🛒 เลือกไอเทมที่ต้องการซื้อ:\n" + "\n".join([f"**เลข {k}:** {v['name']} ({v['buy']} ทอง)" for k, v in ITEM_CONFIG.items() if v.get("purchasable", True)])
        await interaction.response.edit_message(content=content, view=BuySelectView(self.user_id))

    @discord.ui.button(label="📦 ขายไอเทม", style=discord.ButtonStyle.red)
    async def sell_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="เลือกไอเทมที่จะขาย:", view=SellSelectView(self.user_id))

    @discord.ui.button(label="⬅️ กลับไปหมู่บ้าน", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="คุณเดินกลับไปยังจุดพักแรม...", view=VillageEventView(self.user_id))

# --- ระบบซื้อ ---
class BuySelectView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        
        # [ระบบเช็กไฟล์/แคช]
        # print(f"DEBUG: [ร้านค้า] กำลังโหลดหน้า ซื้อไอเทม ให้ User ID: {user_id}")
        
        try:
            for item_id, data in ITEM_CONFIG.items():
                # 🛠️ สร้างปุ่มเฉพาะของที่อนุญาตให้ซื้อ
                if data.get("purchasable", True):
                    btn = discord.ui.Button(label=f"เลข {item_id}", custom_id=item_id)
                    btn.callback = self.buy_callback
                    self.add_item(btn)
            
            # 🚨 จุดที่แก้ไข: ต้องสร้างปุ่มก่อน แล้วค่อยผูกฟังก์ชัน callback 
            back_btn = discord.ui.Button(label="🔙 ย้อนกลับ", style=discord.ButtonStyle.secondary)
            back_btn.callback = self.back_callback
            self.add_item(back_btn)
            
        except Exception as e:
            print(f"ERROR: [ร้านค้า] โหลดหน้าซื้อล้มเหลว: {e}")

    # 🛒 แก้ไขระบบซื้อ
    async def buy_callback(self, interaction: discord.Interaction):
        # 🛡️ 1. สั่ง Defer ทันทีที่กดปุ่ม เพื่อกันบอทขึ้น "การโต้ตอบล้มเหลว"
        await interaction.response.defer()

        item_id = str(interaction.data["custom_id"])
        player = player_model.get_player(self.user_id)
        price = ITEM_CONFIG[item_id]["buy"]
        
        if player["cash"] < price:
            # เปลี่ยนมาใช้ followup เพราะเรา defer ไปแล้ว
            await interaction.followup.send("❌ เงินไม่พอ!", ephemeral=True) 
            return
            
        raw_inv = player.get("inventory", "")
        clean_inv = str(raw_inv)
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            clean_inv = clean_inv.replace(char, "")
            
        inv = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []
        
        inv.append(item_id)
        player["cash"] -= price
        
        player_model.update_player_field(self.user_id, "cash", player["cash"])
        player_model.update_player_field(self.user_id, "inventory", ",".join(inv))
        
        # 🛠️ รีเฟรชข้อความโดยซ่อนไอเทมขยะ
        content = f"🛒 เลือกไอเทมที่ต้องการซื้อ: (เงินคงเหลือ: {player['cash']} ทอง)\n"
        content += "\n".join([f"**เลข {k}:** {v['name']} ({v['buy']} ทอง)" for k, v in ITEM_CONFIG.items() if v.get("purchasable", True)])
        
        # 🛡️ 2. เปลี่ยนมาใช้ edit_original_response
        await interaction.edit_original_response(content=content, view=self)
        await interaction.followup.send(f"✅ ซื้อ {ITEM_CONFIG[item_id]['name']} เข้ากระเป๋า 1 ชิ้น!", ephemeral=True)

    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=ShopEventView(self.user_id))

# --- ระบบขาย ---
class SellSelectView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        player = player_model.get_player(user_id)
        
        try:
            # 🛠️ ระบบกรองทำความสะอาดข้อมูลกระเป๋า
            raw_inv = player.get("inventory", "")
            clean_inv = str(raw_inv)
            for char in ["(", ")", "[", "]", "'", '"', " "]:
                clean_inv = clean_inv.replace(char, "")
                
            inv = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []
            
            unique_items = set(inv)
            
            for item_id in unique_items:
                if item_id in ITEM_CONFIG:
                    btn = discord.ui.Button(label=ITEM_CONFIG[item_id]["name"], custom_id=str(item_id))
                    btn.callback = self.sell_callback
                    self.add_item(btn)
                    
            back_btn = discord.ui.Button(label="🔙 ย้อนกลับ", style=discord.ButtonStyle.secondary)
            back_btn.callback = self.back_callback
            self.add_item(back_btn)
            
        except Exception as e:
            print(f"ERROR: [ร้านค้า] โหลดหน้าขายล้มเหลว: {e}")

    # 💰 แก้ไขระบบขาย
    async def sell_callback(self, interaction: discord.Interaction):
        # 🛡️ 1. สั่ง Defer ทันทีที่กดปุ่ม
        await interaction.response.defer()

        item_id = str(interaction.data["custom_id"])
        player = player_model.get_player(self.user_id)
        
        raw_inv = player.get("inventory", "")
        clean_inv = str(raw_inv)
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            clean_inv = clean_inv.replace(char, "")
            
        inv = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []
        
        if item_id in inv:
            inv.remove(item_id)
            player["cash"] += ITEM_CONFIG[item_id]["sell"]
            
            player_model.update_player_field(self.user_id, "cash", player["cash"])
            player_model.update_player_field(self.user_id, "inventory", ",".join(inv))
            
            content = f"📦 เลือกไอเทมที่จะขาย: (เงินคงเหลือ: {player['cash']} ทอง)"
            # 🛡️ 2. เปลี่ยนมาใช้ edit_original_response
            await interaction.edit_original_response(content=content, view=SellSelectView(self.user_id))
            
            await interaction.followup.send(f"✅ ขาย {ITEM_CONFIG[item_id]['name']} แล้ว! ได้เงินมา {ITEM_CONFIG[item_id]['sell']} ทอง", ephemeral=True)
        else:
            await interaction.followup.send("❌ คุณไม่มีไอเทมชิ้นนี้ให้ขายแล้ว!", ephemeral=True)
            
    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=ShopEventView(self.user_id))
        
# 3. เหตุการณ์ กล่องสมบัติ (Treasure)
class TreasureEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ หีบสมบัตินี้ถูกค้นพบโดยคนอื่น! พิมพ์ `!play` เพื่อออกล่าหีบของตัวเองครับ", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📦 เปิดกล่องสมบัติ", style=discord.ButtonStyle.success)
    async def open_box(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = player_model.get_player(self.user_id)
        
        # 🗡️ เช็กว่าผู้เล่นมีโรล Rogue หรือไม่
        is_rogue = any(role.name == "Rogue" for role in interaction.user.roles)
        
        # 🚨 แก้บั๊กทับซ้อน: คำนวณครั้งเดียว ถ้าเป็น Rogue is_trap จะเป็น False เสมอ
        is_trap = random.random() < 0.25 and not is_rogue

        if is_trap:
            player_model.update_player_field(self.user_id, "current_state", "idle")
            player_model.update_player_field(self.user_id, "last_event", "treasure_trap")
            
            # [ระบบเช็กไฟล์/แคช]
            # print(f"DEBUG: [Treasure] User {self.user_id} โดนกับดัก Mimic!")
            
            await interaction.response.edit_message(
                content="💥 **มันคือหีบกับดักมิมิก (Mimic)!** กลไกกับดักทำงานครอบงำคุณ! (ครั้งหน้าคุณจะเจอกับดักชัวร์ๆ 100%)\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView(author_id=self.user_id)
            )
        else:
            player_model.update_player_field(self.user_id, "current_state", "idle")
            player_model.update_player_field(self.user_id, "last_event", "treasure")
            
            # 🎁 สุ่มประเภทของรางวัล: เงิน (80%) หรือ ไอเทม (20%)
            # ปรับสัดส่วนตรง weights=[80, 20] ได้ตามความต้องการครับ
            reward_type = random.choices(["gold", "item"], weights=[80, 20], k=1)[0]

            if reward_type == "gold":
                gold = random.randint(50, 150)
                player_model.update_player_field(self.user_id, "cash", player["cash"] + gold)
                
                # print(f"DEBUG: [Treasure] User {self.user_id} เปิดได้เงิน {gold} ทอง")
                
                await interaction.response.edit_message(
                    content=f"🎉 โชคดีมาก! ด้านในเป็นหีบสมบัติแท้ คุณได้รับเงินสกุลกลาง `{gold}` ทอง!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                    view=AdventureView(author_id=self.user_id)
                )
            else:
                # 📦 กรณีโชคดีได้ไอเทมฟรี (ใช้ตรรกะออกยากตามราคาแบบเดียวกับ Shop)
                item_ids = list(ITEM_CONFIG.keys())
                weights = [1.0 / max(ITEM_CONFIG[i]["buy"], 1) for i in item_ids] 
                
                chosen_item_id = random.choices(item_ids, weights=weights, k=1)[0]
                chosen_item = ITEM_CONFIG[chosen_item_id]

                # 🛠️ ทำความสะอาดข้อมูลกระเป๋าก่อนยัดของใหม่
                raw_inv = player.get("inventory", "")
                clean_inv = str(raw_inv)
                for char in ["(", ")", "[", "]", "'", '"', " "]:
                    clean_inv = clean_inv.replace(char, "")
                inv_array = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []
                
                # นำของเข้ากระเป๋า (ฟรี ไม่หักเงิน)
                inv_array.append(chosen_item_id)
                player_model.update_player_field(self.user_id, "inventory", ",".join(inv_array))
                
                # print(f"DEBUG: [Treasure] User {self.user_id} แจ็คพอตแตก! เปิดได้ไอเทม {chosen_item['name']}")

                await interaction.response.edit_message(
                    content=f"🎉 แจ็คพอต!! หีบใบนี้ไม่ได้มีแค่เงิน แต่มี **{chosen_item['name']}** ซ่อนอยู่!\n✅ คุณเก็บไอเทมล้ำค่าชิ้นนี้เข้ากระเป๋าไปได้ฟรีๆ!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                    view=AdventureView(author_id=self.user_id)
                )

    @discord.ui.button(label="❌ เมินเฉยและเดินผ่าน", style=discord.ButtonStyle.secondary)
    async def ignore(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "treasure")
        await interaction.response.edit_message(
            content="👀 คุณเลือกที่จะละสายตาจากกล่องและเดินผ่านไปเนิบๆ\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView(author_id=self.user_id)
        )


# 4. เหตุการณ์ เควส NPC
class NpcEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ NPC กำลังสนทนากับนักผจญภัยท่านอื่นอยู่ รบกวนพิมพ์ `!play` แยกน้า", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="💬 เข้าไปพูดคุย", style=discord.ButtonStyle.primary)
    async def talk(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = player_model.get_player(self.user_id)
        outcome = random.choice(["gift", "shop", "nothing"])
        
        # อัปเดตสถานะให้พร้อมออกเดินทางต่อ
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "npc")

        if outcome == "gift":
            gold_gift = random.randint(30, 70)
            player_model.update_player_field(self.user_id, "cash", player["cash"] + gold_gift)
            await interaction.response.edit_message(
                content=f"🧓 NPC ถูกชะตาในตัวคุณ! เขาใจดีมอบเศษเงินทุนกลางจำนวน `{gold_gift}` ทองให้ฟรี!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView(author_id=self.user_id)
            )
            
        elif outcome == "shop":
            # 1. คำนวณเรทสุ่มไอเทม (ไอเทมแพง = โอกาสน้อย)
            item_ids = list(ITEM_CONFIG.keys())
            # ใช้ 1 / ราคาซื้อ เพื่อสร้างน้ำหนัก ยิ่งราคามาก น้ำหนักยิ่งน้อยมาก
            weights = [1.0 / max(ITEM_CONFIG[i]["buy"], 1) for i in item_ids] 
            
            chosen_item_id = random.choices(item_ids, weights=weights, k=1)[0]
            chosen_item = ITEM_CONFIG[chosen_item_id]
            
            # 2. สุ่มราคาขาย (ตั้งแต่ 0 ทอง จนถึง 2 เท่าของราคาเดิม)
            original_price = chosen_item["buy"]
            offered_price = random.randint(0, original_price * 2)
            
            # 3. เช็กเงินว่าพอซื้อไหม
            if player["cash"] >= offered_price:
                # 🛠️ ทำความสะอาดข้อมูลกระเป๋าก่อนยัดของใหม่
                raw_inv = player.get("inventory", "")
                clean_inv = str(raw_inv)
                for char in ["(", ")", "[", "]", "'", '"', " "]:
                    clean_inv = clean_inv.replace(char, "")
                inv_array = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []
                
                # นำของเข้ากระเป๋าและหักเงิน
                inv_array.append(chosen_item_id)
                new_cash = player["cash"] - offered_price
                
                player_model.update_player_field(self.user_id, "cash", new_cash)
                player_model.update_player_field(self.user_id, "inventory", ",".join(inv_array))
                
                price_text = f"`{offered_price:,}` ทอง" if offered_price > 0 else "**ฟรี!!**"
                msg = f"🧓 NPC พ่อค้าเร่เสนอขาย **{chosen_item['name']}** ให้คุณในราคา {price_text}!\n✅ **คุณมีเงินพอจึงจ่ายเงินและรับของมาโดยอัตโนมัติ** (เงินเหลือ `{new_cash:,}`)\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?"
                # print(f"DEBUG: [NPC Shop] สุ่มได้ {chosen_item['name']} ราคา {offered_price} -> ซื้อสำเร็จ")
            else:
                # กรณีเงินไม่พอ ข้ามทันที
                msg = f"🧓 NPC พ่อค้าเร่เสนอขาย **{chosen_item['name']}** ให้คุณในราคา `{offered_price:,}` ทอง!\n❌ **แต่เงินในกระเป๋าของคุณไม่พอ!** (คุณมีแค่ `{player['cash']:,}`) NPC จึงเก็บของแล้วเดินจากไป...\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?"
                # print(f"DEBUG: [NPC Shop] สุ่มได้ {chosen_item['name']} ราคา {offered_price} -> เงินไม่พอ (ข้าม)")

            await interaction.response.edit_message(
                content=msg, 
                view=AdventureView(author_id=self.user_id)
            )
            
        else:
            await interaction.response.edit_message(
                content="💤 NPC แค่บ่นพึมพำเรื่องฟ้าฝนชวนคุยแก้เหงาเฉยๆ ไม่มีอะไรเกิดขึ้น\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView(author_id=self.user_id)
            )

    @discord.ui.button(label="🤫 เมินใส่", style=discord.ButtonStyle.secondary)
    async def ignore(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "npc")
        await interaction.response.edit_message(
            content="🤫 คุณแกล้งทำเป็นมองไม่เห็นและเดินผ่าน NPC ไปอย่างรวดเร็ว\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView(author_id=self.user_id)
        )


# 5. เหตุการณ์ ดันเจี้ยน (Dungeon)
class DungeonEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ นี่คือทางเข้าดันเจี้ยนของนักผจญภัยเจ้าของคำสั่งเท่านั้นครับ!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🚪 บุกเข้าดันเจี้ยน", style=discord.ButtonStyle.danger)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "dungeon_inside") 
        player_model.update_player_field(self.user_id, "dungeon_steps", 10) 
        await interaction.response.edit_message(
            content="💀 คุณก้าวเท้าเข้าสู่ประตูดันเจี้ยนสุดมืดมิด! มีไอชั่วร้ายแผ่ออกมา... ต่อจากนี้คุณต้องสู้กับมอนสเตอร์ต่อเนื่อง 10 ตา!\n----------------------------------------\nคุณต้องการเริ่มสำรวจ (ไปต่อ) หรือไม่?", 
            view=AdventureView(author_id=self.user_id)
        )

    @discord.ui.button(label="🏃 ไม่เข้าดีกว่า", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "dungeon")
        await interaction.response.edit_message(
            content="🏃 ปลอดภัยไว้ก่อน คุณตัดสินใจเดินหันหลังกลับช้าๆ\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView(author_id=self.user_id)
        )


# 6. เหตุการณ์ กับดัก (Trap)
class TrapEventView(View):
    def __init__(self, user_id, member_roles):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.member_roles = member_roles

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ กับดักนี้ดีดใส่ตัวละครอื่นอยู่! ตัวเองรอดแล้วอย่ามากดแทนเพื่อนน้าา", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🎲 ทอยเต๋าหลบกับดัก", style=discord.ButtonStyle.primary)
    async def dodge(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. แจ้ง Discord ว่าบอทได้รับคำสั่งแล้วทันที (กัน Interaction ล้มเหลว)
        await interaction.response.defer()

        player = player_model.get_player(self.user_id)
        # ป้องกันกรณี player ไม่มีข้อมูล (เช่น พิมพ์ !play แล้วไม่อยู่ใน DB)
        if not player:
            await interaction.followup.send("❌ ไม่พบข้อมูลตัวละครของคุณ!", ephemeral=True)
            return

        is_rogue = any(role.name == "Rogue" for role in self.member_roles)
        # อัปเดตสถานะพื้นฐาน
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "trap")
        if is_rogue:
            await interaction.edit_original_response(
                content="💨 **พรสวรรค์คลาส Rogue ทำงาน!** คุณกระโดดม้วนตัวหลบกลไกกับดักพ้นได้อย่างงดงาม 100%!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView(author_id=self.user_id)
            )
            return

        # แก้บรรทัดเดิมของคุณอาเธอร์เป็นชุดนี้ครับ:
        armor_key = player.get("armor", "None")
        armor_data = ARMOR_STATS.get(armor_key)
        
        # ถ้าหาเกราะไม่เจอ ให้ใช้ "None" เป็นค่าเริ่มต้น
        if not armor_data:
            armor_data = ARMOR_STATS["None"]

        armor_evasion = armor_data.get("eva", 0) 
        
        roll_chance = random.randint(1, 100)
        
        if roll_chance <= armor_evasion:
            await interaction.edit_original_response(
                content=f"🎉 รอดหวุดหวิด! (เต๋าสุ่ม {roll_chance} vs อัตราเกราะ {armor_evasion}%) คุณก้าวขาหลบใบมีดกับดักพ้นสำเร็จ!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView(author_id=self.user_id)
            )
        else:
            damage = random.randint(15, 35)
            new_hp = max(0, player["hp"] - damage)
            
            # คำนวณความเสื่อมสภาพเกราะ
            current_armor_dur = player.get("armor_dur", 0)
            if current_armor_dur > 0:
                damage_to_armor = max(1, int(damage / 10))
                new_armor_dur = max(0, current_armor_dur - damage_to_armor)
            else:
                damage_to_armor = 0
                new_armor_dur = 0
            
            # 💾 อัปเดตข้อมูลแยกบรรทัด เพื่อความปลอดภัย (ใช้ update_player_field แบบเดิม)
            player_model.update_player_field(self.user_id, "hp", new_hp)
            player_model.update_player_field(self.user_id, "armor_dur", new_armor_dur)
            
            # 🚨 เช็กว่าเกราะพังหรือไม่
            # armor_alert = "\n🚨 **ชุดเกราะของคุณพังยับเยินจากกับดัก!**" if (new_armor_dur == 0 and current_armor_dur > 0) else ""

            await interaction.edit_original_response(
                content=f"💥 พลาดท่ากระแทกกับดัก! โดนหนามแทงเสีย HP `- {damage}` หน่วย! (เลือดคงเหลือ: {new_hp})\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView(author_id=self.user_id)
        )


# 🏥 VIEW พิเศษ: ฟื้นคืนชีพเมื่อผู้เล่นหมดสติ (Respawn System)
class RespawnView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ วิญญาณนี้ไม่ใช่ของคุณ! ปล่อยให้เจ้าตัวเขากดฟื้นตัวเองนะครับ", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🏥 ฟื้นตัวและกลับหมู่บ้าน", style=discord.ButtonStyle.green)
    async def respawn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = player_model.get_player(self.user_id)
        respawn_hp = int(player["max_hp"] * 0.3)
        penalty_fee = 2500
        new_cash = player.get("cash", 0) - penalty_fee
        
        player_model.update_player_field(self.user_id, "hp", respawn_hp)
        player_model.update_player_field(self.user_id, "cash", new_cash) 
        player_model.update_player_field(self.user_id, "current_state", "village")
        player_model.update_player_field(self.user_id, "last_event", "village")
        player_model.update_player_field(self.user_id, "dungeon_steps", 0) 

        cash_status = f"`{new_cash}` ทอง" if new_cash >= 0 else f"`{new_cash}` ทอง ⚠️ (คุณกำลังติดหนี้สมาคมนักผจญภัย!)"

        await interaction.response.edit_message(
            content=f"😇 **ปาฏิหาริย์!** มีนักเดินทางใจดีช่วยแบกร่างอันหมดสติของคุณมาส่งที่ **'หมู่บ้านอุ่นใจ'**...\n"
                    f"🩸 คุณฟื้นตัวขึ้นมาพร้อมพลังชีวิตเบื้องต้น `❤️ {respawn_hp}` หน่วย\n"
                    f"💸 เสียค่าธรรมเนียมชุบชีวิตและย้ายส่งโรงหมอ `- {penalty_fee}` ทอง (เงินคงเหลือปัจจุบัน: {cash_status})\n"
                    f"----------------------------------------\n"
                    f"ตอนนี้คุณอยู่ในหมู่บ้านแล้ว จะเอาอย่างไรต่อดี?",
            view=VillageEventView(self.user_id) 
        )


# 🧭 VIEW หลักในการเริ่มเดินทาง (!play)
class AdventureView(View):
    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.message = None # 💡 1. เพิ่มตัวแปรไว้เก็บข้อความเพื่อรอการ Edit

    # ==========================================
    # ⏰ ดักจับเวลาผู้เล่นไม่กดปุ่ม "เริ่มออกเดินทาง" ใน 1 นาที
    # ==========================================
    async def on_timeout(self):
        for item in self.children:
            item.disabled = True # ปิดปุ่ม
            
        if self.message:
            try:
                await self.message.edit(content="⏰ **หน้าต่างนี้หมดอายุแล้ว!** รบกวนพิมพ์คำสั่งผจญภัยเพื่อเรียกหน้าต่างใหม่นะครับ", view=self)
            except Exception:
                pass

    # ==========================================
    # ⚠️ ดักจับเวลาปุ่มพังฉุกเฉิน (Soft-lock safeguard)
    # ==========================================
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        print(f"🚨 ERROR [AdventureView]: {error}")
        
        # ปลดล็อกสถานะใน DB ทันที
        player_model.update_player_field(self.author_id, "current_state", "idle")
        err_msg = "⚠️ บอร์ดผจญภัยเกิดข้อผิดพลาด! ระบบได้รีเซ็ตสถานะของคุณให้กลับเป็นปกติแล้วครับ"
        
        if not interaction.response.is_done():
            await interaction.response.send_message(err_msg, ephemeral=True)
        else:
            await interaction.followup.send(err_msg, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ บอร์ดออกเดินทางนี้ไม่ใช่ของคุณ! รบกวนพิมพ์ `!play` เพื่อทริกเกอร์บอร์ดของตัวเองนะครับ", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🧭 เริ่มออกเดินทาง", style=discord.ButtonStyle.green)
    async def start_adv(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        player = player_model.get_player(user_id)

        if player["current_state"] != "idle":
            await interaction.response.send_message("⚠️ คุณกำลังติดเหตุการณ์อื่นอยู่!", ephemeral=True)
            return

        await interaction.response.edit_message(content="✨ คุณเริ่มก้าวเท้าออกเดินทางตรวจตราเส้นทาง...", view=None)

        current_cooldown = player.get("village_cooldown", 0)
        if current_cooldown > 0:
            current_cooldown -= 1
            player_model.update_player_field(user_id, "village_cooldown", current_cooldown)

        # 1. ดึงข้อมูลตัวแปรทั้งหมดมาก่อน (Cache Fetch)
        dg_steps = player.get("dungeon_steps", 0)
        last_evt = player.get("last_event", "none")

        # 2. ตรวจสอบลำดับความสำคัญ (เงื่อนไขบังคับ)
        if dg_steps > 0:
            chosen_event = "monster"
            dg_steps -= 1
            player_model.update_player_field(user_id, "dungeon_steps", dg_steps)
        elif last_evt == "treasure_trap":
            chosen_event = "trap" 
            
        # 3. ถ้าไม่มีเหตุการณ์บังคับ ให้สุ่มตามปกติ
        else:
            if last_evt not in EVENT_WEIGHTS: 
                last_evt = "none"

            current_weights = list(EVENT_WEIGHTS[last_evt])
            
            # ตัดโอกาสเจอหมู่บ้านถ้าติดคูลดาวน์
            if current_cooldown > 0:
                current_weights[1] = 0  

            chosen_event = random.choices(EVENT_LIST, weights=current_weights, k=1)[0]

        # 4. อัปเดต last_event
        player_model.update_player_field(user_id, "last_event", chosen_event)
        
        if chosen_event == "village":
            player_model.update_player_field(user_id, "village_cooldown", 10)


        # ==========================================
        # 🛠️ จุดที่แก้ไข: ท่าส่งข้อความแบบฝัง Timeout ให้เหตุการณ์ถัดไป
        # ==========================================
        if chosen_event == "monster":
            player_model.update_player_field(user_id, "current_state", "fighting")
            status_msg = f"*(เหลืออีก {dg_steps} ตาในดันเจี้ยน)*" if dg_steps > 0 or player.get("dungeon_steps", 0) > 0 else f"*(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*"
            
            # สร้าง View -> ส่งข้อความรอรับค่า -> ยัดข้อความกลับเข้า View
            next_view = MonsterEventView(user_id, interaction.user.roles)
            sent_msg = await interaction.followup.send(content=f"👹 มีเงาปริศนาพุ่งออกมากระโจนขวางทางคุณ! เลือกแอคชั่นหรือคลาสสกิลของคุณ: {status_msg}", view=next_view, wait=True)
            next_view.message = sent_msg
            
        elif chosen_event == "village":
            player_model.update_player_field(user_id, "current_state", "village")
            
            next_view = VillageEventView(user_id)
            sent_msg = await interaction.followup.send(content="🏡 คุณเดินทางมาพบ **'หมู่บ้านอุ่นใจ'** เลือกแอคชั่นของคุณ:", view=next_view, wait=True)
            next_view.message = sent_msg

        elif chosen_event == "treasure":
            player_model.update_player_field(user_id, "current_state", "treasure_choice")
            
            next_view = TreasureEventView(user_id)
            sent_msg = await interaction.followup.send(content=f"📦 คุณพบ **'หีบสมบัติปริศนาลงอักขระโบราณ'** เลือกแอคชั่นของคุณ: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=next_view, wait=True)
            next_view.message = sent_msg

        elif chosen_event == "npc":
            player_model.update_player_field(user_id, "current_state", "npc_choice")
            
            next_view = NpcEventView(user_id)
            sent_msg = await interaction.followup.send(content=f"🧓 คุณเจอนักเดินทางพเนจร (NPC) นั่งอยู่ข้างกองไฟ เลือกแอคชั่นของคุณ: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=next_view, wait=True)
            next_view.message = sent_msg

        elif chosen_event == "dungeon":
            player_model.update_player_field(user_id, "current_state", "dungeon_choice")
            
            next_view = DungeonEventView(user_id)
            sent_msg = await interaction.followup.send(content=f"💀 คุณส่องเห็น **'ช่องอุโมงค์ถ้ำใต้พิภพ (Dungeon)'** เลือกแอคชั่นของคุณ: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=next_view, wait=True)
            next_view.message = sent_msg

        elif chosen_event == "trap":
            player_model.update_player_field(user_id, "current_state", "trap_defense")
            
            next_view = TrapEventView(user_id, interaction.user.roles)
            sent_msg = await interaction.followup.send(content=f"⚠️ *แก๊ก!* คุณพลาดก้าวขาไปเกี่ยวสายสลิง **'กับดักโบราณ'** เข้าให้แล้ว! เตรียมรับมือแอคชั่นหลบหลีก: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=next_view, wait=True)
            next_view.message = sent_msg