import discord
from discord.ext import commands
import models.player_model as player_model
import random
import asyncio
from utils import not_arrested, allowed_channels

class DuelView(discord.ui.View):
    def __init__(self, challenger, target, timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.target = target

    @discord.ui.button(label="ยอมรับการท้าดวล", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("ไม่ใช่คำท้าของคุณ!", ephemeral=True)
        
        await interaction.response.send_message(f"⚔️ {self.target.mention} ยอมรับคำท้า! การต่อสู้เริ่มขึ้นแล้ว!")
        await self.start_duel(interaction)

    @discord.ui.button(label="ปฏิเสธ", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("ไม่ใช่คำท้าของคุณ!", ephemeral=True)
        await interaction.response.send_message(f"{self.target.mention} ปฏิเสธคำท้า...")
        self.stop()

    async def start_duel(self, interaction):
        # ดึงข้อมูลจากฐานข้อมูล
        p1 = player_model.get_player(self.challenger.id)
        p2 = player_model.get_player(self.target.id)

        # เช็กเงินเดิมพัน (ต้องมีคนละอย่างน้อย 2000)
        if p1.get("cash", 0) < 2000 or p2.get("cash", 0) < 2000:
            return await interaction.channel.send("❌ การดวลถูกยกเลิก! ผู้เล่นทั้งสองฝ่ายต้องมีเงินอย่างน้อย 2,000 ทองสำหรับเดิมพัน")

        # 1. กำหนดค่า HP จำลองเพื่อใช้สู้ (ไม่เซฟกลับลง DB ดังนั้นเลือดจะไม่ลดจริง)
        p1_hp = p1.get("hp", 100)
        p2_hp = p2.get("hp", 100)
        
        log = "⚔️ **การประลองเริ่มต้นขึ้น! (ไม่มีใครตาย!)**\n"
        
        # 2. ลูปการสู้กัน (3 รอบ)
        for turn in range(1, 4):
            atk_dmg = random.randint(10, 20) + (p1.get("attack", 5))
            def_dmg = random.randint(10, 20) + (p2.get("attack", 5))
            
            p2_hp -= atk_dmg
            p1_hp -= def_dmg
            
            log += f"รอบที่ {turn}: {self.challenger.name} โจมตี {atk_dmg} | {self.target.name} สวนกลับ {def_dmg}\n"
            
            if p2_hp <= 0 or p1_hp <= 0: break

        # 3. สรุปผล
        if p1_hp > p2_hp:
            winner, loser = self.challenger, self.target
            winner_id, loser_id = self.challenger.id, self.target.id
        else:
            winner, loser = self.target, self.challenger
            winner_id, loser_id = self.target.id, self.challenger.id

        # 4. หักเงินและโอนเงิน
        player_model.increment_player_field(loser_id, "cash", -2000)
        player_model.increment_player_field(winner_id, "cash", 2000)

        log += f"\n🏆 **ผู้ชนะคือ: {winner.name}!** \n💸 {loser.name} เสียค่าปรับ 2,000 ทองให้ {winner.name} แล้ว!"
        
        await interaction.channel.send(log)

class PvpDuel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @allowed_channels(["⚒-แชทลานประลอง-⚒"])
    @not_arrested() # 🛠️ บล็อกคนติดคุก
    @commands.command(name="challenge")
    async def challenge(self, ctx, member: discord.Member):
        if member.id == ctx.author.id:
            return await ctx.send("❌ ท้าดวลตัวเองเนี่ยนะ?")
        
        # เช็กข้อมูลตัวละครก่อน
        attacker = player_model.get_player(ctx.author.id)
        defender = player_model.get_player(member.id)
        
        if not attacker or not defender:
            return await ctx.send("❌ ข้อมูลตัวละครไม่ครบ!")

        await ctx.send(f"🥊 {ctx.author.mention} ท้าดวลกับ {member.mention}! คุณจะยอมรับไหม?", 
                       view=DuelView(ctx.author, member))

async def setup(bot):
    await bot.add_cog(PvpDuel(bot))