import discord
from discord.ext import commands
import random
import asyncio

import models.player_model as player_model
from utils import not_arrested, allowed_channels

# ==========================================
# 🎲 UI View สำหรับเกม ไฮโล (Hi-Lo)
# ==========================================
class HiloView(discord.ui.View):
    def __init__(self, user, bet_amount):
        super().__init__(timeout=60.0)
        self.user = user
        self.bet = bet_amount
        print(f"[LOG] [HILO_INIT] เริ่มต้นกระดานไฮโลสำหรับ {user.display_name} เดิมพัน: {bet_amount} ทอง")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ นี่ไม่ใช่กระดานไฮโลของคุณ!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        print(f"[LOG] [HILO_TIMEOUT] กระดานไฮโลของ {self.user.display_name} หมดเวลา")
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(content="⏳ กระดานไฮโลหมดเวลาแล้ว โปรดพิมพ์คำสั่งใหม่", view=self)
        except: pass

    async def play_hilo(self, interaction: discord.Interaction, choice: str):
        try:
            player = player_model.get_player(self.user.id)
            if not player or player.get("cash", 0) < self.bet:
                print(f"[LOG] [HILO_FAIL] {self.user.display_name} เงินไม่พอตอนกดปุ่ม")
                return await interaction.response.send_message("❌ เงินคุณไม่พอแล้ว!", ephemeral=True)

            # หักเงินทันที
            player_model.increment_player_field(self.user.id, "cash", -self.bet)
            
            # ----------------------------------------------------
            # 😈 ระบบเจ้ามือตุกติก: ยิ่งเดิมพันสูง โอกาสแพ้บังคับยิ่งเยอะ
            # สมมติฐาน: ทุกๆ 10,000 ทอง จะเพิ่มโอกาสโดนล็อคผล 15% (สูงสุด 85%)
            # ----------------------------------------------------
            rig_chance = min(0.85, (self.bet / 10000.0) * 0.15)
            is_rigged = random.random() < rig_chance
            
            # ทอยเต๋าครั้งแรก
            d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
            total = d1 + d2 + d3
            actual_result = "11hilo" if total == 11 else ("low" if total <= 10 else "high")

            # 😈 ถ้าเข้าระบบโกง และผู้เล่นดัน "แทงถูก" -> ให้บอทแอบทอยใหม่จนกว่าจะทายผิด
            if is_rigged and choice == actual_result:
                print(f"[LOG] [CASINO_RIG_HILO] 😈 ระบบตุกติกทำงาน! {self.user.display_name} ลงเงินเยอะ ({self.bet}) และแทงถูก บอทกำลังสับเปลี่ยนลูกเต๋า...")
                attempts = 0
                while choice == actual_result and attempts < 10: # แอบทอยใหม่สูงสุด 10 รอบกันค้าง
                    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
                    total = d1 + d2 + d3
                    actual_result = "11hilo" if total == 11 else ("low" if total <= 10 else "high")
                    attempts += 1
            # ----------------------------------------------------
            
            winnings = 0
            log_msg = f"🎲 ทอยได้ **[{d1}] [{d2}] [{d3}]** (รวม: {total})"
            
            if choice == actual_result:
                if choice == "11hilo":
                    winnings = self.bet * 7 
                    result_text = f"🎉 **แจ็คพอตแตก!! 11 ไฮโล!!** ได้รับ `{winnings}` ทอง!"
                else:
                    winnings = self.bet * 2 
                    result_text = f"✅ **คุณชนะ!** แทงถูกรับไป `{winnings}` ทอง!"
                    
                player_model.increment_player_field(self.user.id, "cash", winnings)
                print(f"[LOG] [HILO_WIN] {self.user.display_name} ชนะ ({choice}) ได้เงิน {winnings}")
            else:
                result_text = f"❌ **คุณแพ้!** เสีย `{self.bet}` ทอง"
                print(f"[LOG] [HILO_LOSE] {self.user.display_name} แพ้ (แทง {choice} ออก {actual_result}) เสีย {self.bet}")

            for item in self.children:
                item.disabled = True
            
            embed = discord.Embed(title="🎲 ผลการทอยไฮโล", color=discord.Color.gold() if winnings > 0 else discord.Color.red())
            embed.description = f"{log_msg}\n\n{result_text}"
            
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()

        except Exception as e:
            print(f"[ERROR] [HILO_PLAY] เกิดข้อผิดพลาดตอนทอยไฮโล: {e}")
            await interaction.response.send_message("❌ เกิดข้อผิดพลาดของระบบคาสิโน!", ephemeral=True)

    @discord.ui.button(label="⬆️ สูง (12-18)", style=discord.ButtonStyle.primary)
    async def btn_high(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play_hilo(interaction, "high")

    @discord.ui.button(label="⬇️ ต่ำ (3-10)", style=discord.ButtonStyle.primary)
    async def btn_low(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play_hilo(interaction, "low")

    @discord.ui.button(label="🎯 11 ไฮโล (x7)", style=discord.ButtonStyle.success)
    async def btn_11hilo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play_hilo(interaction, "11hilo")


# ==========================================
# 🎰 ระบบหลักของคาสิโน (Cog)
# ==========================================
class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f"[LOG] [LOAD_COG] โหลดโมดูล Casino เรียบร้อยแล้ว")

    @allowed_channels(["hilo"]) # 🛠️ ใช้ Decorator บล็อกห้อง
    @not_arrested() # 🛠️ บล็อกคนติดคุก
    @commands.command(name="🎲-Hilo-🎲")
    async def hilo_game(self, ctx, bet: int):
        try:
            if bet <= 0:
                return await ctx.send("❌ เดิมพันต้องมากกว่า 0 ทอง!")
            
            player = player_model.get_player(ctx.author.id)
            if not player or player.get("cash", 0) < bet:
                return await ctx.send("❌ เงินในกระเป๋าของคุณไม่พอ!")

            embed = discord.Embed(title="🎲 โต๊ะไฮโล VIP", description=f"**ผู้เล่น:** {ctx.author.mention}\n**เงินเดิมพัน:** `{bet}` ทอง\n\nโปรดเลือกแทง สูง, ต่ำ หรือ 11 ไฮโล!", color=discord.Color.blue())
            view = HiloView(ctx.author, bet)
            
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg 
            
        except Exception as e:
            print(f"[ERROR] [HILO_CMD] คำสั่ง !hilo พัง: {e}")

    @allowed_channels(["🎰-Slots-🎰"]) # 🛠️ ใช้ Decorator บล็อกห้อง
    @not_arrested() # 🛠️ บล็อกคนติดคุก
    @commands.command(name="slots")
    async def slots_game(self, ctx, bet: int):
        try:
            if bet <= 0:
                return await ctx.send("❌ เดิมพันต้องมากกว่า 0 ทอง!")
            
            player = player_model.get_player(ctx.author.id)
            if not player or player.get("cash", 0) < bet:
                return await ctx.send("❌ เงินในกระเป๋าของคุณไม่พอ!")

            print(f"[LOG] [SLOTS_START] {ctx.author.display_name} หมุนสล็อตด้วยเงิน {bet} ทอง")
            
            player_model.increment_player_field(ctx.author.id, "cash", -bet)

            embed = discord.Embed(title="🎰 สล็อตแมชชีนกำลังหมุน...", description="[ 🌀 | 🌀 | 🌀 ]", color=discord.Color.gold())
            msg = await ctx.send(embed=embed)

            await asyncio.sleep(1.5)

            # ----------------------------------------------------
            # 😈 ระบบเจ้ามือตุกติกสำหรับสล็อต
            # ทุกๆ 10,000 ทอง เพิ่มโอกาสแพ้ 15% (จำกัดสูงสุด 90%)
            # ----------------------------------------------------
            rig_chance = min(0.90, (bet / 10000.0) * 0.15)
            is_rigged = random.random() < rig_chance

            emojis = ["🍒", "🍇", "🍊", "💎", "🔔", "💰"]
            weights = [30, 25, 20, 10, 10, 5]

            def check_win(s1, s2, s3):
                return s1 == s2 or s2 == s3 or s1 == s3

            r1 = random.choices(emojis, weights=weights)[0]
            r2 = random.choices(emojis, weights=weights)[0]
            r3 = random.choices(emojis, weights=weights)[0]

            # 😈 ถ้าโดนโกงและดันหมุนสล็อตชนะ ให้บอทหมุนใหม่จนกว่ารูปจะไม่เหมือนกันเลย
            if is_rigged and check_win(r1, r2, r3):
                print(f"[LOG] [CASINO_RIG_SLOT] 😈 ระบบตุกติกทำงาน! {ctx.author.display_name} หมุนชนะ (Bet: {bet}) บอทกำลังล็อคผลให้ไม่ตรงกัน...")
                attempts = 0
                while check_win(r1, r2, r3) and attempts < 10:
                    r1 = random.choices(emojis, weights=weights)[0]
                    r2 = random.choices(emojis, weights=weights)[0]
                    r3 = random.choices(emojis, weights=weights)[0]
                    attempts += 1
            # ----------------------------------------------------

            result_string = f"[ {r1} | {r2} | {r3} ]"
            winnings = 0
            win_text = ""

            if r1 == r2 == r3:
                if r1 == "💰": multiplier = 15
                elif r1 == "💎": multiplier = 10
                elif r1 == "🔔": multiplier = 7
                else: multiplier = 5
                
                winnings = bet * multiplier
                win_text = f"🎉 **แจ็คพอต!!** ได้สัญลักษณ์ตรงกัน 3 ตัว!\nรับรางวัล `{winnings}` ทอง (x{multiplier})"
            
            elif r1 == r2 or r2 == r3 or r1 == r3:
                multiplier = 1.5
                winnings = int(bet * multiplier)
                win_text = f"✨ **เกือบแจ็คพอต!** ได้สัญลักษณ์ตรงกัน 2 ตัว!\nรับรางวัล `{winnings}` ทอง (x{multiplier})"
            
            else:
                win_text = f"❌ **เสียใจด้วย!** คุณเสีย `{bet}` ทอง"

            if winnings > 0:
                player_model.increment_player_field(ctx.author.id, "cash", winnings)
                print(f"[LOG] [SLOTS_WIN] {ctx.author.display_name} ชนะสล็อต ได้เงิน {winnings}")
            else:
                print(f"[LOG] [SLOTS_LOSE] {ctx.author.display_name} แพ้สล็อต")

            embed.title = "🎰 ผลการหมุนสล็อต"
            embed.description = f"{result_string}\n\n{win_text}"
            embed.color = discord.Color.green() if winnings > 0 else discord.Color.red()
            
            await msg.edit(embed=embed)

        except Exception as e:
            print(f"[ERROR] [SLOTS_CMD] เกิดข้อผิดพลาดในสล็อตแมชชีน: {e}")
            await ctx.send("❌ เกิดข้อผิดพลาดของระบบคาสิโน!")

async def setup(bot):
    try:
        await bot.add_cog(Casino(bot))
        print(f"[LOG] [SETUP] ติดตั้ง Cog Casino เข้ากับระบบหลักสมบูรณ์")
    except Exception as e:
        print(f"[ERROR] [SETUP_CASINO] โหลด Casino ล้มเหลว: {e}")