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

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))