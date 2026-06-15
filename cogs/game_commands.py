None
import discord
from discord.ext import commands, tasks
import models.player_model as player_model
from views.profile_embed import create_profile_embed
import random  # 🌟 [เพิ่มบรรทัดนี้] เปิดทางให้บอทเรียกใช้ระบบสุ่มจับรางวัลทองชาร์ตแชท
import time    # 🌟 [เพิ่มบรรทัดนี้] เปิดทางให้บอทคำนวณเวลาระบบ Cooldown ป้องกันคนสแปมพิมพ์

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 🟢 เริ่มรันระบบ Loop ทันทีที่ Cog ทำงาน
        self.voice_exp_tracker.start()
        self.chat_cooldowns = {} # ⏱️ [เพิ่มตรงนี้] คลังเก็บ Cooldown แชทของผู้เล่นบนแรม
        
    def cog_unload(self):
        # 🛑 สั่งหยุดระบบ Loop เมื่อ Cog โดนรีโหลดหรือปิดบอท
        self.voice_exp_tracker.cancel()

    # ─── 🔄 ระบบสแกนแจก EXP + อัปเดตยศออโต้ในดิสคอร์ด (ทำงานทุก 1 นาที) ───
    @tasks.loop(minutes=1.0)
    async def voice_exp_tracker(self):
        """Loop หลังบ้านสแกนหาผู้เล่นเพื่อแจก EXP พร้อมคิดโบนัสคูณ และแจกยศอัตโนมัติในเซิร์ฟเวอร์"""
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                # 🚫 กฎความปลอดภัย: ถ้าห้องนั้นไม่มีคนอยู่ ไม่ต้องแจก
                if len(voice_channel.members) == 0: 
                    continue
                    
                for member in voice_channel.members:
                    if member.bot: continue 
                    if member.voice.self_deaf or member.voice.self_mute: 
                        continue
                    
                    player = player_model.get_player(member.id)
                    if not player: continue
                        
                    # 🟢 1. คำนวณแจก EXP ตามสูตร 3 เดือน (นาทีละ 100 EXP พื้นฐาน)
                    base_exp = 100 
                    p_lvl = player["level"] 
                    
                    multiplier = 1
                    if p_lvl >= 80: multiplier = 5
                    elif p_lvl >= 40: multiplier = 4
                    elif p_lvl >= 20: multiplier = 3
                    elif p_lvl >= 10: multiplier = 2
                        
                    final_gained_exp = base_exp * multiplier
                    
                    # บันทึก EXP เข้าฐานข้อมูล
                    is_lv_up, new_lv, _ = player_model.add_exp(member.id, final_gained_exp)
                    
                    if is_lv_up:
                        try:
                            await member.send(f"✨🎉 **LEVEL UP!!** แต้มจากการร่วมพูดคุยในห้องเสียงส่งผลให้คุณเลเวลอัปเป็น **Lv.{new_lv}** แล้วครับ!")
                        except discord.Forbidden:
                            pass
                    
                    # 🏅 2. ตรวจสอบและอัปเดตยศ (Rank)
                    current_actual_level = new_lv if is_lv_up else p_lvl
                    is_rank_up, new_rank = player_model.check_and_update_rank(member.id, current_actual_level)
                    
                    # ⚡ เมื่อแรงค์เพิ่ม สั่งแจกยศในดิสคอร์ดเซิร์ฟเวอร์อัตโนมัติ
                    if is_rank_up:
                        role_name = f"นักผจญภัยแรงค์ {new_rank}"
                        role = discord.utils.get(guild.roles, name=role_name)
                        
                        if role:
                            try:
                                # ➕ มอบยศใหม่ให้กับผู้เล่น
                                await member.add_roles(role)
                                
                                # 🗑️ ไล่ลบยศแรงค์เก่าออกเพื่อไม่ให้ยศรกตัวละคร
                                all_ranks = ["F", "E", "D", "C", "B", "A", "SSS"]
                                for r in all_ranks:
                                    if r != new_rank:
                                        old_role = discord.utils.get(guild.roles, name=f"นักผจญภัยแรงค์ {r}")
                                        if old_role and old_role in member.roles:
                                            await member.remove_roles(old_role)
                                            
                                # ส่งข้อความแจ้งเตือนความสำเร็จ
                                await member.send(f"🏅 **[สมาคมนักผจญภัย]** ปรับระดับยศของคุณในเซิร์ฟเวอร์เป็น **{role_name}** เรียบร้อยแล้ว! ⚔️")
                            except discord.Forbidden:
                                print(f"❌ บอทไม่มีสิทธิ์จัดการยศ (Manage Roles) ในเซิร์ฟเวอร์: {guild.name}")
                            except Exception as e:
                                print(f"⚠️ เกิดข้อผิดพลาดในการแจกยศ: {e}")
                        else:
                            print(f"⚠️ ไม่พบยศชื่อ '{role_name}' ในเซิร์ฟเวอร์ {guild.name} (กรุณาสร้างยศนี้รอไว้ในดิสคอร์ด)")

    @voice_exp_tracker.before_loop
    async def before_voice_exp_tracker(self):
        """รอให้บอทล็อกอินและ Gateway เชื่อมต่อเสร็จร้อยเปอร์เซ็นต์ก่อนเริ่มสแกน"""
        await self.bot.wait_until_ready()
    
    # ─── 💬 ระบบดักฟังช่องแชท แจกเงินเล็กน้อยเมื่อพิมพ์คุย (Text Chat Reward) ───
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None or message.content.startswith("!"):
            return
            
        user_id = message.author.id
        
        # ⏱️ ตรวจสอบระบบ Cooldown แชท
        import time
        current_time = time.time()
        if user_id in self.chat_cooldowns:
            last_msg_time = self.chat_cooldowns[user_id]
            # ถ้ายังพิมพ์ไม่เกิน 10 วินาทีนับจากครั้งล่าสุด ให้ปล่อยผ่าน ไม่แจกเงินซ้ำ
            if current_time - last_msg_time < 10: 
                return
                
        player = player_model.get_player(user_id)
        if player:
            gained_gold = random.randint(10, 300)
            player_model.update_player_field(user_id, "cash", player.get("cash", 0) + gained_gold)
            
            # บันทึกเวลาพิมพ์ล่าสุดของผู้เล่นลงแรม
            self.chat_cooldowns[user_id] = current_time
            # print(f"💬 [Chat Reward] คุณ {message.author.name} ได้รับ `{gained_gold}` ทอง")

    # ─── 🛒 คำสั่งเปิดร้านค้าและซื้อขายยศแบบข้อความ (!shop) ───
    @commands.command(name="shop")
    async def shop(self, ctx, action: str = None, item_num: int = None):
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        if not player:
            await ctx.send("❌ ไม่พบข้อมูลตัวละครของคุณ กรุณาพิมพ์ `!play` เพื่อลงทะเบียนก่อนครับ")
            return

        # 📋 คลังข้อมูลราคายศและชื่อยศในเซิร์ฟเวอร์
        shop_items = {
            1: {"name": "ขายยศ 1", "price": 1000},
            2: {"name": "ขายยศ 2", "price": 5000},
            3: {"name": "ขายยศ 3", "price": 10000}
        }

        # 🛑 เคสที่ 1: พิมพ์ !shop เฉยๆ -> บอทเปิดใบรายการหน้าร้านให้ดู
        if action is None:
            embed = discord.Embed(
                title="🛒 สมาคมนักผจญภัย - ร้านค้าตราเกียรติยศ (Text Edition)",
                description=f"ยินดีต้อนรับคุณ **{ctx.author.name}** เข้าสู่หอเกียรติยศ\n💰 เงินคงเหลือปัจจุบัน: `{player.get('cash', 0)}` ทอง\n\n"
                            f"📌 **รายการยศที่มีวางจำหน่าย:**\n"
                            f"🔹 **[1] ยศทดสอบ 1** — ราคา `1,000` ทอง\n"
                            f"🔹 **[2] ยศทดสอบ 2** — ราคา `5,000` ทอง\n"
                            f"🔹 **[3] ยศทดสอบ 3** — ราคา `10,000` ทอง\n\n"
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

    # ─── ⚔️ คำสั่งเล่นเกมคอร์หลัก ───
    @commands.command(name="play")
    async def play(self, ctx):
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        # 🟢 [ระบบดักเช็กยศออโต้] พิมพ์ !play ปุ๊บ ตรวจสอบแรงค์ตามเวลปัจจุบันทันที (ยศเก่าไม่ลบ)
        if player:
            current_level = player.get("level", 1)
            # สั่งให้โมเดลคำนวณและอัปเดตแรงค์ใน DB ให้ถูกต้องก่อน
            _, current_rank = player_model.check_and_update_rank(user_id, current_level)
            
            guild = ctx.guild
            member = ctx.author
            
            if guild and isinstance(member, discord.Member):
                # ฟังก์ชันสแกนเลเวลเพื่อหาว่าควรได้รับแรงค์ไหนบ้างในตัว
                def get_eligible_ranks(lvl):
                    eligible = ["F"] # เลเวล 1 ได้แรงค์ F แน่นอน
                    if lvl >= 5: eligible.append("E")
                    if lvl >= 10: eligible.append("D")
                    if lvl >= 20: eligible.append("C")
                    if lvl >= 50: eligible.append("B")
                    if lvl >= 80: eligible.append("A")
                    if lvl >= 100: eligible.append("SSS")
                    return eligible

                eligible_ranks = get_eligible_ranks(current_level)
                roles_to_add = []

                # วนลูปตรวจสอบ ถ้าในดิสคอร์ดยังไม่มีแรงค์ที่ควรมี ให้จับใส่ลิสต์เตรียมแอดเพิ่ม
                for r in eligible_ranks:
                    role_name = f"นักผจญภัยแรงค์ {r}"
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role not in member.roles:
                        roles_to_add.append(role)

                # ถ้ามียศที่ยังขาดอยู่ สั่งแจกเพิ่มเข้าไปรวดเดียว
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
            await ctx.send(embed=embed, view=RespawnView(user_id))
            return 

        # 🚶 กรณีติดสถานะเลือก Choice อื่นๆ ค้างเฉยๆ (เลือดยังเหลือ) เคลียร์สเตตัสกลับมาเริ่มเดินใหม่ได้
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
        
        # 🎯 ดึงมาประกาศเรียกใช้ตรงนี้เพื่อสยบปัญหา Circular Import
        from views.game_views import AdventureView
        await ctx.send(embed=embed, view=AdventureView())

# ฟังก์ชันสำหรับให้ตัวบอทหลักโหลด Cog นี้เข้าสู่ระบบ
async def setup(bot):
    await bot.add_cog(GameCommands(bot))