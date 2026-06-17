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
            f"🛡️ Status สิทธิ์: {'✅ ผ่าน (Authorized)' if has_permission else '❌ บล็อกระบบ (Blocked)'}\n"
            f"--------------------------------------------------"
        )

        # 🖥️ สั่งพิมพ์ข้อความลงหน้าจอ Terminal ทันที
        print(log_text)

        # 🛑 ถ้าสิทธิ์ไม่ผ่าน ให้บล็อกไม่ให้คำสั่งทำงาน
        if not has_permission:
            return False
        return True

    # ─── 💰 1. คำสั่งเซ็ตเงินติดตัว (!set_cash แบบแปรผัน บวกลบตามค่า) ───
    @commands.command(name="set_cash")
    async def set_cash(self, ctx, target: discord.User = None, amount: int = None):
        print(f"🪙 [CASH ADMIN DEBUG] แอดมิน {ctx.author.name} เรียกใช้คำสั่ง !set_cash | target: {target} | amount: {amount}")

        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_cash [@ชื่อผู้เล่น หรือ ID] [จำนวน]`\n*(ตัวอย่าง: ใส่ `200` เพื่อบวกเพิ่ม / ใส่ `-200` เพื่อหักเงินออก)*")
            return
            
        user_id = target.id
        name = target.display_name

        player = player_model.get_player(user_id)
        if not player:
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครของ **{name}** ในฐานข้อมูล")
            return
            
        current_cash = player.get("cash", 0)
        new_cash = current_cash + amount
        
        if new_cash < 0:
            new_cash = 0

        player_model.update_player_field(user_id, "cash", new_cash)
        
        if amount >= 0:
            await ctx.send(f"⚡ **[Admin]** ได้เพิ่มทองให้กับ **{name}** จำนวน `+ {amount:,}` ทอง\n🪙 (เงินสดปัจจุบัน: `{new_cash:,}` ทอง) 📈💸")
        else:
            await ctx.send(f"⚡ **[Admin]** ได้หักทองของ **{name}** ออกจำนวน `- {abs(amount):,}` ทอง\n🪙 (เงินสดปัจจุบัน: `{new_cash:,}` ทอง) 📉💸")

    # ─── 🩸 2. คำสั่งเซ็ตเลือดปัจจุบัน (!set_hp) ───
    @commands.command(name="set_hp")
    async def set_hp(self, ctx, target: discord.User = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_hp [@ชื่อผู้เล่น หรือ ID] [จำนวน]`")
            return
        user_id = target.id
        name = target.display_name
        if not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "hp", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนค่าพลังชีวิต (HP) ของ **{name}** เป็น `{amount:,}` HP เรียบร้อยแล้วครับ! 🩸")

    # ─── 🧪 3. คำสั่งเซ็ตเลือดสูงสุด (!set_max_hp) ───
    @commands.command(name="set_max_hp")
    async def set_max_hp(self, ctx, target: discord.User = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_max_hp [@ชื่อผู้เล่น หรือ ID] [จำนวน]`")
            return
        user_id = target.id
        name = target.display_name
        if not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "max_hp", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนขีดจำกัดเลือดสูงสุด (Max HP) ของ **{name}** เป็น `{amount:,}` Max HP เรียบร้อยแล้วครับ! 🧪")

    # ─── 🛡️ 4. คำสั่งเซ็ตค่าเกราะ (!set_armor) ───
    @commands.command(name="set_armor")
    async def set_armor(self, ctx, target: discord.User = None, amount: str = "None"):
        if target is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_armor [@ชื่อผู้เล่น หรือ ID] [ชื่อคีย์เวิร์ดเกราะ]`")
            return
        user_id = target.id
        name = target.display_name
        if not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "armor", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนชุดเกราะของ **{name}** เป็นคีย์ `{amount}` เรียบร้อยแล้วครับ! 🛡️")

    # ─── 📈 5. คำสั่งเซ็ตค่า EXP (!set_exp) ───
    @commands.command(name="set_exp")
    async def set_exp(self, ctx, target: discord.User = None, amount: int = None):
        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_exp [@ชื่อผู้เล่น หรือ ID] [จำนวน EXP]`")
            return
        user_id = target.id
        name = target.display_name
        if not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "exp", amount)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนค่า EXP ของ **{name}** เป็น `{amount:,}` EXP เรียบร้อยแล้วครับ! 🎯")

    # ─── 🎖️ 6. คำสั่งเซ็ตแรงค์ (!set_rank) ───
    @commands.command(name="set_rank")
    async def set_rank(self, ctx, target: discord.User = None, *, rank_name: str = None):
        if target is None or rank_name is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_rank [@ชื่อผู้เล่น หรือ ID] [ชื่อแรงค์]`")
            return
        user_id = target.id
        name = target.display_name
        if not player_model.get_player(user_id):
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครในฐานข้อมูล")
            return
        player_model.update_player_field(user_id, "rank", rank_name)
        await ctx.send(f"⚡ **[Admin]** ปรับเปลี่ยนตำแหน่งแรงค์ของ **{name}** เป็น **\"{rank_name}\"** เรียบร้อยแล้วครับ! 🎖️")
    
    # ─── 🏦 7. คำสั่งแอดมิน: เซ็ตเงินในธนาคาร (!set_bank บวกลบตามค่า) ───
    @commands.command(name="set_bank")
    async def set_bank(self, ctx, target: discord.User = None, amount: int = None):
        print(f"🏦 [BANK ADMIN DEBUG] แอดมิน {ctx.author.name} เรียกใช้คำสั่ง !set_bank | target: {target} | amount: {amount}")

        if target is None or amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_bank [@ชื่อผู้เล่น หรือ ID] [จำนวน]`\n*(ตัวอย่าง: ใส่ `500` เพื่อฝากเพิ่ม / ใส่ `-500` เพื่อหักเงินฝากออก)*")
            return
            
        user_id = target.id
        name = target.display_name

        player = player_model.get_player(user_id)
        if not player:
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครของ **{name}** ในฐานข้อมูล")
            return
            
        current_bank = player.get("bank", 0)
        new_bank = current_bank + amount
        
        if new_bank < 0:
            new_bank = 0

        player_model.update_player_field(user_id, "bank", new_bank)
        print(f"💾 [BANK ADMIN DEBUG] อัปเดตเงินในบัญชี {name} สำเร็จ: {current_bank:,} -> {new_bank:,} ทอง")
        
        if amount >= 0:
            await ctx.send(f"⚡ **[Admin]** ได้เพิ่มเงินฝากในธนาคารให้กับ **{name}** จำนวน `+ {amount:,}` ทอง\n🏦 (เงินฝากปัจจุบัน: `{new_bank:,}` ทอง) 📈💳")
        else:
            await ctx.send(f"⚡ **[Admin]** ได้ยึด/หักเงินฝากในธนาคารของ **{name}** ออกจำนวน `- {abs(amount):,}` ทอง\n🏦 (เงินฝากปัจจุบัน: `{new_bank:,}` ทอง) 📉💳")

    # ─── 🧹 8. คำสั่งแอดมิน: เคลียร์ข้อมูลเฉพาะส่วน (รายบุคคล / ทั้งเซิร์ฟเวอร์) ───
    @commands.command(name="reset_player")
    async def reset_player(self, ctx, scope: str = None, target: str = None, confirm: str = None):
        print(f"🧹 [RESET DEBUG] แอดมิน {ctx.author.name} เรียกใช้คำสั่ง !reset_player | scope: {scope}, target: {target}, confirm: {confirm}")

        valid_scopes = ["cash", "bank", "level", "rank", "all_data"]
        if not scope or scope.lower() not in valid_scopes or not target:
            embed_help = discord.Embed(
                title="🧹 วิธีใช้งานคำสั่ง !reset_player (เฉพาะแอดมิน)",
                description=(
                    "**📌 เคลียร์เฉพาะบุคคล:**\n"
                    "`!reset_player [ประเภท] [@ชื่อผู้เล่น หรือ ID]`\n"
                    "*ตัวอย่าง: `!reset_player cash @Arthur`*\n\n"
                    "**🚨 เคลียร์ทั้งเซิร์ฟเวอร์ (ล้างกระดาน):**\n"
                    "`!reset_player [ประเภท] all ยืนยัน`\n"
                    "*ตัวอย่าง: `!reset_player level all ยืนยัน`*\n\n"
                    "**📋 ประเภทการเคลียร์ (Scope):**\n"
                    "🔹 `cash` : รีเซ็ตเงินสดติดตัวเป็น 0 ทอง\n"
                    "🔹 `bank` : รีเซ็ตเงินในธนาคารเป็น 0 ทอง\n"
                    "🔹 `level` : รีเซ็ตเลเวลเป็น 1 และ EXP เป็น 0\n"
                    "🔹 `rank` : ปลดชั้นยศ Rank (F-SSS) ทั้งหมดออกจากตัวในดิสคอร์ด และเซ็ตค่าใน DB กลับเป็น F\n"
                    "🔹 `all_data` : ล้างทุกอย่างข้างต้นกลับไปจุดเริ่มต้นเหมือนไอดีเกิดใหม่ซิง ๆ"
                ),
                color=0xe53e3e
            )
            await ctx.send(embed=embed_help)
            return

        scope = scope.lower()
        target = target.lower()
        guild = ctx.guild

        rank_roles_names = [
            "• นักผจญภัยแรงค์ F",
            "• นักผจญภัยแรงค์ E",
            "• นักผจญภัยแรงค์ D",
            "• นักผจญภัยแรงค์ C",
            "• นักผจญภัยแรงค์ B",
            "• นักผจญภัยแรงค์ A",
            "• นักผจญภัยแรงค์ S 🗺️",
            "• นักผจญภัยแรงค์ SS 💰",
            "• นักผจญภัยแรงค์ SSS 👑"
        ]

        # ==========================================================
        # 🚨 [CASE 1]: รีเซ็ตทั้งเซิร์ฟเวอร์ (Target == 'all') แบบพิมพ์เช็กละเอียด
        # ==========================================================
        print(f"\n🔍 [RESET ALL DEBUG - STEP 1] เช็กค่าเปรียบเทียบก่อนเข้าเงื่อนไข:")
        print(f"👉 scope ตัวพิมพ์เล็ก: '{scope}'")
        print(f"👉 target ตัวพิมพ์เล็ก: '{target}'")
        print(f"👉 confirm คีย์เวิร์ด: '{confirm}'")

        if target == "all":
            print(f"🎯 [RESET ALL DEBUG - STEP 2] ผ่านเข้าบล็อก target == 'all' สำเร็จ")
            
            if confirm != "ยืนยัน":
                print(f"❌ [RESET ALL DEBUG - STEP 2.1] หลุดคัดกรอง: คำยืนยันไม่ถูกต้อง (กรอกมาคือ: '{confirm}')")
                await ctx.send("⚠️ **โปรดตรวจสอบคีย์เวิร์ด:** หากต้องการรีเซ็ตข้อมูล**ทั้งเซิร์ฟเวอร์** กรุณาพิมพ์คำว่า `ยืนยัน` ปิดท้ายคำสั่งด้วยครับ\n*(เช่น `!reset_player cash all ยืนยัน`)*")
                return

            print(f"🚀 [RESET ALL DEBUG - STEP 3] ผ่านการเช็กตัวคีย์เวิร์ดยืนยันแล้ว กำลังเข้าเช็กประเภท scope...")
            await ctx.send(f"⏳ **[System]** กำลังเริ่มกระบวนการล้างข้อมูลประเภท `{scope}` ของผู้เล่นทุกคนในเซิร์ฟเวอร์...")

            if scope == "cash":
                print("🪙 [RESET ALL DEBUG] เริ่มระบบล้างเงินสดติดตัว (cash) ทั้งเซิร์ฟ...")
                player_model.execute_raw_sql("UPDATE players SET cash = 0, bank = 0;")
                await ctx.send("✅ **[Reset All]** เคลียร์**เงินสดและเงินในธนาคาร**ของผู้เล่นทุกคนเป็น `0` ทอง เรียบร้อยแล้ว! 🪙💥")

            elif scope == "bank":
                print("💳 [RESET ALL DEBUG] เริ่มระบบล้างเงินในคลังบัญชี (bank) ทั้งเซิร์ฟ...")
                player_model.execute_raw_sql("UPDATE players SET bank = 0;")
                await ctx.send("✅ **[Reset All]** เคลียร์**เงินในธนาคาร**ของผู้เล่นทุกคนเป็น `0` ทอง เรียบร้อยแล้ว! 💳💥")

            elif scope == "level":
                print("📈 [RESET ALL DEBUG] เริ่มระบบรีเวล (level) ทั้งเซิร์ฟ...")
                player_model.execute_raw_sql("UPDATE players SET level = 1, exp = 0;")
                await ctx.send("✅ **[Reset All]** รีเซ็ตเลเวลเป็น `Lv.1` และเคลียร์ค่า `EXP = 0` ของทุกคนเรียบร้อยแล้ว! 📈💥")

            elif scope == "rank":
                print("🎖️ [RESET ALL DEBUG] เริ่มระบบล้างแต้มยศ (rank) ทั้งเซิร์ฟ...")
                player_model.execute_raw_sql("UPDATE players SET rank = 'F';")
                
                print("👼 [RESET ALL DEBUG] กำลังเริ่มกวาดถอดยศ Rank ออกจากสมาชิกในดิสคอร์ด...")
                for role_name in rank_roles_names:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        for member in role.members:
                            try: await member.remove_roles(role)
                            except: pass
                await ctx.send(f"✅ **[Reset All]** เซ็ตค่า Rank ใน DB กลับเป็น F และสั่งปลดยศกลุ่ม Rank (F-SSS) ออกจากสมาชิกรวดเดียวสำเร็จ! 🎖️❌")

            elif scope == "all_data":
                print("🔥 [RESET ALL DEBUG - STEP 4] พบคีย์เวิร์ด 'all_data' ! เริ่มกระบวนการถล่มตารางฐานข้อมูล...")
                
                try:
                    import sqlite3
                    # 🔌 1. เปิดการเชื่อมต่อตรงดิ่งไปที่ไฟล์ฐานข้อมูล (แก้ชื่อไฟล์ DB ให้ตรงกับเครื่องของคุณอาเธอร์ เช่น game_data.db หรือ database.db)
                    db_name = getattr(player_model, "DB_NAME", "game_data.db") # ดึงชื่อไฟล์จากโมเดล หรือใช้ค่า Default
                    conn = sqlite3.connect(db_name)
                    cursor = conn.cursor()
                    
                    # 💥 2. รันคำสั่งกวาดล้างข้อมูลผู้เล่นเกลี้ยงตาราง
                    print("🧹 [RESET ALL DEBUG - STEP 4.1] กำลังยิงคำสั่ง: DELETE FROM players;")
                    cursor.execute("DELETE FROM players;")
                    
                    # 🧼 3. รีเซ็ตตัวนับ ID (AUTOINCREMENT) ให้กลับไปนับ 1 ใหม่
                    print("🧼 [RESET ALL DEBUG - STEP 4.3] กำลังเคลียร์ตัวนับ ID ตาราง...")
                    try:
                        cursor.execute("DELETE FROM sqlite_sequence WHERE name='players';")
                    except:
                        pass
                        
                    # บันทึกการเปลี่ยนแปลงและปิดการเชื่อมต่อ
                    conn.commit()
                    conn.close()
                    print("✅ [RESET ALL DEBUG - STEP 4.4] เคลียร์ฐานข้อมูลเกลี้ยงตารางสำเร็จ!")

                    # 👑 4. สั่งปลดยศในดิสคอร์ดค้างไว้เหมือนเดิม
                    print("👑 [RESET ALL DEBUG - STEP 4.5] กำลังเริ่มลูปปลดยศ Rank บนหัวทุกคนในดิสคอร์ด...")
                    success_roles_count = 0
                    for role_name in rank_roles_names:
                        role = discord.utils.get(guild.roles, name=role_name)
                        if role:
                            for member in role.members:
                                try: 
                                    await member.remove_roles(role)
                                    success_roles_count += 1
                                except: 
                                    pass
                    print(f"✅ [RESET ALL DEBUG - STEP 4.6] ลูปถอดยศเสร็จสิ้น ถอดไปทั้งหมด {success_roles_count} ครั้ง")

                    await ctx.send("🔥 **[RESET GRAND CHAMPION]** สั่งล้างฐานข้อมูลผู้เล่นเกลี้ยงตาราง `DELETE FROM players;` พร้อมเคลียร์ยศ Rank F-SSS ออกจากดิสคอร์ด ต้อนรับซีซันใหม่อย่างเป็นทางการเรียบร้อยแล้วครับ!")
                    print("📢 [RESET ALL DEBUG - STEP 4.7] ส่งข้อความประกาศความสำเร็จลงแชทเรียบร้อย!")

                except Exception as sql_error:
                    print(f"💥 [RESET ALL CRITICAL ERROR] โค้ดฝั่ง SQL ระเบิดคามือ: {sql_error}")
                    await ctx.send(f"⚠️ **ระบบล้างตารางขัดข้องเนื่องจาก:** `{sql_error}`")
            
            else:
                print(f"❓ [RESET ALL DEBUG] โค้ดวิ่งมาถึงทางตันเนื่องจากไม่รู้จักคีย์เวิร์ดสล็อต scope: '{scope}'")
            
            return

        # ==========================================================
        # 👤 [CASE 2]: รีเซ็ตรายบุคคล (Target == ID/Tag)
        # ==========================================================
        # ดึงสิทธิ์แปลงไอดีด้วยระบบแปลงของตัวดิสคอร์ดแบบแมนนวลกรณีพิมพ์ข้อความดิบ
        clean_id = target.replace("<@", "").replace(">", "").replace("!", "")
        if not clean_id.isdigit():
            await ctx.send("❌ **ไม่พบผู้เล่น:** กรุณาระบุเป็น Tag `@ชื่อผู้เล่น` หรือกรอก `Discord ID` ให้ถูกต้องครับ")
            return
            
        user_id = int(clean_id)
        member = guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        name = member.display_name if member else f"User ID: {user_id}"

        player = player_model.get_player(user_id)
        if not player:
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครของ **{name}** ในฐานข้อมูล")
            return

        if scope == "cash":
            player_model.update_player_field(user_id, "cash", 0)
            await ctx.send(f"🧹 **[Reset]** เคลียร์**เงินสดติดตัว**ของ **{name}** กลับเป็น `0` ทอง เรียบร้อยแล้วครับ 🪙")

        elif scope == "bank":
            player_model.update_player_field(user_id, "bank", 0)
            await ctx.send(f"🧹 **[Reset]** เคลียร์**เงินในธนาคาร**ของ **{name}** กลับเป็น `0` ทอง เรียบร้อยแล้วครับ 💳")

        elif scope == "level":
            player_model.update_player_field(user_id, "level", 1)
            player_model.update_player_field(user_id, "exp", 0)
            await ctx.send(f"🧹 **[Reset]** รีเซ็ตเลเวลของ **{name}** กลับเป็น `Lv.1` (EXP: 0) เรียบร้อยแล้วครับ ⚔️")

        elif scope == "rank":
            player_model.update_player_field(user_id, "rank", "F")
            removed_ranks = []
            if member and isinstance(member, discord.Member):
                for role_name in rank_roles_names:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role in member.roles:
                        try:
                            await member.remove_roles(role)
                            removed_ranks.append(role_name)
                        except discord.Forbidden:
                            await ctx.send("❌ บอทไม่มีสิทธิ์ถอดยศ กรุณาเช็กเลเยอร์ยศของบอทให้สูงกว่ากลุ่มยศ Rank ครับ")
                            return
            msg_rank = f" และปลดยศ Rank `{', '.join(removed_ranks)}` ออกจากตัวแล้ว" if removed_ranks else " (ผู้เล่นไม่มียศ Rank ติดตัวอยู่แล้ว)"
            await ctx.send(f"🧹 **[Reset]** เซ็ตค่าฐานข้อมูลกลับเป็น Rank F{msg_rank} เรียบร้อยครับ 🎖️❌")

        elif scope == "all_data":
            player_model.update_player_field(user_id, "cash", 0)
            player_model.update_player_field(user_id, "bank", 0)
            player_model.update_player_field(user_id, "level", 1)
            player_model.update_player_field(user_id, "exp", 0)
            player_model.update_player_field(user_id, "rank", "F")
            
            if member and isinstance(member, discord.Member):
                for role_name in rank_roles_names:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role in member.roles:
                        try: await member.remove_roles(role)
                        except: pass
            await ctx.send(f"💥 **[Reset All Data]** ข้อมูลทั้งหมดของ **{name}** ถูกล้างกลับสู่จุดเริ่มต้น และล้างยศ Rank เดิมออกเรียบร้อยแล้วครับ!")

        print(f"✅ [RESET INDIVIDUAL SUCCESS] ล้างข้อมูลของ {name} ประเภท {scope} สำเร็จ")

    # ─── 🔮 9. คำสั่งเซ็ตสถานะทั่วไป (!set_state) ───
    @commands.command(name="set_state")
    async def set_state(self, ctx, target: discord.User = None, state: str = "idle"):
        if target is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!set_state [@ชื่อผู้เล่น] [ชื่อสถานะ (เช่น idle/dungeon/rest)]`")
            return
            
        user_id = target.id
        name = target.display_name
        player_model.update_player_field(user_id, "current_state", state)
        await ctx.send(f"🔮 **[Admin]** ได้ปรับสถานะตัวละครของ **{name}** เป็น `{state}` เรียบร้อยแล้วครับ! (แก้อาการตัวค้าง)")

    # ─── 🎒 10. คำสั่งล้างกระเป๋าไอเทม (!clear_inventory) ───
    @commands.command(name="clear_inventory")
    async def clear_inventory(self, ctx, target: str = None, confirm: str = None):
        if target is None:
            await ctx.send("❓ **วิธีใช้งาน:** \nรายคน: `!clear_inventory [@ชื่อผู้เล่น]`\nทั้งเซิร์ฟ: `!clear_inventory all ยืนยัน`")
            return

        if target.lower() == "all":
            if confirm != "ยืนยัน":
                await ctx.send("⚠️ กรุณาพิมพ์ `ยืนยัน` ต่อท้ายเพื่อล้างกระเป๋าผู้เล่นทุกคน")
                return
            player_model.execute_raw_sql("UPDATE players SET inventory = '[]';")
            await ctx.send("🔥 **[Reset Inventory]** ล้างกระเป๋าไอเทมของผู้เล่นทุกคนในเซิร์ฟเวอร์เกลี้ยงแล้วครับ!")
            return

        clean_id = target.replace("<@", "").replace(">", "").replace("!", "")
        if clean_id.isdigit():
            user_id = int(clean_id)
            player_model.update_player_field(user_id, "inventory", "[]")
            await ctx.send(f"🧹 ล้างไอเทมในกระเป๋าของ ID `{user_id}` จนโล่งเรียบร้อยแล้วครับ!")

    # ─── 🪙 11. คำสั่งแจกเงินกิจกรรมทุกคนในฐานข้อมูล (!give_cash_all) ───
    @commands.command(name="give_cash_all")
    async def give_cash_all(self, ctx, amount: int = None):
        if amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!give_cash_all [จำนวนทอง]`")
            return
        
        # ตรวจสอบว่าโมเดลมีการ commit หรือไม่
        sql = f"UPDATE players SET cash = cash + {amount}"
        player_model.execute_raw_sql(sql)
        await ctx.send(f"📢 **[ประกาศ]** แจกทองทุกคนคนละ `{amount:,}` ทอง!")

    
    @commands.command(name="give_bank_all")
    async def give_bank_all(self, ctx, amount: int = None):
        if amount is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!give_bank_all [จำนวนทอง]`")
            return
        
        sql = f"UPDATE players SET bank = bank + {amount}"
        print(f"🪙 [ADMIN LOG] แจกเงินผู้เล่นทุกคนคนละ +{amount:,} ทอง")
        player_model.execute_raw_sql(sql)
        await ctx.send(f"📢 **[ประกาศจากสมาคม]** ท่านแอดมินได้ทำการแจกทองให้กับนักผจญภัยทุกคนในฐานข้อมูล จำนวน `+ {amount:,}` ทอง! 🪙✨")

    # ─── 🚫 12. คำสั่งแอดมิน: สั่งจับกุมแบบกำหนดเวลา / ปลดปล่อยผู้เล่น (!arrest) ───
    @commands.command(name="arrest")
    async def arrest(self, ctx, target: discord.User = None, duration_mins: int = None):
        import time
        print(f"\n🔍 [ARREST STEP 1] เริ่มฟังก์ชัน !arrest | target: {target} | duration_mins: {duration_mins}")

        if target is None or duration_mins is None:
            print("❌ [ARREST STEP 1.1] หลุดเงื่อนไข: กรอกพารามิเตอร์ไม่ครบ (เป็น None)")
            await ctx.send("❓ **วิธีใช้งาน:**\n🚨 สั่งจับกุม: `!arrest [@ชื่อผู้เล่น] [จำนวนนาที]` *(เช่น `!arrest @Arthur 30`)*\n🔓 ปลดปล่อยทันที: `!arrest [@ชื่อผู้เล่น] 0`")
            return

        user_id = target.id
        name = target.display_name
        print(f"🆔 [ARREST STEP 2] แปลง User สำเร็จ -> ชื่อ: {name} | ID: {user_id}")

        try:
            print("🗄️ [ARREST STEP 3] กำลังดึงข้อมูลผู้เล่นจากฐานข้อมูล...")
            player = player_model.get_player(user_id)
            print(f"📦 [ARREST STEP 3.1] ข้อมูลที่ได้จาก DB: {player}")

            if not player:
                print(f"❌ [ARREST STEP 3.2] หลุดเงื่อนไข: ไม่พบข้อมูลไอดี {user_id} ใน Database")
                await ctx.send(f"❌ ไม่พบข้อมูลตัวละครของ **{name}** ในฐานข้อมูล (ผู้เล่นต้องพิมพ์ `!play` ก่อน)")
                return

            if duration_mins <= 0:
                print("🔓 [ARREST STEP 4] เข้าสู่เงื่อนไขปลดปล่อยตัว (เวลาน้อยกว่าหรือเท่ากับ 0)")
                player_model.update_player_field(user_id, "current_state", "idle")
                player_model.update_player_field(user_id, "arrest_until", 0)
                await ctx.send(f"🔓 **[กองปราบปราม]** นักผจญภัย **{name}** ได้รับการปล่อยตัวเป็นอิสระแล้ว! 🕊️✨")
                return

            print("🚨 [ARREST STEP 5] เข้าสู่เงื่อนไขสั่งขังคุกตามเวลา")
            current_timestamp = int(time.time())
            release_timestamp = current_timestamp + (duration_mins * 60)

            player_model.update_player_field(user_id, "current_state", "arrested")
            player_model.update_player_field(user_id, "arrest_until", release_timestamp)

            await ctx.send(
                f"🚨 **[กองปราบปราม]** นักผจญภัย **{name}** ถูกสั่ง **จับกุมควบคุมตัว** เป็นเวลา `{duration_mins}` นาที! 🔗⛓️\n"
                f"🚫 จะไม่สามารถใช้คำสั่งใดๆ ของบอทได้จนกว่าจะครบกำหนดเวลา!"
            )

        except Exception as e:
            print(f"💥 [ARREST CRITICAL ERROR] โค้ดระเบิดภายในฟังก์ชัน: {e}")
            await ctx.send(f"⚠️ **ระบบหลังบ้านขัดข้อง:** เกิดข้อผิดพลาดตัวแปรระเบิด `({e})` กรุณาแจ้งแอดมินเช็กด่วน")
    # ==========================================================
    # 🏅 [COMMAND]: !add_role [ยศ] [ผู้เล่น หรือ all] (เวอร์ชันเสถียร 100%)
    # ==========================================================
    @commands.command(name="add_role")
    @commands.has_permissions(administrator=True)
    async def add_role_command(self, ctx, role: discord.Role = None, target: str = None):
        """คำสั่งแอดมิน: แจกยศให้ผู้เล่นรายคน หรือทุกคนในเซิร์ฟเวอร์ (!add_role @ยศ @ชื่อคน/all)"""
        if role is None or target is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!add_role [@แท็กยศ หรือ ชื่อยศ] [@แท็กผู้เล่น หรือ ID หรือ all]`")
            return

        guild = ctx.guild
        role_name = role.name

        # 👥 [CASE 1]: แจกยศให้ทุกคนในเซิร์ฟเวอร์ (target == "all")
        if target.lower() == "all":
            await ctx.send(f"⏳ **[System]** กำลังเริ่มกระบวนการแจกยศ `{role_name}` ให้แก่สมาชิกทุกคนในเซิร์ฟเวอร์ (อาจใช้เวลาสักครู่)...")
            success_count = 0
            
            for member in guild.members:
                if member.bot: 
                    continue
                if role not in member.roles:
                    try:
                        await member.add_roles(role)
                        success_count += 1
                    except:
                        pass
            
            await ctx.send(f"✅ **[Role All Success]** แจกยศ **{role_name}** ให้แก่ผู้เล่นทุกคนสำเร็จรวมทั้งหมด `{success_count}` คนเรียบร้อยแล้วครับ! 👑")
            print(f"🏅 [ADMIN ROLE] แจกยศ {role_name} ให้ทุกคนสำเร็จ ({success_count} คน)")

        # 👤 [CASE 2]: แจกยศให้ผู้เล่นรายคน
        else:
            try:
                converter = commands.MemberConverter()
                member = await converter.convert(ctx, target)
            except:
                await ctx.send("❌ **ไม่พบผู้เล่น:** กรุณาทำการแท็ก `@ผู้เล่น` หรือใส่ `Discord ID` ให้ถูกต้องครับ")
                return

            if role in member.roles:
                await ctx.send(f"⚠️ ผู้เล่น **{member.display_name}** มีสิทธิ์ยศ `{role_name}` อยู่แล้วครับ")
                return

            try:
                await member.add_roles(role)
                await ctx.send(f"✅ แจกยศ **{role_name}** ให้แก่ **{member.mention}** เรียบร้อยแล้วครับ! ⚔️")
                print(f"🏅 [ADMIN ROLE] แจกยศ {role_name} ให้แก่ {member.name} สำเร็จ")
            except discord.Forbidden:
                await ctx.send("❌ **บอทไม่มีสิทธิ์จัดการยศ:** ยศของบอทอยู่ต่ำกว่ายศที่ต้องการแจก กรุณาลากยศของบอทให้สูงขึ้นในตารางตั้งค่ายศของดิสคอร์ดครับ")
            except Exception as e:
                await ctx.send(f"⚠️ เกิดข้อผิดพลาด: `{e}`")

    # ==========================================================
    # ❌ [COMMAND]: !remove_role [ยศ] [ผู้เล่น หรือ all] (เวอร์ชันเสถียร 100%)
    # ==========================================================
    @commands.command(name="remove_role")
    @commands.has_permissions(administrator=True)
    async def remove_role_command(self, ctx, role: discord.Role = None, target: str = None):
        """คำสั่งแอดมิน: ริบยศคืนจากผู้เล่นรายคน หรือทุกคนในเซิร์ฟเวอร์ (!remove_role @ยศ @ชื่อคน/all)"""
        if role is None or target is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!remove_role [@แท็กยศ หรือ ชื่อยศ] [@แท็กผู้เล่น หรือ ID หรือ all]`")
            return

        guild = ctx.guild
        role_name = role.name

        # 👥 [CASE 1]: ลบยศออกจากทุกคนในเซิร์ฟเวอร์ (target == "all")
        if target.lower() == "all":
            await ctx.send(f"⏳ **[System]** กำลังเริ่มกระบวนการลบยศ `{role_name}` ออกจากสมาชิกทุกคนในเซิร์ฟเวอร์...")
            success_count = 0
            
            for member in role.members:
                if member.bot: 
                    continue
                try:
                    await member.remove_roles(role)
                    success_count += 1
                except:
                    pass
            
            await ctx.send(f"🧹 **[Remove Role All Success]** ทำการริบยศ **{role_name}** ออกจากสมาชิกทุกคนสำเร็จรวมทั้งหมด `{success_count}` คนเรียบร้อยแล้วครับ!")
            print(f"❌ [ADMIN ROLE] ลบยศ {role_name} ออกจากทุกคนสำเร็จ ({success_count} คน)")

        # 👤 [CASE 2]: ลบยศออกรายบุคคล
        else:
            try:
                converter = commands.MemberConverter()
                member = await converter.convert(ctx, target)
            except:
                await ctx.send("❌ **ไม่พบผู้เล่น:** กรุณาทำการแท็ก `@ผู้เล่น` หรือใส่ `Discord ID` ให้ถูกต้องครับ")
                return

            if role not in member.roles:
                await ctx.send(f"⚠️ ผู้เล่น **{member.display_name}** ไม่มีสิทธิ์ยศ `{role_name}` อยู่แล้วครับ")
                return

            try:
                await member.remove_roles(role)
                await ctx.send(f"✅ ลบยศ **{role_name}** ออกจากโปรไฟล์ของ **{member.mention}** เรียบร้อยแล้วครับ! 🧼")
                print(f"❌ [ADMIN ROLE] ลบยศ {role_name} ออกจาก {member.name} สำเร็จ")
            except discord.Forbidden:
                await ctx.send("❌ **บอทไม่มีสิทธิ์จัดการยศ:** ยศของบอทอยู่ต่ำกว่ายศดังกล่าว กรุณาขยับเลเยอร์ยศบอทให้สูงขึ้นครับ")
            except Exception as e:
                await ctx.send(f"⚠️ เกิดข้อผิดพลาด: `{e}`")

    # ─── 🔍 13. แอดมินส่องดูสเตตัสโปรไฟล์ผู้เล่น (!check_profile) ───
    @commands.command(name="check_profile")
    async def check_profile(self, ctx, target: discord.User = None):
        if target is None:
            await ctx.send("❓ **วิธีใช้งาน:** `!check_profile [@ชื่อผู้เล่น หรือ ID]`")
            return

        user_id = target.id
        name = target.display_name

        player = player_model.get_player(user_id)
        if not player:
            await ctx.send(f"❌ ไม่พบข้อมูลตัวละครของ **{name}** ในฐานข้อมูลครับ")
            return

        level = player.get("level", 1)
        exp = player.get("exp", 0)
        cash = player.get("cash", 0)
        bank = player.get("bank", 0)
        hp = player.get("hp", 100)
        max_hp = player.get("max_hp", 100)
        armor = player.get("armor", "0")
        rank = player.get("rank", "นักผจญภัยฝึกหัด")
        current_state = player.get("current_state", "ปกติ")

        total_mins = player.get("total_online_time", 0)
        
        MINS_IN_HOUR = 60
        MINS_IN_DAY = 60 * 24
        MINS_IN_MONTH = MINS_IN_DAY * 30
        MINS_IN_YEAR = MINS_IN_DAY * 365

        years = total_mins // MINS_IN_YEAR
        months = (total_mins % MINS_IN_YEAR) // MINS_IN_MONTH
        days = (total_mins % MINS_IN_MONTH) // MINS_IN_DAY
        hours = (total_mins % MINS_IN_DAY) // MINS_IN_HOUR
        mins = total_mins % MINS_IN_HOUR

        time_parts = []
        if years > 0: time_parts.append(f"`{years}` ปี")
        if months > 0: time_parts.append(f"`{months}` เดือน")
        if days > 0: time_parts.append(f"`{days}` วัน")
        if hours > 0: time_parts.append(f"`{hours}` ชม.")
        if mins > 0 or len(time_parts) == 0: 
            time_parts.append(f"`{mins}` นาที")
        
        formatted_time = " ".join(time_parts)

        embed = discord.Embed(
            title=f"🔎 Admin Inspection — {name}",
            description=f"📂 ข้อมูลสเตตัสในระบบอย่างละเอียด\n💻 User ID: `{user_id}`",
            color=0x3182ce
        )
        
        embed.add_field(name="🎖️ ตำแหน่ง / เลเวล", value=f"**Rank:** {rank}\n**Level:** `{level}`\n**EXP:** `{exp:,}`", inline=True)
        embed.add_field(name="💰 Status การเงิน", value=f"**เงินติดตัว:** `{cash:,}` ทอง\n**ในธนาคาร:** `{bank:,}` ทอง", inline=True)
        embed.add_field(name="⏳ เวลาออนไลน์สะสม", value=f"⏱️: {formatted_time}", inline=False)
        embed.add_field(name="🩸 พลังชีวิตและป้องกัน", value=f"**HP:** `{hp}` / `{max_hp}` | **Armor:** `{armor}` แต้ม\n**สถานะตัวละคร:** `{current_state}`", inline=False)
        
        embed.set_footer(text=f"ตรวจสอบโดย Admin: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))