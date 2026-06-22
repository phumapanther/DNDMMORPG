import discord
from discord.ext import commands, tasks
import models.player_model as player_model
import random
import time

# ค่าเริ่มต้นเป็น 1 (ปกติ)

class VoiceChatTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_cooldowns = {}
        
        # 🎙️ สั่งให้ตารางเริ่มเดินเครื่อง 1 ครั้งถ้วน รองรับทั้งร่าง chat และร่าง game (Bypass)
        bot_type = getattr(self.bot, 'bot_type', None)
        if bot_type in ["chat", "game"]:
            try:
                self.voice_exp_tracker.start()
                print(f"🎙️ [VOICE TRACKER LOOP] บอทร่าง [{bot_type.upper()}] เริ่มทำงานระบบสแกนห้องเสียงแล้ว!")
            except RuntimeWarning:
                pass
        
    def cog_unload(self):
        # สั่งหยุดระบบ Loop เมื่อ Cog โดนรีโหลดหรือปิดบอท
        bot_type = getattr(self.bot, 'bot_type', None)
        if bot_type in ["chat", "game"] and self.voice_exp_tracker.is_running():
            self.voice_exp_tracker.cancel()


    @tasks.loop(minutes=1.0)
    async def voice_exp_tracker(self):
        # """Loop หลังบ้านสแกนหาผู้เล่นเพื่อแจก EXP พร้อมคิดโบนัสคูณ และเก็บระยะเวลาสะสมลงฐานข้อมูล"""
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                member_count = len(voice_channel.members)
                
                if member_count > 0:
                    raw_names = ", ".join([m.name for m in voice_channel.members])
                else:
                    continue
                    
                for member in voice_channel.members:
                    if member.bot: 
                        continue 
                    
                    player = player_model.get_player(member.id)
                    if not player: 
                        continue
                        
                    # ⏱️ สั่งโมเดลหลังบ้านบวกเวลาเพิ่ม 1 นาที
                    player_model.increment_player_field(member.id, "total_online_time", 1)
                    
                    # 📈 คำนวณแจก EXP ตามระดับเลเวล
                    base_exp = 100 
                    p_lvl = player["level"] 

                    # 1. เช็กยศจาก member object
                    roles = [role.name for role in member.roles]

                    # 2. ตั้งค่าตัวคูณพื้นฐานตามเลเวล
                    multiplier = 0.5
                    if p_lvl >= 80: multiplier = 0.5   # เลเวลสูงเก็บช้าลง
                    elif p_lvl >= 40: multiplier = 0.8
                    elif p_lvl >= 20: multiplier = 1.0
                    else: multiplier = 1.5

                    # 3. เพิ่มโบนัสให้นักกวี (ได้รับ EXP เพิ่ม x4 จากโบนัสห้องเสียง)
                    # ถ้าเป็นนักกวี ให้คูณเพิ่มอีก 4 เท่าจากค่าเดิมที่คำนวณได้
                    if "ทีมงาน" in roles:
                        multiplier = multiplier * 1.2
                        print(f"🛠️ [Voice Reward] คุณ {member.name} (ทีมงาน) ได้รับโบนัส EXP ห้องเสียง x2!")

                    # 3. เพิ่มโบนัสให้นักกวี (คูณ 4)
                    if "꒰ EN ꒱ นักกวี 𝄞⋆" in roles:
                        multiplier = multiplier * 1.5
                        print(f"✨ [Voice Reward] คุณ {member.name} (นักกวี) ได้รับโบนัส EXP ห้องเสียง x4!")

                    # 4. 🎁 ตัวคูณพิเศษช่วงกิจกรรม (กำหนดเป็น 2 ถ้าเปิดกิจกรรม, เป็น 1 ถ้าปิด)
                    event_multiplier = getattr(self.bot, "CURRENT_EVENT_MULTIPLIER", 1.0)
                    final_multiplier = multiplier * event_multiplier

                    final_gained_exp = base_exp * final_multiplier
                    is_lv_up, new_lv, _ = player_model.add_exp(member.id, final_gained_exp)
                    
                    log_time = player.get("total_online_time", 0) + 1
                    
                    if is_lv_up:
                        print(f"✨🎉 [LEVEL UP] -> {member.name} เลเวลอัปเป็น Lv.{new_lv} !!")
                        target_channel = discord.utils.get(member.guild.channels, name="〔⚔〕โดมอัพแรงค์ผจญภัย-⍟")
                        if target_channel:
                            try:
                                # ส่งข้อความแท็กเรียกผู้เล่นประกาศความสำเร็จลงห้องที่กำหนด
                                await target_channel.send(
                                    f"✨🎉 **LEVEL UP!!** แต้มจากการร่วมผจญภัยและพูดคุย ส่งผลให้คุณ {member.mention} "
                                    f"เลเวลอัปเป็น **Lv.{new_lv}** แล้ว! มาร่วมยินดีกันเร็วทุกคน! ⚔️🔥"
                                )
                                print(f"📢 [LEVEL UP LOG] ประกาศเลเวลอัปของ {member.name} ลงห้อง {target_channel.name} สำเร็จ")
                            except Exception as e:
                                print(f"⚠️ [LEVEL UP ERROR] ไม่สามารถส่งข้อความลงห้องได้เนื่องจาก: {e}")
                        else:
                            print("❌ [LEVEL UP ERROR] หาห้องแชท '〔⚔〕โดมอัพแรงค์ผจญภัย-⍟' ไม่พบในเซิร์ฟเวอร์")
                    
                    # 🏅 ตรวจสอบและอัปเดตยศ (Rank) แบบสะสมยศเก่าไม่ลบ
                    updated_player = player_model.get_player(member.id)
                    current_actual_level = updated_player.get("level", 1) if updated_player else p_lvl
                    
                    is_rank_up, new_rank = player_model.check_and_update_rank(member.id, current_actual_level)
                    
                    # 🎖️ นิยามลิสต์ยศที่มีอีโมจิครบถ้วนตามผังเซิร์ฟเวอร์
                    rank_roles_names = [
                        "• นักผจญภัยแรงค์ F",
                        "• นักผจญภัยแรงค์ E",
                        "• นักผจญภัยแรงค์ D",
                        "• นักผจญภัยแรงค์ C",
                        "• นักผจญภัยแรงค์ B",
                        "• นักผจญภัยแรงค์ A",
                        "• นักผจญภัยแรงค์ S 🗺️",
                        "• นักผจญภัยแรงค์ SS 💰",
                        "• นักผจญภัยแรงค์ SSS 👑"
                    ]

                    # 🧠 ค้นหาข้อความในลิสต์ที่มีอักษร Rank (เช่น "แรงค์ F" หรือ "แรงค์ S") 
                    role_name = None
                    for r_name in rank_roles_names:
                        if f"แรงค์ {new_rank}" in r_name:
                            role_name = r_name
                            break

                    if role_name:
                        current_guild = member.guild
                        role = discord.utils.get(current_guild.roles, name=role_name)
                        
                        if role:
                            if is_rank_up or (role not in member.roles):
                                try:
                                    # # 🧹 ล้างยศเก่าที่เคยมีออกให้หมดก่อน เพื่อป้องกันสิทธิ์ทับซ้อน
                                    # for old_role_name in rank_roles_names:
                                    #     old_role = discord.utils.get(current_guild.roles, name=old_role_name)
                                    #     if old_role and old_role in member.roles and old_role != role:
                                    #         try: await member.remove_roles(old_role)
                                    #         except: pass

                                    # 🏅 สั่งแอดแจกยศล่าสุดเข้าไปแทนที่
                                    await member.add_roles(role)
                                    print(f"🏅 [RANK SYNC/UP] -> แจกยศเริ่มต้น/อัปเดตยศ {role_name} ให้แก่ {member.name} สำเร็จ")
                                    
                                except discord.Forbidden:
                                    print(f"❌ บอทไม่มีสิทธิ์จัดการยศในเซิร์ฟเวอร์: {current_guild.name} (กรุณาลากยศบอทให้อยู่สูงกว่ายศแรงค์)")
                                except Exception as e:
                                    print(f"⚠️ เกิดข้อผิดพลาดในการแจกยศห้องเสียง: {e}")
    
    # ─── 💬 ระบบดักฟังช่องแชท แจกเงินเล็กน้อยเมื่อพิมพ์คุย (Text Chat Reward) ───
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None or message.content.startswith("!"):
            return
            
        # 💬 อนุญาตให้รันได้ทั้งร่าง "chat" และร่าง "game" (โหมดบายพาส)
        bot_type = getattr(self.bot, 'bot_type', None)
        if bot_type not in ["chat", "game"]:
            return
            
        user_id = message.author.id
        player = player_model.get_player(user_id)
        if not player:
            return

        # 1. จัดการยศเพื่อคำนวณโบนัส
        roles = [role.name for role in message.author.roles]
        
        # 📈 เก็บสถิติ (ทีมงานได้ event_text * 2)
        event_bonus = 2 if "ทีมงาน" in roles else 1
        current_total = player.get("total_text", 0)
        current_event = player.get("event_text", 0)
        
        player_model.update_player_field(user_id, "total_text", current_total + 1)
        player_model.update_player_field(user_id, "event_text", current_event + event_bonus)

        current_time = time.time()
        
        # ⏱️ ระบบ Cooldown 10 วิ
        if user_id in self.chat_cooldowns:
            if current_time - self.chat_cooldowns[user_id] < 10: 
                return
                
        # 💰 คำนวณเงิน (ผู้ส่งสารได้เงิน * 3)
        gold_multi = 3 if "꒰ PR ꒱ ผู้ส่งสาร" in roles else 1
        gained_gold = random.randint(10, 300) * gold_multi
        new_cash = player.get("cash", 0) + gained_gold
        player_model.update_player_field(user_id, "cash", new_cash)

        self.chat_cooldowns[user_id] = current_time
        
        # 📊 [SYSTEM LOG] พ่นแชทรูมแจกตังค์ลงบนหน้าจอ Terminal
        print(f"💰 [Chat Reward] คุณ {message.author.name} พิมพ์แชทในช่อง #{message.channel.name} -> ได้รับ: +{gained_gold} ทอง (ทองรวมปัจจุบัน: {new_cash})")

# ฟังก์ชันสำหรับติดตั้ง Cog เข้าสู่ระบบบอท
async def setup(bot):
    await bot.add_cog(VoiceChatTracker(bot))