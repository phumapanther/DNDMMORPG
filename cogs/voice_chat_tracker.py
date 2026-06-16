import discord
from discord.ext import commands, tasks
import models.player_model as player_model
import random
import time

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


   # ─── 🔄 ระบบสแกนดักเช็กห้องเสียง + แจก EXP และบันทึกเวลารายคน (ทำงานทุก 1 นาที) ───
    @tasks.loop(minutes=1.0)
    async def voice_exp_tracker(self):
        # """Loop หลังบ้านสแกนหาผู้เล่นเพื่อแจก EXP พร้อมคิดโบนัสคูณ และเก็บระยะเวลาสะสมลงฐานข้อมูล"""
        # print(f"\n🔍 [VOICE SCAN TIME] ─── เริ่มต้นตรวจสอบรายชื่อห้องเสียงสะสมสเตตัส ───")
        
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                # 🖥️ ดักเช็กตั้งแต่บรรทัดนี้ เพื่อดูว่าบอทมองเห็นห้องเสียงในเซิร์ฟเวอร์ไหม
                member_count = len(voice_channel.members)
                
                # แสดงสถิติห้องเบื้องต้นใน Terminal (ทำให้รู้ว่าบอทไม่ตาย)
                if member_count > 0:
                    raw_names = ", ".join([m.name for m in voice_channel.members])
                    # print(f"📡 [SCANNING] เจอห้อง #{voice_channel.name} | มนุษย์ด้านใน: {member_count} คน ({raw_names})")
                else:
                    continue
                    
                for member in voice_channel.members:
                    if member.bot: 
                        continue 
                        
                    # 🔇 [คอมเมนต์ปิดไว้] ดักเช็กคนปิดไมค์/หูฟัง (หากต้องการกลับมาใช้ ให้ลบเครื่องหมาย # ออก)
                    # if member.voice.self_deaf or member.voice.self_mute: 
                    #     print(f"🔇 [SKIP USER] -> {member.name} โดนข้าม (เนื่องจากปิดไมค์ หรือปิดหูฟังอยู่)")
                    #     continue
                    
                    player = player_model.get_player(member.id)
                    if not player: 
                        # print(f"👤 [SKIP USER] -> {member.name} โดนข้าม (ไม่มีข้อมูลตัวละครในฐานข้อมูล พิมพ์ !play หรือยัง?)")
                        continue
                        
                    # ⏱️ [ระบบบันทึกเวลาแยกฟังก์ชัน] สั่งโมเดลหลังบ้านบวกเวลาเพิ่ม 1 นาทีตรงๆ ใน SQL ไม่ทับค่าเก่า
                    player_model.increment_player_field(member.id, "total_online_time", 1)
                    
                    # 📈 คำนวณแจก EXP ตามระดับเลเวล
                    base_exp = 100 
                    p_lvl = player["level"] 
                    
                    multiplier = 1
                    if p_lvl >= 80: multiplier = 5
                    elif p_lvl >= 40: multiplier = 4
                    elif p_lvl >= 20: multiplier = 3
                    elif p_lvl >= 10: multiplier = 2
                        
                    final_gained_exp = base_exp * multiplier
                    is_lv_up, new_lv, _ = player_model.add_exp(member.id, final_gained_exp)
                    
                    # 🖥️ [PROCESS SUCCESS LOG] ดึงค่าเวลาเดิมจากฐานข้อมูลมา + 1 เพื่อแสดงผลจำลองบนหน้าจอให้แอดมินดูแม่นยำ
                    log_time = player.get("total_online_time", 0) + 1
                    # print(
                    #     f"✅ [REWARDED] -> {member.name} สะสมเวลาสำเร็จ! "
                    #     f"(เวลารวมคาดการณ์: {log_time} นาที | ได้รับ: +{final_gained_exp} EXP)"
                    # )
                    
                    if is_lv_up:
                        print(f"✨🎉 [LEVEL UP] -> {member.name} เลเวลอัปเป็น Lv.{new_lv} !!")
                        # 📩 [คอมเมนต์ปิดไว้] ระบบส่งข้อความแจ้งเลเวลอัปทาง DM
                        # try:
                        #     await member.send(f"✨🎉 **LEVEL UP!!** แต้มจากการร่วมพูดคุยในห้องเสียงส่งผลให้คุณเลเวลอัปเป็น **Lv.{new_lv}** แล้วครับ!")
                        # except discord.Forbidden:
                        #     pass
                    
                    # 🏅 ตรวจสอบและอัปเดตยศ (Rank) แบบสะสมยศเก่าไม่ลบ
                    current_actual_level = new_lv if is_lv_up else p_lvl
                    is_rank_up, new_rank = player_model.check_and_update_rank(member.id, current_actual_level)
                    
                    if is_rank_up:
                        role_name = f"นักผจญภัยแรงค์ {new_rank}"
                        role = discord.utils.get(guild.roles, name=role_name)
                        
                        if role:
                            try:
                                await member.add_roles(role)
                                print(f"🏅 [RANK UP] -> แจกยศ {role_name} ให้แก่ {member.name} สำเร็จ")
                                # 📩 [คอมเมนต์ปิดไว้] ระบบส่งข้อความแจ้งอัปยศทาง DM
                                # await member.send(f"🏅 **[สมาคมนักผจญภัย]** ปรับระดับยศของคุณในเซิร์ฟเวอร์เป็น **{role_name}** เรียบร้อยแล้ว! ⚔️")
                            except discord.Forbidden:
                                print(f"❌ บอทไม่มีสิทธิ์จัดการยศในเซิร์ฟเวอร์: {guild.name}")
                            except Exception as e:
                                print(f"⚠️ เกิดข้อผิดพลาดในการแจกยศ: {e}")
        
        print(f"🏁 [SCAN FINISHED] ─── ประมวลผลลูปห้องเสียงรอบนี้เสร็จสิ้น ───\n")
    
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
        current_time = time.time()
        
        # ⏱️ ตรวจสอบระบบ Cooldown แชท (10 วินาที)
        if user_id in self.chat_cooldowns:
            last_msg_time = self.chat_cooldowns[user_id]
            if current_time - last_msg_time < 10: 
                return
                
        player = player_model.get_player(user_id)
        if player:
            gained_gold = random.randint(10, 300)
            new_cash = player.get("cash", 0) + gained_gold
            
            # บันทึกข้อมูลทองเข้าฐานข้อมูล
            player_model.update_player_field(user_id, "cash", new_cash)
            self.chat_cooldowns[user_id] = current_time
            
            # 📊 [SYSTEM LOG] พ่นแชทรูมแจกตังค์ลงบนหน้าจอ Terminal
            print(f"💰 [Chat Reward] คุณ {message.author.name} พิมพ์แชทในช่อง #{message.channel.name} -> ได้รับ: +{gained_gold} ทอง (ทองรวมปัจจุบัน: {new_cash})")

# ฟังก์ชันสำหรับติดตั้ง Cog เข้าสู่ระบบบอท
async def setup(bot):
    await bot.add_cog(VoiceChatTracker(bot))