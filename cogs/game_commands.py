import discord
from discord.ext import commands
import models.player_model as player_model
from views.profile_embed import create_profile_embed

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 🎮 [คลีนระบบ] ถอดคำสั่งสั่งเริ่มทำงานของลูปแจก EXP และ Cooldown แชทออกทั้งหมดแล้ว (ย้ายไปโมดูลอื่นสำเร็จ)

    # ─── 🛒 คำสั่งเปิดร้านค้าและซื้อขายยศแบบข้อความ (!shop) ───
    @commands.command(name="shop")
    async def shop(self, ctx, action: str = None, item_num: int = None):
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        if not player:
            await ctx.send("❌ 不พบข้อมูลตัวละครของคุณ กรุณาพิมพ์ `!play` เพื่อลงทะเบียนก่อนครับ")
            return

        # 📋 คลังข้อมูลราคายศและชื่อยศในเซิร์ฟเวอร์
        shop_items = {
            1: {"name": "ขายยศ 1", "price": 10000},
            2: {"name": "ขายยศ 2", "price": 50000},
            3: {"name": "ขายยศ 3", "price": 100000}
        }

        # 🛑 เคสที่ 1: พิมพ์ !shop เฉยๆ -> บอทเปิดใบรายการหน้าร้านให้ดู
        if action is None:
            embed = discord.Embed(
                title="🛒 สมาคมนักผจญภัย - ร้านค้าตราเกียรติยศ (Text Edition)",
                description=f"ยินดีต้อนรับคุณ **{ctx.author.name}** เข้าสู่หอเกียรติยศ\n💰 เงินคงเหลือปัจจุบัน: `{player.get('cash', 0)}` ทอง\n\n"
                            f"📌 **รายการยศที่มีวางจำหน่าย:**\n"
                            f"🔹 **[1] ยศทดสอบ 1** — ราคา `10,000` ทอง\n"
                            f"🔹 **[2] ยศทดสอบ 2** — ราคา `50,000` ทอง\n"
                            f"🔹 **[3] ยศทดสอบ 3** — ราคา `100,000` ทอง\n\n"
                            f"⌨️ **วิธีสั่งซื้อ:** พิมพ์คำสั่ง `!shop ซื้อ [เลขยศ]` (เช่น `!shop ซื้อ 1`)",
                color=0xecc94b
            )
            await ctx.send(embed=embed)
            return

        # 🛑 เคสที่ 2: พิมพ์คำสั่งซื้อแต่กรอกพารามิเตอร์ไม่ครบ หรือพิมพ์คำอื่นที่ไม่ใช่ "ซื้อ"
        if action not in ["ซื้อ", "buy"] or item_num is None:
            await ctx.send("❓ **รูปแบบคำสั่งไม่ถูกต้อง:** กรุณาพิมพ์ `!shop ซื้อ [เลขยศ]` เช่น `!shop ซื้อ 1` ครับ")
            return

        # 🛑 เคสที่ 3: กรอกเลขยศที่ไม่มีในร้าน (เช่น ใส่เลข 4 หรือ 99)
        if item_num not in shop_items:
            await ctx.send("❌ **ไม่มีสินค้านี้ในระบบ:** กรุณาเลือกซื้อเฉพาะหมายเลข 1, 2 หรือ 3 เท่านั้นครับ")
            return

        # 🎯 เข้าสู่กระบวนการตรวจสอบข้อมูลและแลกเปลี่ยนยศ
        item = shop_items[item_num]
        role_name = item["name"]
        price = item["price"]
        current_cash = player.get("cash", 0)

        # 🚫 เช็กทอง
        if current_cash < price:
            await ctx.send(f"❌ **ทองไม่พอ!** คุณมีเงินเพียง `{current_cash}` ทอง แต่ยศนี้ราคา `{price}` ทองครับ")
            return

        guild = ctx.guild
        member = ctx.author
        role = discord.utils.get(guild.roles, name=role_name)

        # 🚫 เช็กว่าแอดมินสร้างยศรอไว้ในดิสคอร์ดหรือยัง
        if not role:
            await ctx.send(f"⚠️ **ระบบเซิร์ฟเวอร์ขัดข้อง:** ไม่พบยศชื่อ `{role_name}` ในเซิร์ฟเวอร์นี้ (กรุณาแจ้งให้แอดมินสร้างยศให้ตรงกัน)")
            return

        # 🚫 เช็กยศซ้ำซ้อนบนตัวผู้เล่น
        if role in member.roles:
            await ctx.send(f"🔰 คุณมี `{role_name}` ประดับอยู่บนตัวละครอยู่แล้วครับ!")
            return

        # 💸 ผ่านกฎทั้งหมด -> หักเงินใน DB และสั่งแจกยศดิสคอร์ดทันที
        new_cash = current_cash - price
        player_model.update_player_field(user_id, "cash", new_cash)

        try:
            await member.add_roles(role)
            await ctx.send(f"🎉 **ซื้อยศสำเร็จ!**\n🎖️ คุณได้รับยศ: **{role_name}** ติดตัวเรียบร้อยแล้ว!\n💸 เสียค่าธรรมเนียมสมาคม: `- {price}` ทอง (คงเหลือ: `{new_cash}` ทอง)")
        except discord.Forbidden:
            await ctx.send(f"❌ บอทไม่มีสิทธิ์จัดการยศ (Manage Roles) กรุณาตรวจสอบให้มั่นใจว่าลากยศของบอทให้อยู่สูงกว่ายศที่วางขายแล้วหรือยัง")
        except Exception as e:
            print(f"⚠️ เกิดข้อผิดพลาดในร้านค้าแบบพิมพ์: {e}")

    # ─── 📊 คำสั่งพิมพ์ดูโปรไฟล์ ───
    @commands.command(name="profile", aliases=["info"])
    async def profile(self, ctx, member: discord.Member = None):
        target_member = member if member else ctx.author
        player_data = player_model.get_player(target_member.id)
        
        embed = create_profile_embed(target_member, player_data)
        await ctx.send(embed=embed)

    # ─── ⚔️ คำสั่งเล่นเกมคอร์หลัก (ระบบแสดงผลเฉพาะคนใช้คำสั่ง - Ephemeral) ───
    @commands.hybrid_command(name="play", description="เริ่มออกเดินทางในโลก D&D MMORPG")
    async def play(self, ctx):
        # 💡 ระบบ Hybrid Command จะรองรับทั้งการพิมพ์ !play และ /play 
        # และเปิดทางให้ใช้คำสั่ง ctx.send(..., ephemeral=True) เพื่อซ่อนข้อความได้ทันทีครับ
        
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        # 🚫 [ระบบความปลอดภัยคนเล่นใหม่] ดักเช็กเผื่อไม่มีข้อมูลใน DB ให้ระบบแจ้งลงทะเบียนก่อน
        if not player:
            await ctx.send("❌ **ไม่พบข้อมูลตัวละครของคุณ!** กรุณาลงทะเบียนสร้างตัวละครก่อนครับ", ephemeral=True)
            return

        # 🟢 [ระบบดักเช็กยศออโต้] พิมพ์ !play ปุ๊บ ตรวจสอบแรงค์ตามเวลปัจจุบันทันที (ยศเก่าไม่ลบ)
        current_level = player.get("level", 1)
        _, current_rank = player_model.check_and_update_rank(user_id, current_level)
        
        guild = ctx.guild
        member = ctx.author
        
        if guild and isinstance(member, discord.Member):
            def get_eligible_ranks(lvl):
                eligible = ["F"]
                if lvl >= 5: eligible.append("E")
                if lvl >= 10: eligible.append("D")
                if lvl >= 20: eligible.append("C")
                if lvl >= 50: eligible.append("B")
                if lvl >= 80: eligible.append("A")
                if lvl >= 100: eligible.append("SSS")
                return eligible

            eligible_ranks = get_eligible_ranks(current_level)
            roles_to_add = []

            for r in eligible_ranks:
                role_name = f"นักผจญภัยแรงค์ {r}"
                role = discord.utils.get(guild.roles, name=role_name)
                if role and role not in member.roles:
                    roles_to_add.append(role)

            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add)
                    role_names_str = ", ".join([r.name for r in roles_to_add])
                    print(f"🏅 [Auto-Sync] เติมยศที่ขาดหายให้คุณ {member.name}: {role_names_str}")
                except discord.Forbidden:
                    print(f"❌ บอทไม่มีสิทธิ์จัดการยศ (Manage Roles) ตอนรันคำสั่ง !play")
                except Exception as e:
                    print(f"⚠️ เกิดข้อผิดพลาดในการซิงค์ยศตอน !play: {e}")

        # 🛑 [กฎเหล็ก] ถ้าอยู่ในสถานะต่อสู้/ตาย และเลือดหมดตัว (HP <= 0) บังคับสเตตัสเข้าลูปตายเกิดใหม่ทันที
        if player["current_state"] in ["fighting", "dead"] or player["hp"] <= 0:
            player_model.update_player_field(user_id, "current_state", "dead")
            
            embed = discord.Embed(
                title="💀 คุณพ่ายแพ้ในการต่อสู้และหมดสติลง...",
                description=f"วิญญาณของคุณยังล่องลอยอยู่กลางสนามรบ\n❤️ HP ของคุณ: `0/{player['max_hp']}`\n\n📌 กรุณากดปุ่มด้านล่างเพื่อฟื้นตัวและยอมรับบทลงโทษกลับหมู่บ้าน",
                color=0xe53e3e
            )
            from views.game_views import RespawnView
            # ส่งแผงเกิดใหม่แบบซ่อนข้อความเห็นคนเดียว
            await ctx.send(embed=embed, view=RespawnView(user_id), ephemeral=True)
            return 

        # 🚶 กรณีติดสถานะเลือก Choice อื่นๆ ค้างเฉยๆ เคลียร์สเตตัสกลับมาเริ่มเดินใหม่ได้
        lock_states = ["npc_choice", "treasure_choice", "dungeon_choice", "trap_defense", "village", "shopping"]
        if player["current_state"] in lock_states:
            player_model.update_player_field(user_id, "current_state", "idle")
            player = player_model.get_player(user_id)

        # หน้าตาแผงผจญภัยสำหรับผู้เล่นปกติทั่วไป
        embed = discord.Embed(
            title="⚔️ ยินดีต้อนรับสู่โลก D&D MMORPG",
            description=f"กระเป๋าเงินกลางของคุณ: `{player['cash']}` ทอง\nสถานะปัจจุบัน: `{player['current_state']}`",
            color=0x2b6cb0
        )
        
        # 🧭 [แก้ไขสำเร็จ] เปิดฉากส่งแผงผจญภัยแรกแบบกระซิบเห็นคนเดียวร้อยเปอร์เซ็นต์!
        from views.game_views import AdventureView
        await ctx.send(embed=embed, view=AdventureView(author_id=user_id), ephemeral=True)

# ฟังก์ชันสำหรับให้ตัวบอทหลักโหลด Cog นี้เข้าสู่ระบบ
async def setup(bot):
    await bot.add_cog(GameCommands(bot))