import discord
from discord.ui import View
import random
import models.player_model as player_model
from views.profile_embed import ARMOR_STATS, GAME_CLASSES
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

# ==========================================================
# 👹 DATA: โครงสร้างข้อมูลระดับความโหดของมอนสเตอร์ (Monster Rank Matrix)
# ==========================================================
MONSTER_RANKS = {
    "Common":      {"name": "🟢 มอนสเตอร์ทั่วไป (Common)",      "dice_count": 1, "hp_range": (40, 100),   "flee_chance": 85,  "gold_mult": 5,   "exp_reward": 25},
    "Mini-Boss":   {"name": "🟡 มินิบอส (Mini-Boss)",         "dice_count": 2, "hp_range": (100, 500),  "flee_chance": 60,  "gold_mult": 12,  "exp_reward": 80},
    "Main-Boss":   {"name": "🔴 บอสหลัก (Main-Boss)",         "dice_count": 3, "hp_range": (500, 1000), "flee_chance": 30,  "gold_mult": 30,  "exp_reward": 250},
    "Secret":      {"name": "🟣 มอนสเตอร์ลับ (Secret)",         "dice_count": 2, "hp_range": (100, 1000), "flee_chance": 50,  "gold_mult": 25,  "exp_reward": 200},
    "Unbeatable":  {"name": "💀 ไร้พ่าย (Unbeatable)",         "dice_count": 5, "hp_range": (1000, 2000), "flee_chance": 5,   "gold_mult": 100, "exp_reward": 1000}
}

# ==========================================================
# 🎮 INTERACTIVE VIEWS (แก้ไขให้ส่ง AdventureView() กลับไปตอนจบ)
# ==========================================================

# 1. เหตุการณ์ มอนสเตอร์ (Monster)
class MonsterEventView(View):
    # 🎯 จุดที่ 1: เพิ่ม , turn_count=1 เข้าไปท้ายสุดของพารามิเตอร์เพื่อรับค่าจากเทิร์นก่อนหน้า
    def __init__(self, user_id, member_roles, monster_rank=None, monster_hp=None, active_buffs=None, turn_count=1):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.member_roles = member_roles
        
        # 🔄 เก็บค่าบัฟ/ดีบัฟต่อเนื่องระหว่างเทิร์น (ถ้าไม่มีให้ตั้งเป็น Dict ว่าง)
        self.active_buffs = active_buffs if active_buffs else {}
        
        # 🎯 จุดที่ 2: แก้เป็นดึงค่าจากพารามิเตอร์ turn_count ที่ส่งมาตรงๆ (ไม่ใช่ตั้งฟิกไว้เป็น 1)
        self.turn_count = turn_count
        
        # 🎲 ดึงค่ามอนสเตอร์ตามระบบเดิม
        if monster_rank is None:
            rank_keys = list(MONSTER_RANKS.keys())
            self.monster_rank = random.choices(rank_keys, weights=[60, 23, 10, 5, 2], k=1)[0]
            self.m_stats = MONSTER_RANKS[self.monster_rank]
            self.monster_hp = random.randint(self.m_stats["hp_range"][0], self.m_stats["hp_range"][1])
        else:
            self.monster_rank = monster_rank
            self.m_stats = MONSTER_RANKS[self.monster_rank]
            self.monster_hp = monster_hp

        # 🛡️ ระบบตรวจสอบอาชีพเพื่อสร้างปุ่มสกิล Dynamically
        self.player_class = "Unknown"
        for role in self.member_roles:
            if role.name in GAME_CLASSES:
                self.player_class = role.name
                break

        # เรียกใช้ฟังก์ชันยัดปุ่มสกิลเข้าเมนู
        self.add_skill_buttons()

    def add_skill_buttons(self):
        """สร้างปุ่มสกิลและผูกฟังก์ชันรันเทิร์น (Callback) เข้าไปทันที"""
        skills_map = {
            "Warrior": [("🛡️ Shield Bash", "skill_shield_bash"), ("⚔️ Heavy Strike", "skill_heavy_strike")],
            "Mage":    [("🔥 Fireball", "skill_fireball"),       ("❄️ Frostbolt", "skill_frostbolt")],
            "Rogue":   [("🗡️ Backstab", "skill_backstab"),       ("💨 Evasion", "skill_evasion")],
            "Cleric":  [("✨ Heal", "skill_heal"),               ("🛡️ Holy Aura", "skill_holy_aura")]
        }

        if self.player_class in skills_map:
            for label, custom_id in skills_map[self.player_class]:
                btn = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id, row=1)
                
                # 🎯 ผูกเป้าหมาย: เมื่อกดปุ่มสกิลนี้ ให้รันฟังก์ชัน skill_callback ทันที
                btn.callback = self.skill_callback 
                self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """ตรวจสิทธิ์คนกดปุ่ม"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ นี่ไม่ใช่การต่อสู้ของคุณ!", ephemeral=True)
            return False
        return True

    async def process_turn(self, interaction: discord.Interaction, skill_used=None):
        # 🟢 1. ดึงข้อมูลผู้เล่นขึ้นมาเตรียมประมวลผลบนแรม
        player = player_model.get_player(self.user_id)
        p_lvl = player.get("level", 1)
        
        player_roll = random.randint(1, 20)
        monster_roll = sum(random.randint(1, 20) for _ in range(self.m_stats["dice_count"]))
        
        skill_log = ""
        combat_log = ""
        db_updates = {} # คลังสำหรับรวบรวมข้อมูลไว้ Commit รอบเดียว ท้ายฟังก์ชัน
        
        # ─── 💢 ระบบบอสคลั่งตามจำนวนเทิร์น (Enrage Factor) ───
        enrage_bonus = 0
        if self.turn_count > 3:
            rank_danger = {"Common": 2, "Mini-Boss": 5, "Main-Boss": 10, "Secret": 8, "Unbeatable": 25}
            enrage_bonus = (self.turn_count - 3) * rank_danger.get(self.monster_rank, 2)
            skill_log += f"😡 **{self.m_stats['name']} กำลังคลั่ง!** บอสสะสมความโกรธเพิ่มพลังโจมตีเด็ดขาด `+{enrage_bonus}` หน่วยในเทิร์นนี้!\n"

        # ─── 🔮 [STEP 1] ประมวลผลฝั่งสกิล ───
        damage_multiplier = 1

        if skill_used == "skill_heavy_strike":
            chance = 80 + p_lvl
            if random.randint(1, 100) <= chance:
                damage_multiplier = 2
                skill_log += "✨ **Heavy Strike สำเร็จ!** การโจมตีในเทิร์นนี้จะแรงขึ้น 2 เท่า!\n"
            else:
                skill_log += "💨 **Heavy Strike ล้มเหลว!** ทอยเต๋าพลาดสมาธิหลุด\n"

        elif skill_used == "skill_evasion":
            chance = 50 + p_lvl
            if random.randint(1, 100) <= chance:
                player_model.update_player_field(self.user_id, "current_state", "idle")
                await interaction.response.edit_message(content=f"💨 **Evasion สำเร็จ!** คุณม้วนตัวหนีออกจากสู้กับ **{self.m_stats['name']}** ได้สำเร็จ!", view=AdventureView())
                return
            else:
                skill_log += "⚠️ **Evasion ล้มเหลว!** มอนสเตอร์ดักทางเท้าไว้ได้\n"

        elif skill_used == "skill_heal":
            heal_percent = 0.50 + (p_lvl * 0.01)
            heal_amount = int(player["max_hp"] * heal_percent)
            
            if self.monster_rank in ["Main-Boss", "Unbeatable"]:
                stolen_heal = int(heal_amount * 0.3)
                heal_amount -= stolen_heal
                self.monster_hp = min(self.m_stats["hp_range"][1], self.monster_hp + stolen_heal)
                skill_log += f"💔 **คำสาปบอสทำงาน!** บอสสูบกลืนแสงฮีลของคุณไป `+{stolen_heal}` HP! "
            
            new_hp = min(player["max_hp"], player["hp"] + heal_amount)
            player["hp"] = new_hp # พักค่าไว้บนแรมก่อน
            skill_log += f"✨ **Heal!** พลังชีวิตของคุณฟื้นฟู `+ {heal_amount}` หน่วย (❤️ HP: {new_hp})\n"

        # จัดการบัฟต่อเนื่อง
        if skill_used == "skill_shield_bash": self.active_buffs["shield_bash"] = 3
        elif skill_used == "skill_fireball": self.active_buffs["fireball"] = 3
        elif skill_used == "skill_frostbolt": self.active_buffs["frostbolt"] = 1 + int(p_lvl * 0.1)
        elif skill_used == "skill_holy_aura": self.active_buffs["holy_aura"] = 3
        elif skill_used == "skill_backstab":
            if random.randint(1, 100) <= (50 + p_lvl): self.active_buffs["backstab"] = 1

        # ─── ⏳ [STEP 2] บัฟต่อเนื่องเผือดเลือดมอน ───
        if self.active_buffs.get("fireball", 0) > 0:
            burn_percent = 0.10 + (p_lvl * 0.005)
            burn_damage = int(self.m_stats["hp_range"][1] * burn_percent)
            self.monster_hp = max(0, self.monster_hp - burn_damage)
            combat_log += f"🔥 *เอฟเฟกต์เผาไหม้:* บอสโดนไฟบอลเผาเสีย HP `- {burn_damage}` หน่วย (บอสเหลือ HP: {self.monster_hp})\n"
            self.active_buffs["fireball"] -= 1

        # ─── ⚔️ [STEP 3] ฉากแลกเลือดวัดแต้มลูกเต๋า ───
        if player_roll >= monster_roll:
            damage_to_monster = player_roll * 5 * damage_multiplier
            self.monster_hp = max(0, self.monster_hp - damage_to_monster)
            combat_log += f"⚔️ คุณทอยได้ **🎲 {player_roll}** โจมตีสร้างความเสียหายใส่บอส `- {damage_to_monster}` หน่วย\n"
        else:
            damage_to_player = random.randint(10, 25) + enrage_bonus
            
            if self.active_buffs.get("frostbolt", 0) > 0:
                damage_to_player = 0
                combat_log += f"❄️ *น้ำแข็งเกาะ:* บอสติดแช่แข็ง พลังโจมตีกลายเป็น `0`!\n"
            elif self.active_buffs.get("holy_aura", 0) > 0 and random.randint(1, 100) <= (50 + p_lvl):
                damage_to_player = 0
                combat_log += "✨ *Holy Aura ทำงาน:* ร่างกายส่องแสงบล็อคพลังโจมตีของบอสกลายเป็น 0!\n"
            elif self.active_buffs.get("backstab", 0) > 0:
                damage_to_player = int(damage_to_player * 0.2)
                combat_log += f"🗡️ *Backstab คุมเชิง:* ดาเมจสวนกลับลดลง 80% (โดนแค่ `- {damage_to_player}`)\n"
            elif self.active_buffs.get("shield_bash", 0) > 0:
                reduction = 0.50 + (p_lvl * 0.01)
                damage_to_player = int(damage_to_player * (1 - min(0.9, reduction)))
                combat_log += f"🛡️ *Shield Bash บล็อก:* ดาเมจลดลงครึ่งหนึ่ง (โดนแค่ `- {damage_to_player}`)\n"

            if damage_to_player > 0:
                player["hp"] = max(0, player["hp"] - damage_to_player)
                combat_log += f"💥 บอสทอยได้ **🎲 {monster_roll}** สวนกลับกระแทกใส่คุณเสีย HP `- {damage_to_player}` หน่วย\n"

        # หักจำนวนเทิร์นบัฟ
        if self.active_buffs.get("frostbolt", 0) > 0: self.active_buffs["frostbolt"] -= 1
        if self.active_buffs.get("holy_aura", 0) > 0: self.active_buffs["holy_aura"] -= 1
        if self.active_buffs.get("shield_bash", 0) > 0: self.active_buffs["shield_bash"] -= 1
        if self.active_buffs.get("backstab", 0) > 0: self.active_buffs["backstab"] -= 1

        # เตรียมอัปเดตเลือดปัจจุบันลงคลังรวม
        db_updates["hp"] = player["hp"]

        # ─── 🛑 [STEP 4] ตรวจสอบผลลัพธ์พร้อม Commit ข้อมูลก้อนเดียว ───
        if self.monster_hp <= 0:
            reward = random.randint(30, 70) * self.m_stats["gold_mult"]
            gained_exp = self.m_stats["exp_reward"] + random.randint(5, 15)
            
            db_updates["cash"] = player["cash"] + reward
            db_updates["last_event"] = "monster"

            # 🎯 [ปรับตรงนี้] บังคับเคลียร์ให้เป็น "idle" ทั้งหมดเมื่อมอนตาย 
            # เพื่อให้เวลาบอทส่งปุ่ม AdventureView (ปุ่มสีเขียว) ออกไป 
            # ผู้เล่นจะสามารถกดก้าวต่อไปได้ทันทีโดยไม่โดนตัวเช็กความปลอดภัยบล็อกครับ
            db_updates["current_state"] = "idle"
            
            if player.get("current_state") == "dungeon_choice" or player.get("dungeon_steps", 0) > 0:
                next_view = AdventureView() 
                battle_end_log = f"\n⚔️ มอนสเตอร์ในชั้นนี้ถูกกำจัดแล้ว! เตรียมตัวเดินทางลึกเข้าไปในดันเจี้ยนขั้นถัดไป..."
            else:
                next_view = AdventureView()
                battle_end_log = ""

            # 🔷 คำนวณระบบ EXP สไตล์พาราโบลา 3 เดือน
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

            # 🏅 คำนวณระบบยศ (Rank)
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
            
            # 🚀 [🔥 🟥 บันทึกครั้งเดียวจบ!] ส่งชุดตัวแปรทั้งหมดลงฐานข้อมูล
            player_model.update_player_fields(self.user_id, db_updates)
            
            # ⚡ จัดการส่งยศจริงเข้าไปในระบบเซิร์ฟเวอร์ Discord
            if old_rank != new_rank:
                guild = interaction.guild
                member = interaction.user
                if guild and isinstance(member, discord.Member):
                    role_name = f"นักผจญภัยแรงค์ {new_rank}"
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        try:
                            await member.add_roles(role)
                            all_ranks = ["F", "E", "D", "C", "B", "A", "SSS"]
                            for r in all_ranks:
                                if r != new_rank:
                                    old_role = discord.utils.get(guild.roles, name=f"นักผจญภัยแรงค์ {r}")
                                    # if old_role and old_role in member.roles:
                                    #     await member.remove_roles(old_role)
                            rank_msg = f"\n🎖️ **สมาคมนักผจญภัยได้เลื่อนขั้นให้คุณเป็น: {role_name}!**"
                        except Exception as e:
                            print(f"⚠️ ระบบปรับบทบาทดิสคอร์ดขัดข้อง: {e}")

            lv_up_msg = f"\n✨🎉 **LEVEL UP!! คุณเลเวลเพิ่มขึ้นเป็น Lv.{current_level}** พลังชีวิตสูงสุดเพิ่มขึ้น เลือดฟื้นฟูเต็มเปี่ยม! ✨🎉" if is_lv_up else ""
            required_xp_display = (current_level ** 2) * 70
            
            # 🎯 เปลี่ยนมาใช้ความเร็วแสงทางนี้ ป้องกันคิวสัญญาณชนกัน
            await interaction.response.edit_message(
                content=f"{skill_log}{combat_log}🎉 **ยินดีด้วย! คุณสามารถโค่น {self.m_stats['name']} ลงได้สำเร็จ!**\n💰 ได้รับเงินรางวัล `{reward}` ทอง\n🔷 ได้รับค่าประสบการณ์ `+{gained_exp}` EXP *(สะสมปัจจุบัน: {current_exp}/{required_xp_display} XP)*{lv_up_msg}{rank_msg}{battle_end_log}", 
                view=next_view
            )
            
        elif player["hp"] <= 0:
            db_updates["current_state"] = "dead"
            player_model.update_player_fields(self.user_id, db_updates) # บันทึกคนตายรอบเดียว
            
            await interaction.response.edit_message(
                content=f"{skill_log}{combat_log}💀 **คุณหมดสติลงกลางสนามรบเนื่องจากทนความโกรธของบอสไม่ไหว...**", 
                view=RespawnView(self.user_id)
            )
        else:
            # กรณีสู้ต่อ ยิงบันทึกเลือดลดลง DB รอบเดียวแล้วส่งปุ่มชุดเทิร์นถัดไปออกไป
            player_model.update_player_fields(self.user_id, db_updates)
            
            next_turn = self.turn_count + 1
            await interaction.response.edit_message(
                content=f"⚔️ **[เทิร์นที่ {self.turn_count}] การต่อสู้ทวีความรุนแรง!**\n👾 ศัตรู: **{self.m_stats['name']}** (🩸 HP คงเหลือ: **{self.monster_hp}**)\n❤️ เลือกร่างกายของคุณ: **{player['hp']}/{player['max_hp']}**\n\n{skill_log}{combat_log}----------------------------------------\nบอสจะแกร่งขึ้นเรื่อยๆ เลือกแอคชั่นหรือสกิลที่จะใช้ถัดไป:",
                view=MonsterEventView(self.user_id, self.member_roles, self.monster_rank, self.monster_hp, self.active_buffs, turn_count=next_turn)
            )

    # ─── ปุ่มคำสั่งมาตรฐานแถว 0 ───
    @discord.ui.button(label="⚔️ สู้ต่อ (ทอยเต๋าปกติ)", style=discord.ButtonStyle.danger, row=0)
    async def fight_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 🎯 [แก้ไข] เอาคำสั่งเคลียร์สัญญาณหัวฟังก์ชันออกให้หมด! ห้ามมี edit_message() หรือ defer ตรงนี้
        # ปล่อยให้สิทธิ์การตอบกลับไหลไปโต้งๆ ที่ process_turn
        await self.process_turn(interaction)

    @discord.ui.button(label="🏃 วิ่งหนี!", style=discord.ButtonStyle.secondary, row=0)
    async def flee(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 🎯 สำหรับปุ่มวิ่งหนีที่จบในตัวมันเอง ไม่ได้ส่งไป process_turn ให้ใช้ interaction.response ได้ตามปกติครับ
        flee_roll = random.randint(1, 100)
        player_model.update_player_field(self.user_id, "current_state", "idle")
        
        if flee_roll <= self.m_stats["flee_chance"]:
            await interaction.response.edit_message(content=f"💨 **หนีสำเร็จ!** สลัดหลุดจากมอนสเตอร์สำเร็จ!", view=AdventureView())
        else:
            player_model.update_player_field(self.user_id, "current_state", "fighting")
            player = player_model.get_player(self.user_id)
            damage = random.randint(15, 30)
            new_hp = max(0, player["hp"] - damage)
            player_model.update_player_field(self.user_id, "hp", new_hp)
            
            if new_hp <= 0:
                player_model.update_player_field(self.user_id, "current_state", "dead")
                await interaction.response.edit_message(content="💥 หนีไม่พ้นและโดนตบตายคาที่!", view=RespawnView(self.user_id))
            else:
                next_turn = self.turn_count + 1
                await interaction.response.edit_message(content=f"💥 หนีไม่พ้น! โดนสวนหลังฟาดกระอักเลือด `- {damage}`!", view=MonsterEventView(self.user_id, self.member_roles, self.monster_rank, self.monster_hp, self.active_buffs, turn_count=next_turn))
    
    # ─── ระบบดักฟังปุ่ม Button สกิลเสริมแถว 2 ───
    async def skill_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction): return
        
        # 🎯 [แก้ไข] เอาคำสั่งพวก interaction.response.edit_message() หรือ defer_update ที่เคยอยู่ตรงนี้ออกไปให้เกลี้ยง!
        # ส่ง interaction สดๆ ไปให้ process_turn ปิดจ๊อบส่งคำตอบรอบเดียวพอ
        await self.process_turn(interaction, skill_used=interaction.data["custom_id"])

# ==========================================================
# 2. เหตุการณ์ หมู่บ้าน (Village) -> แก้ไขบั๊กสเตตัสค้าง
# ==========================================================
class VillageEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="🛏️ พักแรม (500 ทอง)", style=discord.ButtonStyle.primary)
    async def rest(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        player = player_model.get_player(self.user_id)
        if player["cash"] < 500:
            await interaction.response.send_message("❌ เงินสดกลางไม่พอจ่ายค่าห้องนอน!", ephemeral=True)
            return
            
        # ─── 🛠️ ปรับแก้จุดนี้ ───
        player_model.update_player_field(self.user_id, "cash", player["cash"] - 500)
        player_model.update_player_field(self.user_id, "hp", player["max_hp"])
        
        # ✅ [เพิ่มบรรทัดนี้] เคลียร์สถานะตัวละครให้กลับเป็น idle ทันทีหลังพักผ่อนเสร็จ เพื่อให้กดเดินต่อได้!
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "village")
        
        await interaction.response.edit_message(
            content="💤 คุณนอนพักผ่อนอย่างเต็มอิ่ม ฟื้นฟู HP จนเต็ม!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView()
        )

    @discord.ui.button(label="🛒 ซื้อของ", style=discord.ButtonStyle.green)
    async def shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        await interaction.response.send_message("🏪 พ่อค้าในหมู่บ้านโบกมือทักทาย (ระบบเปิดร้านค้ากำลังพัฒนาในสเต็ปถัดไป)", ephemeral=True)

    @discord.ui.button(label="🚶 ออกเดินทางต่อ", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        
        # ✅ ฟังก์ชันก้าวเท้าออกจากหมู่บ้านมีคำสั่งปรับเป็น idle อยู่แล้ว (ทำงานได้ปกติ)
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "village")
        
        await interaction.response.edit_message(
            content="🚶 คุณก้าวเท้าเดินออกจากหมู่บ้านมุ่งสู่เส้นทางหลัก...\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView()
        )


# 3. เหตุการณ์ กล่องสมบัติ (Treasure)
class TreasureEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="📦 เปิดกล่องสมบัติ", style=discord.ButtonStyle.success)
    async def open_box(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        player = player_model.get_player(self.user_id)
        
        is_trap = random.random() < 0.25
        if is_trap:
            player_model.update_player_field(self.user_id, "current_state", "idle")
            player_model.update_player_field(self.user_id, "last_event", "trap")
            await interaction.response.edit_message(
                content="💥 **มันคือหีบกับดักมิมิก (Mimic)!** กลไกกับดักทำงานครอบงำคุณ! (ครั้งหน้าคุณจะเจอกับดักชัวร์ๆ 100%)\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )
        else:
            gold = random.randint(50, 150)
            player_model.update_player_field(self.user_id, "cash", player["cash"] + gold)
            player_model.update_player_field(self.user_id, "current_state", "idle")
            player_model.update_player_field(self.user_id, "last_event", "treasure")
            await interaction.response.edit_message(
                content=f"🎉 โชคดีมาก! ด้านในเป็นหีบสมบัติแท้ คุณได้รับเงินสกุลกลาง `{gold}` ทอง!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )

    @discord.ui.button(label="❌ เมินเฉยและเดินผ่าน", style=discord.ButtonStyle.secondary)
    async def ignore(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "treasure")
        
        await interaction.response.edit_message(
            content="👀 คุณเลือกที่จะละสายตาจากกล่องและเดินผ่านไปเนิบๆ\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView()
        )


# 4. เหตุการณ์ เควส NPC
class NpcEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="💬 เข้าไปพูดคุย", style=discord.ButtonStyle.primary)
    async def talk(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        player = player_model.get_player(self.user_id)
        
        outcome = random.choice(["gift", "shop", "nothing"])
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "npc")

        if outcome == "gift":
            gold_gift = random.randint(30, 70)
            player_model.update_player_field(self.user_id, "cash", player["cash"] + gold_gift)
            await interaction.response.edit_message(
                content=f"🧓 NPC ถูกชะตาในตัวคุณ! เขาใจดีมอบเศษเงินทุนกลางจำนวน `{gold_gift}` ทองให้ฟรี!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )
        elif outcome == "shop":
            await interaction.response.edit_message(
                content="📜 NPC ขอเปิดกระเป๋าสุ่มขายของหายากให้คุณในราคาพิเศษ!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )
        else:
            await interaction.response.edit_message(
                content="💤 NPC แค่บ่นพึมพำเรื่องฟ้าฝนชวนคุยแก้เหงาเฉยๆ ไม่มีอะไรเกิดขึ้น\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )

    @discord.ui.button(label="🤫 เมินใส่", style=discord.ButtonStyle.secondary)
    async def ignore(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "npc")
        
        await interaction.response.edit_message(
            content="🤫 คุณแกล้งทำเป็นมองไม่เห็นและเดินผ่าน NPC ไปอย่างรวดเร็ว\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView()
        )

# ==========================================================
# 5. เหตุการณ์ ดันเจี้ยน (Dungeon) -> [🚪 ยอมรับเข้า] หรือ [🏃 ข้ามไป]
# ==========================================================
class DungeonEventView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="🚪 บุกเข้าดันเจี้ยน", style=discord.ButtonStyle.danger)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        
        # 🛑 [แก้ไขใหม่] ล็อกคอผู้เล่น ตั้งค่าสเต็ปดันเจี้ยน 10 ตาใน DB ทันที!
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "dungeon_inside") 
        player_model.update_player_field(self.user_id, "dungeon_steps", 10) 
        
        await interaction.response.edit_message(
            content="💀 คุณก้าวเท้าเข้าสู่ประตูดันเจี้ยนสุดมืดมิด! มีไอชั่วร้ายแผ่ออกมา... ต่อจากนี้คุณต้องสู้กับมอนสเตอร์ต่อเนื่อง 10 ตา!\n----------------------------------------\nคุณต้องการเริ่มสำรวจ (ไปต่อ) หรือไม่?", 
            view=AdventureView()
        )

    @discord.ui.button(label="🏃 ไม่เข้าดีกว่า", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "dungeon")
        
        await interaction.response.edit_message(
            content="🏃 ปลอดภัยไว้ก่อน คุณตัดสินใจเดินหันหลังกลับช้าๆ\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
            view=AdventureView()
        )


# 6. เหตุการณ์ กับดัก (Trap)
class TrapEventView(View):
    def __init__(self, user_id, member_roles):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.member_roles = member_roles

    @discord.ui.button(label="🎲 ทอยเต๋าหลบกับดัก", style=discord.ButtonStyle.primary)
    async def dodge(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        player = player_model.get_player(self.user_id)
        
        is_rogue = any(role.name == "Rogue" for role in self.member_roles)
        player_model.update_player_field(self.user_id, "current_state", "idle")
        player_model.update_player_field(self.user_id, "last_event", "trap")
        
        if is_rogue:
            await interaction.response.edit_message(
                content="💨 **พรสวรรค์คลาส Rogue ทำงาน!** คุณกระโดดม้วนตัวหลบกลไกกับดักพ้นได้อย่างงดงาม 100%!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )
            return

        armor_key = player.get("armor", "None")
        armor_evasion = ARMOR_STATS.get(armor_key, ARMOR_STATS["None"])["evasion"]
        roll_chance = random.randint(1, 100)

        if roll_chance <= armor_evasion:
            await interaction.response.edit_message(
                content=f"🎉 รอดหวุดหวิด! (เต๋าสุ่ม {roll_chance} vs อัตราเกราะ {armor_evasion}%) คุณก้าวขาหลบใบมีดกับดักพ้นสำเร็จ!\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )
        else:
            damage = random.randint(15, 35)
            new_hp = max(0, player["hp"] - damage)
            player_model.update_player_field(self.user_id, "hp", new_hp)
            await interaction.response.edit_message(
                content=f"💥 พลาดท่ากระแทกกับดัก! โดนหนามแทงเสีย HP `- {damage}` หน่วย! (เลือดคงเหลือ: {new_hp})\n----------------------------------------\nคุณต้องการไปต่อหรือไม่?", 
                view=AdventureView()
            )

# ==========================================================
# 🏥 VIEW พิเศษ: ฟื้นคืนชีพเมื่อผู้เล่นหมดสติ (Respawn System)
# ==========================================================
class RespawnView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="🏥 ฟื้นตัวและกลับหมู่บ้าน", style=discord.ButtonStyle.green)
    async def respawn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        
        # ฟื้นฟูเลือดให้บางส่วน (เช่น 30% ของ Max HP) เพื่อประคองตัว
        player = player_model.get_player(self.user_id)
        respawn_hp = int(player["max_hp"] * 0.3)
        
        # 💸 [ระบบใหม่] คำนวณค่าธรรมเนียมกู้ชีพหักเงิน 500 ทอง (ติดลบได้)
        penalty_fee = 500
        new_cash = player.get("cash", 0) - penalty_fee
        
        # ส่งตัวละครไปที่สถานะ village และเคลียร์ดันเจี้ยน
        player_model.update_player_field(self.user_id, "hp", respawn_hp)
        player_model.update_player_field(self.user_id, "cash", new_cash) # ✨ บันทึกเงินใหม่ที่ถูกหักลงฐานข้อมูล
        player_model.update_player_field(self.user_id, "current_state", "village")
        player_model.update_player_field(self.user_id, "last_event", "village")
        player_model.update_player_field(self.user_id, "dungeon_steps", 0) # หลุดออกจากดันเจี้ยนทันทีถ้าตายในนั้น

        # สร้างข้อความแจ้งเตือนสถานะการเงิน (ถ้าติดลบจะแจ้งว่าเป็นหนี้สมาคม)
        cash_status = f"`{new_cash}` ทอง" if new_cash >= 0 else f"`{new_cash}` ทอง ⚠️ (คุณกำลังติดหนี้สมาคมนักผจญภัย!)"

        await interaction.response.edit_message(
            content=f"😇 **ปาฏิหาริย์!** มีนักเดินทางใจดีช่วยแบกร่างอันหมดสติของคุณมาส่งที่ **'หมู่บ้านอุ่นใจ'**...\n"
                    f"🩸 คุณฟื้นตัวขึ้นมาพร้อมพลังชีวิตเบื้องต้น `❤️ {respawn_hp}` หน่วย\n"
                    f"💸 เสียค่าธรรมเนียมชุบชีวิตและย้ายส่งโรงหมอ `- {penalty_fee}` ทอง (เงินคงเหลือปัจจุบัน: {cash_status})\n"
                    f"----------------------------------------\n"
                    f"ตอนนี้คุณอยู่ในหมู่บ้านแล้ว จะเอาอย่างไรต่อดี?",
            view=VillageEventView(self.user_id) # 🔄 ส่งต่อเข้าเมนูของหมู่บ้านทันที!
        )

# ==========================================================
# 🧭 VIEW หลักในการเริ่มเดินทาง (!play)
# ==========================================================
class AdventureView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="🧭 เริ่มออกเดินทาง", style=discord.ButtonStyle.green)
    async def start_adv(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        player = player_model.get_player(user_id)

        if player["current_state"] != "idle":
            await interaction.response.send_message("⚠️ คุณกำลังติดเหตุการณ์อื่นอยู่!", ephemeral=True)
            return

        # ซ่อน/ถอดปุ่มกดเก่าออกทันที
        await interaction.response.edit_message(content="✨ คุณเริ่มก้าวเท้าออกเดินทางตรวจตราเส้นทาง...", view=None)

        # ⏳ จัดการลดคูลดาวน์หมู่บ้านตามปกติ
        current_cooldown = player.get("village_cooldown", 0)
        if current_cooldown > 0:
            current_cooldown -= 1
            player_model.update_player_field(user_id, "village_cooldown", current_cooldown)

        # 💀 [ระบบใหม่] เช็กจำนวนรอบที่ติดอยู่ในดันเจี้ยน
        dg_steps = player.get("dungeon_steps", 0)

        # ─── 🎰 คำนวณเลือกเหตุการณ์ ───
        if dg_steps > 0:
            # 🛑 กฎบังคับเด็ดขาด: ถ้ายังติดสเต็ปดันเจี้ยน ให้เจอมอนสเตอร์ 100%!
            chosen_event = "monster"
            
            # ลดจำนวนสเต็ปดันเจี้ยนลงทีละ 1 รอบแล้วบันทึกค่า
            dg_steps -= 1
            player_model.update_player_field(user_id, "dungeon_steps", dg_steps)
        else:
            # หากอยู่นอกดันเจี้ยน ให้ดึงระบบสุ่มแบบใช้สัดส่วนน้ำหนักตามปกติ
            last_evt = player.get("last_event", "none")
            if last_evt not in EVENT_WEIGHTS: last_evt = "none"

            current_weights = list(EVENT_WEIGHTS[last_evt])
            if current_cooldown > 0:
                current_weights[1] = 0  # บังคับโอกาสเกิดหมู่บ้านเป็น 0% ถ้ายังติดคูลดาวน์

            chosen_event = random.choices(EVENT_LIST, weights=current_weights, k=1)[0]

        # 🏡 ถ้าสุ่มได้หมู่บ้านในรอบปกติ ให้ล็อกคอตั้งคูลดาวน์ 10 ตา
        if chosen_event == "village":
            player_model.update_player_field(user_id, "village_cooldown", 10)


        # ─── ส่งข้อความเหตุการณ์ใหม่ไปยังแชท ───
        if chosen_event == "monster":
            player_model.update_player_field(user_id, "current_state", "fighting")
            status_msg = f"*(เหลืออีก {dg_steps} ตาในดันเจี้ยน)*" if dg_steps > 0 or player.get("dungeon_steps", 0) > 0 else f"*(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*"
            # ✅ ถอด ephemeral=True ออกเรียบร้อย ปุ่มสกิลและปุ่มสู้จะกลับมาแสดงผลทันที!
            await interaction.followup.send(content=f"👹 มีเงาปริศนาพุ่งออกมากระโจนขวางทางคุณ! เลือกแอคชั่นหรือคลาสสกิลของคุณ: {status_msg}", view=MonsterEventView(user_id, interaction.user.roles))
            
        elif chosen_event == "village":
            player_model.update_player_field(user_id, "current_state", "village")
            await interaction.followup.send(content="🏡 คุณเดินทางมาพบ **'หมู่บ้านอุ่นใจ'** เลือกแอคชั่นของคุณ:", view=VillageEventView(user_id))

        elif chosen_event == "treasure":
            player_model.update_player_field(user_id, "current_state", "treasure_choice")
            await interaction.followup.send(content=f"📦 คุณพบ **'หีบสมบัติปริศนาลงอักขระโบราณ'** เลือกแอคชั่นของคุณ: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=TreasureEventView(user_id))

        elif chosen_event == "npc":
            player_model.update_player_field(user_id, "current_state", "npc_choice")
            await interaction.followup.send(content=f"🧓 คุณเจอนักเดินทางพเนจร (NPC) นั่งอยู่ข้างกองไฟ เลือกแอคชั่นของคุณ: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=NpcEventView(user_id))

        elif chosen_event == "dungeon":
            player_model.update_player_field(user_id, "current_state", "dungeon_choice")
            await interaction.followup.send(content=f"💀 คุณส่องเห็น **'ช่องอุโมงค์ถ้ำใต้พิภพ (Dungeon)'** เลือกแอคชั่นของคุณ: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=DungeonEventView(user_id))

        elif chosen_event == "trap":
            player_model.update_player_field(user_id, "current_state", "trap_defense")
            await interaction.followup.send(content=f"⚠️ *แก๊ก!* คุณพลาดก้าวขาไปเกี่ยวสายสลิง **'กับดักโบราณ'** เข้าให้แล้ว! เตรียมรับมือแอคชั่นหลบหลีก: *(คูลดาวน์หมู่บ้านเหลือ: {current_cooldown} ตา)*", view=TrapEventView(user_id, interaction.user.roles))
            