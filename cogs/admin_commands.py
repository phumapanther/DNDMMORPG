import discord
from discord.ext import commands
from models import player_model  # ดึงโมเดลจัดการฐานข้อมูลมาใช้งาน
import random

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔒 [ระบบตรวจสิทธิ์ + พิมพ์ LOG ลง Terminal เท่านั้น]
    async def cog_check(self, ctx):
        is_owner = ctx.author.id == ctx.guild.owner_id
        is_admin = ctx.author.guild_permissions.administrator
        has_permission = is_owner or is_admin

        # 📄 เตรียมข้อความเพื่อฟ้องลงหน้าจอ Terminal บนเซิร์ฟเวอร์คลาวด์
        log_title = "🟢 [ADMIN COMMAND USED]" if has_permission else "🚨 [UNAUTHORIZED ATTEMPT]"
        log_text = (
            f"\n--------------------------------------------------\n"
            f"{log_title} ตรวจพบการเรียกใช้คำสั่งแอดมิน\n"
            f"👤 ผู้ใช้งาน: {ctx.author.name} (ID: {ctx.author.id})\n"
            f"💬 คำสั่งที่พิมพ์: {ctx.message.content}\n"
            f"📍 ช่องแชท: #{ctx.channel.name}\n"
            f"🛡️ สถานะความปลอดภัย: {'✅ ผ่าน (Authorized)' if has_permission else '❌ บล็อกระบบ (Blocked)'}\n"
            f"--------------------------------------------------"
        )

        # 🖥️ สั่งพิมพ์ข้อความลงหน้าจอ Terminal ทันที
        print(log_text)

        # 🛑 ถ้าสิทธิ์ไม่ผ่าน ให้ดีดข้อความเตือนคนพิมพ์ในแชทดนคอร์ดปกติ และบล็อกไม่ให้คำสั่งทำงาน
        if not has_permission:
            # await ctx.send("❌ **[ปฏิเสธการเข้าถึง]** คำสั่งนี้จำกัดสิทธิ์เฉพาะเจ้าของเซิร์ฟเวอร์ หรือผู้ดูแลระบบเท่านั้นครับ!")
            return False
        return True

    # 🧠 ฟังก์ชันกลางช่วยแปลงค่า: รองรับทั้งการแท็กคน (@ชื่อ) หรือพิมพ์เป็นเลข ID ตรง ๆ
    async def get_target_user_id(self, ctx, user_input):
        if isinstance(user_input, discord.Member) or isinstance(user_input, discord.User):
            return user_input.id, user_input.display_name
            
        if isinstance(user_input, str):
            clean_id = user_input.replace("<@", "").replace(">", "").replace("!", "")
            if clean_id.isdigit():
                uid = int(clean_id)
                member = ctx.guild.get_member(uid) or await self.bot.fetch_user(uid)
                name = member.display_name if member else f"User ID: {uid}"
                return uid, name
        return None, None

    # ─── 💰 1. คำสั่งเซ็ตเงินติดตัว (!set_cash) ───
    @commands.command(name="set_cash")
    async def set_cash(self, ctx, target: str = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_cash [@ชื่อผู้เล่น หรือ ID] [จำนวน]`")
            return
        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id or not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "cash", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนจำนวนทองติดตัวของ **{name}** เป็น `{amount:,}` ทอง เรียบร้อยแล้วครับ! 💸")

    # ─── 🏦 2. คำสั่งเซ็ตเงินในธนาคาร (!set_bank) ───
    @commands.command(name="set_bank")
    async def set_bank(self, ctx, target: str = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_bank [@ชื่อผู้เล่น หรือ ID] [จำนวน]`")
            return
        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id or not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "bank", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนเงินในธนาคารของ **{name}** เป็น `{amount:,}` ทอง เรียบร้อยแล้วครับ! 🏦")

    # ─── 🩸 3. คำสั่งเซ็ตเลือดปัจจุบัน (!set_hp) ───
    @commands.command(name="set_hp")
    async def set_hp(self, ctx, target: str = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_hp [@ชื่อผู้เล่น หรือ ID] [จำนวน]`")
            return
        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id or not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "hp", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนค่าพลังชีวิต (HP) ของ **{name}** เป็น `{amount:,}` HP เรียบร้อยแล้วครับ! 🩸")

    # ─── 🧪 4. คำสั่งเซ็ตเลือดสูงสุด (!set_max_hp) ───
    @commands.command(name="set_max_hp")
    async def set_max_hp(self, ctx, target: str = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_max_hp [@ชื่อผู้เล่น หรือ ID] [จำนวน]`")
            return
        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id or not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "max_hp", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนขีดจำกัดเลือดสูงสุด (Max HP) ของ **{name}** เป็น `{amount:,}` Max HP เรียบร้อยแล้วครับ! 🧪")

    # ─── 🛡️ 5. คำสั่งเซ็ตค่าเกราะ (!set_armor) ───
    @commands.command(name="set_armor")
    async def set_armor(self, ctx, target: str = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_armor [@ชื่อผู้เล่น หรือ ID] [จำนวน]`")
            return
        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id or not player_model.get_player(user_id):
            await ctx.send(f"❌ 不พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "armor", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนค่าเกราะป้องกัน (Armor) ของ **{name}** เป็น `{amount:,}` แต้ม เรียบร้อยแล้วครับ! 🛡️")

    # ─── 📈 6. คำสั่งเซ็ตค่า EXP (!set_exp) ───
    @commands.command(name="set_exp")
    async def set_exp(self, ctx, target: str = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_exp [@ชื่อผู้เล่น หรือ ID] [จำนวน EXP]`")
            return
        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id or not player_model.get_player(user_id):
            await ctx.send(f"❌ 不พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "exp", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนค่า EXP ของ **{name}** เป็น `{amount:,}` EXP เรียบร้อยแล้วครับ! 🎯")

    # ─── 🎖️ 7. คำสั่งเซ็ตแรงค์ (!set_rank) ───
    @commands.command(name="set_rank")
    async def set_rank(self, ctx, target: str = None, *, rank_name: str = None):
        if target is None or rank_name is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_rank [@ชื่อผู้เล่น หรือ ID] [ชื่อแรงค์]`")
            return
        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id or not player_model.get_player(user_id):
            await ctx.send(f"❌ 不พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "rank", rank_name)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนตำแหน่งแรงค์ของ **{name}** เป็น **\"{rank_name}\"** เรียบร้อยแล้วครับ! 🎖️")
        
    # ─── 🔍 8. แอดมินส่องดูสเตตัสโปรไฟล์ผู้เล่น + แปลงเวลา วัน/เดือน/ปี (!check_profile) ───
    @commands.command(name="check_profile")
    async def check_profile(self, ctx, target: str = None):
        if target is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!check_profile [@ชื่อผู้เล่น หรือ ID]`")
            return

        user_id, name = await self.get_target_user_id(ctx, target)
        if not user_id:
            await ctx.send("❌ **ไม่พบผู้ใช้:** รูปแบบไอดีหรือการแท็กชื่อไม่ถูกต้องครับ")
            return

        player = player_model.get_player(user_id)
        if not player:
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครของ **{name}** ในฐานข้อมูลครับ")
            return

        # 📋 ดึงค่าฟิลด์มาตรฐานจาก SQL
        level = player.get("level", 1)
        exp = player.get("exp", 0)
        cash = player.get("cash", 0)
        bank = player.get("bank", 0)
        hp = player.get("hp", 100)
        max_hp = player.get("max_hp", 100)
        armor = player.get("armor", "0")
        rank = player.get("rank", "นักผจญภัยฝึกหัด")
        current_state = player.get("current_state", "ปกติ")

        # ⏱️ [ระบบคำนวณและแปลงค่านาทีเวอร์ชันแก้บั๊กตัวเลขหาย]
        total_mins = player.get("total_online_time", 0)
        
        # ตัวแปรตั้งค่าเวลามาตรฐานระบบเกม
        MINS_IN_HOUR = 60
        MINS_IN_DAY = 60 * 24        # 1,440 นาที
        MINS_IN_MONTH = MINS_IN_DAY * 30  # 43,200 นาที (คิดเฉลี่ยเดือนละ 30 วัน)
        MINS_IN_YEAR = MINS_IN_DAY * 365  # 525,600 นาที

        # ถอดรหัสเวลาแยกก้อนอิสระ มั่นใจได้ว่าเศษนาทีไม่โดนริบหายระหว่างทาง
        years = total_mins // MINS_IN_YEAR
        months = (total_mins % MINS_IN_YEAR) // MINS_IN_MONTH
        days = (total_mins % MINS_IN_MONTH) // MINS_IN_DAY
        hours = (total_mins % MINS_IN_DAY) // MINS_IN_HOUR
        mins = total_mins % MINS_IN_HOUR  # เศษนาทีที่เหลืออยู่จริง ๆ

        # ประกอบข้อความแสดงผล (ชิ้นไหนเป็น 0 จะไม่แสดง ยกเว้นถ้านั่งแช่ยังไม่ถึง 1 ชั่วโมงจะโชว์นาทีให้ชัดเจน)
        time_parts = []
        if years > 0: time_parts.append(f"`{years}` ปี")
        if months > 0: time_parts.append(f"`{months}` เดือน")
        if days > 0: time_parts.append(f"`{days}` วัน")
        if hours > 0: time_parts.append(f"`{hours}` ชม.")
        
        # ถ้านาทีมีค่า หรือยังไม่มีข้อมูลเวลาหน่วยอื่นสะสมเลย ให้ดึงค่าน่าทีขึ้นมาแสดงตรง ๆ
        if mins > 0 or len(time_parts) == 0: 
            time_parts.append(f"`{mins}` นาที")
        
        formatted_time = " ".join(time_parts)

        # 🎨 วาดการ์ด Embed ตรวจสอบ
        embed = discord.Embed(
            title=f"🔎 Admin Inspection — {name}",
            description=f"📂 ข้อมูลสเตตัสในระบบอย่างละเอียด\n💻 User ID: `{user_id}`",
            color=0x3182ce
        )
        
        embed.add_field(name="🎖️ ตำแหน่ง / เลเวล", value=f"**Rank:** {rank}\n**Level:** `{level}`\n**EXP:** `{exp:,}`", inline=True)
        embed.add_field(name="💰 Status การเงิน", value=f"**เงินติดตัว:** `{cash:,}` ทอง\n**ในธนาคาร:** `{bank:,}` ทอง", inline=True)
        embed.add_field(name="⏳ เวลาออนไลน์สะสม", value=f"⏱️:{formatted_time}", inline=False)
        embed.add_field(name="🩸 พลังชีวิตและป้องกัน", value=f"**HP:** `{hp}` / `{max_hp}` | **Armor:** `{armor}` แต้ม\n**สถานะตัวละคร:** `{current_state}`", inline=False)
        
        embed.set_footer(text=f"ตรวจสอบโดย Admin: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))