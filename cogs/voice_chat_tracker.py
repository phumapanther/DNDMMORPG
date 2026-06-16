import discord
from discord.ext import commands, tasks
import models.player_model as player_model
import random
import time

class VoiceChatTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_cooldowns = {}
        
        # 🎙️ [แยกหน้าที่] สั่งให้ลูปห้องเสียงแจก EXP ทำงาน "เฉพาะบอทสาย chat (แพนด้า)" เท่านั้น
        if hasattr(self.bot, 'bot_type') and self.bot.bot_type == "chat":
            self.voice_exp_tracker.start()
        
    def cog_unload(self):
        # สั่งหยุดระบบ Loop เมื่อ Cog โดนรีโหลดหรือปิดบอท
        if hasattr(self.bot, 'bot_type') and self.bot.bot_type == "chat":
            self.voice_exp_tracker.cancel()

    # ─── 🔄 ระบบสแกนแจก EXP + อัปเดตยศออโต้ในดิสคอร์ด (ทำงานทุก 1 นาที) ───
    @tasks.loop(minutes=1.0)
    async def voice_exp_tracker(self):
        """Loop หลังบ้านสแกนหาผู้เล่นเพื่อแจก EXP พร้อมคิดโบนัสคูณ และแจกยศอัตโนมัติในเซิร์ฟเวอร์"""
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                if len(voice_channel.members) == 0: 
                    continue
                    
                for member in voice_channel.members:
                    if member.bot: continue 
                    if member.voice.self_deaf or member.voice.self_mute: 
                        continue
                    
                    player = player_model.get_player(member.id)
                    if not player: continue
                        
                    base_exp = 100 
                    p_lvl = player["level"] 
                    
                    multiplier = 1
                    if p_lvl >= 80: multiplier = 5
                    elif p_lvl >= 40: multiplier = 4
                    elif p_lvl >= 20: multiplier = 3
                    elif p_lvl >= 10: multiplier = 2
                        
                    final_gained_exp = base_exp * multiplier
                    is_lv_up, new_lv, _ = player_model.add_exp(member.id, final_gained_exp)
                    
                    if is_lv_up:
                        try:
                            await member.send(f"✨🎉 **LEVEL UP!!** แต้มจากการร่วมพูดคุยในห้องเสียงส่งผลให้คุณเลเวลอัปเป็น **Lv.{new_lv}** แล้วครับ!")
                        except discord.Forbidden:
                            pass
                    
                    # 🏅 ตรวจสอบและอัปเดตยศ (Rank) แบบสะสมยศเก่าไม่ลบ
                    current_actual_level = new_lv if is_lv_up else p_lvl
                    is_rank_up, new_rank = player_model.check_and_update_rank(member.id, current_actual_level)
                    
                    if is_rank_up:
                        role_name = f"นักผจญภัยแรงค์ {new_rank}"
                        role = discord.utils.get(guild.roles, name=role_name)
                        
                        if role:
                            try:
                                await member.add_roles(role)
                                await member.send(f"🏅 **[สมาคมนักผจญภัย]** ปรับระดับยศของคุณในเซิร์ฟเวอร์เป็น **{role_name}** เรียบร้อยแล้ว! ⚔️")
                            except discord.Forbidden:
                                print(f"❌ บอทไม่มีสิทธิ์จัดการยศในเซิร์ฟเวอร์: {guild.name}")
                            except Exception as e:
                                print(f"⚠️ เกิดข้อผิดพลาดในการแจกยศ: {e}")

    @voice_exp_tracker.before_loop
    async def before_voice_exp_tracker(self):
        await self.bot.wait_until_ready()
    
    # ─── 💬 ระบบดักฟังช่องแชท แจกเงินเล็กน้อยเมื่อพิมพ์คุย (Text Chat Reward) ───
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None or message.content.startswith("!"):
            return
            
        # 💬 [แยกหน้าที่ + รองรับบายพาส] อนุญาตให้รันได้ทั้งร่าง "chat" (ตัวจริง) และร่าง "game" (ตอนเปิดบายพาส)
        if hasattr(self.bot, 'bot_type') and self.bot.bot_type not in ["chat", "game"]:
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
            
            # 📊 [เพิ่มบรรทัดนี้] สั่งพ่น Log สว่างวาบลงบนหน้าจอ Terminal ทันทีที่มีคนได้ตังค์
            print(f"💰 [Chat Reward] คุณ {message.author.name} พิมพ์แชทในช่อง #{message.channel.name} -> ได้รับ: +{gained_gold} ทอง (ทองรวมปัจจุบัน: {new_cash})")

# ฟังก์ชันสำหรับติดตั้ง Cog เข้าสู่ระบบบอท
async def setup(bot):
    await bot.add_cog(VoiceChatTracker(bot))