import discord
from discord.ext import commands
import random
import models.player_model as player_model
import time # อย่าลืม import time เข้ามานะครับ

class PlayerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. ฝากเงิน: ย้ายเงินจาก Cash -> Bank
    @commands.command(name="deposit")
    async def deposit(self, ctx, amount: int):
        player = player_model.get_player(ctx.author.id)
        if amount <= 0 or player["cash"] < amount:
            return await ctx.send("❌ เงินไม่พอหรือจำนวนไม่ถูกต้อง!")
        
        player_model.update_player_field(ctx.author.id, "cash", player["cash"] - amount)
        player_model.update_player_field(ctx.author.id, "bank", player.get("bank", 0) + amount)
        await ctx.send(f"💰 ฝากเงินเข้าธนาคารเรียบร้อย: `{amount}` ทอง")
        
    @commands.command(name="withdraw")
    async def withdraw(self, ctx, amount: int):
        player = player_model.get_player(ctx.author.id)
        
        # ตรวจสอบ: จำนวนต้องมากกว่า 0 และเงินในธนาคารต้องมีพอ
        if amount <= 0:
            return await ctx.send("❌ จำนวนเงินต้องมากกว่า 0!")
        
        if player.get("bank", 0) < amount:
            return await ctx.send("❌ เงินในธนาคารไม่พอถอนครับ!")
        
        # อัปเดตฐานข้อมูล: หักจาก bank เพิ่มเข้า cash
        player_model.update_player_field(ctx.author.id, "bank", player["bank"] - amount)
        player_model.update_player_field(ctx.author.id, "cash", player["cash"] + amount)
        
        await ctx.send(f"💸 ถอนเงินออกจากธนาคารเรียบร้อย: `{amount:,}` ทอง")

    # 2. โอนเงิน: โอนจาก Bank -> ผู้เล่นอื่น
    @commands.command(name="transfer")
    async def transfer(self, ctx, member: discord.Member, amount: int):
        sender = player_model.get_player(ctx.author.id)
        if sender.get("bank", 0) < amount:
            return await ctx.send("❌ เงินในธนาคารไม่พอโอน!")
        
        target = player_model.get_player(member.id)
        if not target: return await ctx.send("❌ ไม่พบข้อมูลผู้เล่นปลายทาง")

        player_model.update_player_field(ctx.author.id, "bank", sender["bank"] - amount)
        player_model.update_player_field(member.id, "bank", target.get("bank", 0) + amount)
        await ctx.send(f"💸 โอนเงิน `{amount}` ทอง ให้ {member.mention} สำเร็จ!")

    # 3. ขอเงิน (Beg): ต้องมียศ "ขอทาน" และสุ่มดึงจาก Top 10
    @commands.command(name="beg")
    async def beg(self, ctx):
        # ตรวจสอบยศ "ขอทาน"
        if not any(role.name == "ขอทาน" for role in ctx.author.roles):
            return await ctx.send("❌ เฉพาะคนมียศ 'ขอทาน' เท่านั้นที่จะขอเงินคนอื่นได้!")

        top_players = player_model.get_all_players_sorted_by_wealth()[:10] # ต้องทำฟังก์ชันใน model
        if not top_players: return await ctx.send("❌ ไม่มีเศรษฐีให้ขอเลย...")

        target = random.choice(top_players)
        tax = int(target.get("bank", 0) * 0.01)
        
        player_model.update_player_field(target["user_id"], "bank", target["bank"] - tax)
        player_model.update_player_field(ctx.author.id, "cash", player_model.get_player(ctx.author.id)["cash"] + tax)
        await ctx.send(f"🤲 ขอทานได้เงิน `{tax}` ทอง จากเศรษฐี {target['username']}!")

    # 4. ปล้น (Rob): @คนอื่น ถ้าเขาออนอยู่ โอกาสสำเร็จ 20% ดึงมา 50%
    @commands.command(name="rob")
    async def rob(self, ctx, member: discord.Member):
        # 1. เช็กว่าตัวเองติดคุกอยู่ไหม (สถานะต้องไม่ใช่ 'arrested')
        player = player_model.get_player(ctx.author.id)
        if player.get("current_state") == "arrested":
            # เช็กเวลาปลดคุก (ถ้าเวลาปัจจุบันยังไม่ถึงเวลาใน arrest_until)
            if time.time() < player.get("arrest_until", 0):
                return await ctx.send("❌ คุณกำลังติดคุกอยู่! ยังไม่ถึงเวลาพ้นโทษ")
            else:
                # ถ้าเวลาผ่านไปแล้ว ให้รีเซ็ตสถานะเป็น idle
                player_model.update_player_field(ctx.author.id, "current_state", "idle")

        # 2. เช็กสถานะเป้าหมาย
        if member.status == discord.Status.offline:
            return await ctx.send("❌ เป้าหมายออฟไลน์อยู่ ปล้นไม่ได้!")

        # 3. สุ่มผลลัพธ์
        if random.random() <= 0.20: # สำเร็จ 20%
            victim = player_model.get_player(member.id)
            rob_amount = int(victim.get("bank", 0) * 0.5)
            
            player_model.update_player_field(member.id, "bank", victim["bank"] - rob_amount)
            player_model.update_player_field(ctx.author.id, "cash", player["cash"] + rob_amount)
            await ctx.send(f"🥷 ปล้นสำเร็จ! คุณได้เงินจาก {member.mention} มา `{rob_amount}` ทอง")
        
        else: # ปล้นพลาด - ติดคุก 3 นาที
            # คำนวณเวลาสิ้นสุด: ปัจจุบัน + 180 วินาที (3 นาที)
            jail_time = int(time.time() + 180)
            
            # อัปเดตสถานะให้เหมือนคำสั่ง arrest
            player_model.update_player_field(ctx.author.id, "current_state", "arrested")
            player_model.update_player_field(ctx.author.id, "arrest_until", jail_time)
            
            await ctx.send(f"👮 **ปล้นพลาด!** คุณถูกตำรวจจับ! ถูกขังคุกเป็นเวลา 3 นาที")

async def setup(bot):
    await bot.add_cog(PlayerCommands(bot))