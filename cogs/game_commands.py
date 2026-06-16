import discord
from discord.ext import commands
import models.player_model as player_model
from views.profile_embed import create_profile_embed
from views.profile_embed import GAME_RACES, GAME_CLASSES

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 🎮 [คลีนระบบ] ถอดคำสั่งสั่งเริ่มทำงานของลูปแจก EXP และ Cooldown แชทออกทั้งหมดแล้ว (ย้ายไปโมดูลอื่นสำเร็จ)

    # ─── 🛒 คำสั่งเปิดร้านค้าและซื้อขายยศ + ระบบกาชาคู่ (สุ่มเผ่า/สุ่มคลาส) (!shop) ───
    @commands.command(name="shop")
    async def shop(self, ctx, action: str = None, item_num: int = None):
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        if not player:
            await ctx.send("❌ 不พบข้อมูลตัวละครของคุณ กรุณาพิมพ์ `!play` เพื่อลงทะเบียนก่อนครับ")
            return

        # 📋 คลังข้อมูลไอเทมในร้านค้า (ยศ 1-3 ปิดไว้ / เปิดกาชาเบอร์ 4 และ 5)
        shop_items = {
            # 1: {"name": "ขายยศ 1", "price": 10000, "type": "role"},
            # 2: {"name": "ขายยศ 2", "price": 50000, "type": "role"},
            # 3: {"name": "ขายยศ 3", "price": 100000, "type": "role"},
            4: {"name": "🎲 คัมภีร์กาชาสุ่มเปลี่ยนเผ่าพันธุ์", "price": 5000, "type": "gacha_race"},
            5: {"name": "🔮 คัมภีร์กาชาสุ่มเปลี่ยนคลาสอาชีพ", "price": 5000, "type": "gacha_class"} # 🔥 เพิ่มตู้คลาสตรงนี้
        }

        # 🛑 เคสที่ 1: พิมพ์ !shop เฉยๆ -> บอทเปิดใบรายการหน้าร้านให้ดู
        if action is None:
            embed = discord.Embed(
                title="🛒 สมาคมนักผจญภัย - ร้านค้าตราเกียรติยศ & ตู้กาชาเวทมนตร์",
                description=f"ยินดีต้อนรับคุณ **{ctx.author.name}** เข้าสู่หอเกียรติยศ\n💰 เงินคงเหลือปัจจุบัน: `{player.get('cash', 0)}` ทอง\n\n"
                            f"📌 **รายการสินค้าที่มีวางจำหน่าย:**\n"
                            f"🔸 **[4] 🎲 คัมภีร์กาชาสุ่มเปลี่ยนเผ่า** — ราคา `5,000` ทอง *(ลบเผ่าเก่า แอดเผ่าใหม่)*\n"
                            f"🔮 **[5] 🔮 คัมภีร์กาชาสุ่มเปลี่ยนคลาส** — ราคา `5,000` ทอง *(ลบกลุ่มคลาสเก่า แอดคลาสใหม่)*\n\n"
                            f"⌨️ **วิธีสั่งซื้อ:** พิมพ์คำสั่ง `!shop ซื้อ [เลขไอเทม]` (เช่น `!shop ซื้อ 5` เพื่อสุ่มอาชีพ)",
                color=0xecc94b
            )
            await ctx.send(embed=embed)
            return

        # 🛑 เคสที่ 2: พิมพ์คำสั่งซื้อแต่กรอกพารามิเตอร์ไม่ครบ
        if action not in ["ซื้อ", "buy"] or item_num is None:
            await ctx.send("❓ **รูปแบบคำสั่งไม่ถูกต้อง:** กรุณาพิมพ์ `!shop ซื้อ [เลขไอเทม]` เช่น `!shop ซื้อ 5` ครับ")
            return

        # 🛑 เคสที่ 3: กรอกเลขไอเทมที่ไม่มีในร้าน
        if item_num not in shop_items:
            await ctx.send("❌ **ไม่มีสินค้านี้ในระบบ:** ปัจจุบันระบบเปิดจำหน่ายเฉพาะหมายเลข 4 และ 5 เท่านั้นครับ")
            return

        item = shop_items[item_num]
        price = item["price"]
        current_cash = player.get("cash", 0)

        if current_cash < price:
            await ctx.send(f"❌ **ทองไม่พอ!** คุณมีเงินเพียง `{current_cash}` ทอง แต่ไอเทมนี้ราคา `{price}` ทองครับ")
            return

        guild = ctx.guild
        member = ctx.author
        import random

        # ==========================================================
        # 🎰 [ตู้กาชาเผ่า] เคสที่ 4: สุ่มเปลี่ยนเผ่าพันธุ์
        # ==========================================================
        if item["type"] == "gacha_race":
            new_cash = current_cash - price
            player_model.update_player_field(user_id, "cash", new_cash)
            new_race = random.choice(GAME_RACES)

            try:
                removed_races = []
                for race_name in GAME_RACES:
                    old_role = discord.utils.get(guild.roles, name=race_name)
                    if old_role and old_role in member.roles:
                        await member.remove_roles(old_role)
                        removed_races.append(race_name)

                new_role = discord.utils.get(guild.roles, name=new_race)
                if not new_role:
                    await ctx.send(f"⚠️ **ระบบขัดข้อง:** สุ่มได้เผ่า `{new_race}` แต่ไม่พบชื่อยศนี้ในดิสคอร์ด")
                    return

                await member.add_roles(new_role)
                removed_msg = f" (ปลดเผ่าเดิม: `{removed_races[0]}` ออกแล้ว)" if removed_races else ""
                await ctx.send(
                    f"🎰🔮 **[ตู้กาชาโบราณ]** คุณ {member.mention} ได้ฉีกคัมภีร์สุ่มเผ่าพันธุ์สำเร็จ!\n"
                    f"🧬 พรแห่งโชคชะตาเปลี่ยนร่างของคุณเป็น: **{new_race}** ✨{removed_msg}\n"
                    f"💸 เสียค่าธรรมเนียมกาชา: `- {price}` ทอง (คงเหลือ: `{new_cash}` ทอง)"
                )
            except discord.Forbidden:
                await ctx.send(f"❌ บอทไม่มีสิทธิ์จัดการยศ กรุณาลากยศบอทให้อยู่สูงกว่ายศเผ่าพันธุ์ทั้งหมด")
            except Exception as e:
                print(f"⚠️ เกิดข้อผิดพลาดในกาชาเผ่า: {e}")
            return

        # ==========================================================
        # 🔮 [ตู้กาชาคลาส] เคสที่ 5: สุ่มเปลี่ยนคลาสอาชีพ (เวอร์ชันเช็ก/สลับยศบนดิสคอร์ด 100%)
        # ==========================================================
        if item["type"] == "gacha_class":
            # 1. หักเงินใน DB ตามปกติ
            new_cash = current_cash - price
            player_model.update_player_field(user_id, "cash", new_cash)
            
            # 2. สุ่มคลาสอาชีพใหม่จากลิสต์ในไฟล์ profile_embed
            new_class = random.choice(GAME_CLASSES)

            try:
                removed_classes = []
                # 🛡️ 3. ลอจิกเคลียร์ยศคลาสอาชีพเก่าทั้งหมดออกจากตัวผู้เล่นบนดิสคอร์ด
                for class_name in GAME_CLASSES:
                    old_role = discord.utils.get(guild.roles, name=class_name)
                    if old_role and old_role in member.roles:
                        await member.remove_roles(old_role)
                        removed_classes.append(class_name)

                # 4. มอบยศคลาสอาชีพใหม่ให้ผู้เล่นบนดิสคอร์ด
                new_role = discord.utils.get(guild.roles, name=new_class)
                if not new_role:
                    await ctx.send(f"⚠️ **ระบบขัดข้อง:** สุ่มได้คลาส `{new_class}` แต่ไม่พบชื่อยศนี้ในดิสคอร์ด")
                    return

                await member.add_roles(new_role)
                
                # ❌ [ลบออกแล้ว!] บรรทัด player_model.update_player_field(user_id, "class", new_class) ถูกเอาออกถาวรเพื่อไม่ให้เกิด Error column class

                # 5. ประกาศผลลัพธ์ลงแชท
                removed_msg = f" (สละอาชีพเดิม: `{removed_classes[0]}` เคลียร์ออกเรียบร้อย)" if removed_classes else ""
                await ctx.send(
                    f"🔮✨ **[แท่นทำนายวิญญาณ]** คุณ {member.mention} ได้เบิกเนตรสุ่มคลาสอาชีพใหม่สำเร็จ!\n"
                    f"⚔️ จิตวิญญาณแห่งการต่อสู้เลือกให้คุณเป็นคลาส: **{new_class}** 🛡️{removed_msg}\n"
                    f"💸 เสียค่าธูปทำนายวิญญาณ: `- {price}` ทอง (คงเหลือ: `{new_cash}` ทอง)"
                )
            except discord.Forbidden:
                await ctx.send(f"❌ บอทไม่มีสิทธิ์จัดการยศ กรุณาลากยศบอทให้อยู่สูงกว่ายศคลาสอาชีพทั้งหมดด้วยครับ")
            except Exception as e:
                print(f"⚠️ เกิดข้อผิดพลาดในกาชาคลาส: {e}")
            return

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