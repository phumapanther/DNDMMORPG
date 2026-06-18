import discord
from discord.ext import commands
import random
import models.player_model as player_model
import time
import sqlite3
from contextlib import contextmanager
from utils import not_arrested, allowed_channels  # 👈 ใส่บรรทัดนี้ลงไป


class PlayerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "game_data.db"

    # --- Database Context Manager ---
    @contextmanager
    def get_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        finally:
            conn.close()

    # --- ฟังก์ชันเสริม: ดึงข้อมูลชื่อผู้เล่นแบบมีประสิทธิภาพ ---
    async def get_user_name(self, uid):
        user = self.bot.get_user(uid) or await self.bot.fetch_user(uid)
        return user.name if user else f"User {uid}"

    # 1. ฝากเงิน: ย้ายเงินจาก Cash -> Bank
    @not_arrested() #ตรวจการถูกจับกุมก่อนอนุญาตให้ใช้คำสั่ง
    @commands.command(name="deposit")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def deposit(self, ctx, amount: int):
        player = player_model.get_player(ctx.author.id)
        if amount <= 0 or player["cash"] < amount:
            return await ctx.send("❌ เงินไม่พอหรือจำนวนไม่ถูกต้อง!")
        
        player_model.update_player_field(ctx.author.id, "cash", player["cash"] - amount)
        player_model.update_player_field(ctx.author.id, "bank", player.get("bank", 0) + amount)
        await ctx.send(f"💰 ฝากเงินเข้าธนาคารเรียบร้อย: `{amount}` ทอง")
        
    @not_arrested() #ตรวจการถูกจับกุมก่อนอนุญาตให้ใช้คำสั่ง
    @commands.command(name="withdraw")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
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
    @not_arrested() #ตรวจการถูกจับกุมก่อนอนุญาตให้ใช้คำสั่ง
    @commands.command(name="transfer")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
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
    @not_arrested() #ตรวจการถูกจับกุมก่อนอนุญาตให้ใช้คำสั่ง
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

    # 4. ปล้น (Rob) - ปรับปรุงการป้องกันตัวเอง
    @not_arrested() #ตรวจการถูกจับกุมก่อนอนุญาตให้ใช้คำสั่ง
    @commands.command(name="rob")
    async def rob(self, ctx, member: discord.Member):
        if member.id == ctx.author.id:
            return await ctx.send("❌ จะปล้นตัวเองทำไมล่ะ!")

        player = player_model.get_player(ctx.author.id)
        if player.get("current_state") == "arrested":
            if time.time() < player.get("arrest_until", 0):
                return await ctx.send("❌ คุณกำลังติดคุกอยู่! ยังไม่ถึงเวลาพ้นโทษ")
            else:
                player_model.update_player_field(ctx.author.id, "current_state", "idle")

        if random.random() <= 0.05:
            victim = player_model.get_player(member.id)
            rob_amount = int(victim.get("cash", 0) * 0.5)
            player_model.update_player_field(member.id, "cash", victim["cash"] - rob_amount)
            player_model.update_player_field(ctx.author.id, "cash", player["cash"] + rob_amount)
            await ctx.send(f"🥷 ปล้นสำเร็จ! คุณได้เงินจาก {member.mention} มา `{rob_amount:,}` ทอง")
        else:
            jail_time = int(time.time() + 180)
            player_model.update_player_field(ctx.author.id, "current_state", "arrested")
            player_model.update_player_field(ctx.author.id, "arrest_until", jail_time)
            await ctx.send(f"👮 **ปล้นพลาด!** คุณถูกตำรวจจับ! ถูกขังคุกเป็นเวลา 3 นาที")

    # 5. rich (ปรับปรุงด้วย Database Context Manager & get_user)
    @commands.command(name="rich")
    async def rich(self, ctx):
        with self.get_db() as cursor:
            cursor.execute("SELECT user_id, (bank + cash) as total FROM players ORDER BY total DESC LIMIT 10")
            rows = cursor.fetchall()
        
        msg = "🏆 **10 อันดับมหาเศรษฐี** 🏆\n"
        for i, (uid, total) in enumerate(rows, 1):
            name = await self.get_user_name(uid)
            msg += f"{i}. **{name}**: `{total:,}` ทอง\n"
        await ctx.send(msg)

    # 6. toplvl (ปรับปรุงด้วย Database Context Manager & get_user)
    @commands.command(name="toplvl")
    async def toplvl(self, ctx):
        with self.get_db() as cursor:
            cursor.execute("SELECT user_id, level, exp FROM players ORDER BY level DESC, exp DESC LIMIT 10")
            rows = cursor.fetchall()

        msg = "⚔️ **10 อันดับผู้กล้าเลเวลสูง** ⚔️\n"
        for i, (uid, lvl, exp) in enumerate(rows, 1):
            name = await self.get_user_name(uid)
            msg += f"{i}. **{name}**: เลเวล `{lvl}` (EXP: `{exp}`)\n"
        await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(PlayerCommands(bot))

async def setup(bot):
    await bot.add_cog(PlayerCommands(bot))