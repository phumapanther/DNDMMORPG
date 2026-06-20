import discord
from collections import Counter
from discord.ext import commands
import random
import models.player_model as player_model
import time
import sqlite3
from contextlib import contextmanager
from utils import not_arrested, allowed_channels
from views.profile_embed import ARMOR_STATS, GAME_CLASSES, WEAPON_STATS, ITEM_CONFIG , BAG_STATS
from views.game_views import DeathRespawnView

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
    @not_arrested() 
    @commands.command(name="deposit")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def deposit(self, ctx, amount: int):
        player = player_model.get_player(ctx.author.id)
        if amount <= 0 or player["cash"] < amount:
            return await ctx.send("❌ เงินไม่พอหรือจำนวนไม่ถูกต้อง!")
        
        player_model.update_player_field(ctx.author.id, "cash", player["cash"] - amount)
        player_model.update_player_field(ctx.author.id, "bank", player.get("bank", 0) + amount)
        await ctx.send(f"💰 ฝากเงินเข้าธนาคารเรียบร้อย: `{amount}` ทอง")
        
    @not_arrested() 
    @commands.command(name="withdraw")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def withdraw(self, ctx, amount: int):
        player = player_model.get_player(ctx.author.id)
        
        if amount <= 0:
            return await ctx.send("❌ จำนวนเงินต้องมากกว่า 0!")
        
        if player.get("bank", 0) < amount:
            return await ctx.send("❌ เงินในธนาคารไม่พอถอนครับ!")
        
        player_model.update_player_field(ctx.author.id, "bank", player["bank"] - amount)
        player_model.update_player_field(ctx.author.id, "cash", player["cash"] + amount)
        
        await ctx.send(f"💸 ถอนเงินออกจากธนาคารเรียบร้อย: `{amount:,}` ทอง")
    
    # 2. โอนเงิน: โอนจาก Bank -> ผู้เล่นอื่น
    @not_arrested() 
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

    # 3. ขอเงิน (Beg)
    @not_arrested() 
    @commands.command(name="beg")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def beg(self, ctx):
        if not any(role.name == "ขอทาน" for role in ctx.author.roles):
            return await ctx.send("❌ เฉพาะคนมียศ 'ขอทาน' เท่านั้นที่จะขอเงินคนอื่นได้!")

        top_players = player_model.get_all_players_sorted_by_wealth()[:10] 
        if not top_players: return await ctx.send("❌ ไม่มีเศรษฐีให้ขอเลย...")

        target = random.choice(top_players)
        tax = int(target.get("bank", 0) * 0.01)
        
        player_model.update_player_field(target["user_id"], "bank", target["bank"] - tax)
        player_model.update_player_field(ctx.author.id, "cash", player_model.get_player(ctx.author.id)["cash"] + tax)
        await ctx.send(f"🤲 ขอทานได้เงิน `{tax}` ทอง จากเศรษฐี {target['username']}!")

    # 4. ปล้น (Rob)
    @not_arrested() 
    @commands.command(name="rob")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
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

    # 5. rich
    @commands.command(name="rich")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def rich(self, ctx):
        with self.get_db() as cursor:
            cursor.execute("SELECT user_id, (bank + cash) as total FROM players ORDER BY total DESC LIMIT 10")
            rows = cursor.fetchall()
        
        msg = "🏆 **10 อันดับมหาเศรษฐี** 🏆\n"
        for i, (uid, total) in enumerate(rows, 1):
            name = await self.get_user_name(uid)
            msg += f"{i}. **{name}**: `{total:,}` ทอง\n"
        await ctx.send(msg)

    # 6. toplvl
    @commands.command(name="toplvl")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def toplvl(self, ctx):
        with self.get_db() as cursor:
            cursor.execute("SELECT user_id, level, exp FROM players ORDER BY level DESC, exp DESC LIMIT 10")
            rows = cursor.fetchall()

        msg = "⚔️ **10 อันดับผู้กล้าเลเวลสูง** ⚔️\n"
        for i, (uid, lvl, exp) in enumerate(rows, 1):
            name = await self.get_user_name(uid)
            msg += f"{i}. **{name}**: เลเวล `{lvl}` (EXP: `{exp}`)\n"
        await ctx.send(msg)
    
    # ==========================================
    # 💬 คำสั่งเช็กสถิติการพิมพ์ของตัวเอง (!mytext)
    # ==========================================
    @commands.command(name="mytext")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def check_my_text(self, ctx):
        player = player_model.get_player(ctx.author.id)
        if not player:
            return await ctx.send("❌ ไม่พบข้อมูลตัวละครของคุณในระบบ!")
        
        total_text = player.get("total_text", 0)
        event_text = player.get("event_text", 0)
        
        embed = discord.Embed(
            title="📊 สถิติการพิมพ์แชทของคุณ", 
            color=discord.Color.blue()
        )
        
        # ใส่รูปโปรไฟล์ของผู้เล่น
        if ctx.author.avatar:
            embed.set_thumbnail(url=ctx.author.avatar.url)
            
        embed.add_field(name="💬 ข้อความทั้งหมด (ตลอดชีพ)", value=f"`{total_text:,}` ข้อความ", inline=False)
        embed.add_field(name="🏆 ข้อความกิจกรรม (ซีซั่นนี้)", value=f"`{event_text:,}` ข้อความ", inline=False)
        
        await ctx.send(embed=embed)


    # ==========================================
    # 🏆 คำสั่งเช็ก 10 อันดับคนพิมพ์เยอะที่สุด (!toptext)
    # ==========================================
    @commands.command(name="toptext")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def top_text_leaderboard(self, ctx):
        # เรียกใช้ฟังก์ชันดึง Top 10 ที่เราเพิ่งสร้าง
        top_players = player_model.get_top_text_players(10)
        
        if not top_players:
            return await ctx.send("❌ ยังไม่มีสถิติการพิมพ์ในเซิร์ฟเวอร์เลย! (ไปพิมพ์แชทกันก่อนนะ)")
            
        embed = discord.Embed(
            title="🏆 TOP 10 นักแชทแห่งเซิร์ฟเวอร์ 🏆", 
            description="รายชื่อนักผจญภัยที่พูดคุยเยอะที่สุดในดินแดนนี้!", 
            color=discord.Color.gold()
        )
        
        board_text = ""
        for index, (user_id, total, event) in enumerate(top_players, start=1):
            # จัดการเหรียญรางวัลให้อันดับ 1-3
            if index == 1:
                medal = "🥇"
            elif index == 2:
                medal = "🥈"
            elif index == 3:
                medal = "🥉"
            else:
                medal = f"**{index}.**"
            
            # ใช้ <@user_id> เพื่อให้ Discord แท็ก (Mention) โชว์ชื่อผู้เล่นปัจจุบันอัตโนมัติ
            board_text += f"{medal} <@{user_id}>\n"
            board_text += f"└ 💬 รวม: `{total:,}` | 🏆 กิจกรรม: `{event:,}`\n\n"
            
        embed.add_field(name="อันดับกระดานผู้นำ", value=board_text, inline=False)
        embed.set_footer(text="ระบบจะนับเฉพาะข้อความที่พิมพ์ในช่องแชททั่วไปเท่านั้น")
        
        await ctx.send(embed=embed)
    
    # --- โค้ดคำสั่ง !bag ---
    @commands.command(name="bag")
    async def check_bag(self, ctx): # 🚨 จุดสำคัญ: เติม self ลงไปตรงนี้ครับ
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        # [ระบบเช็กไฟล์/แคช]
        if not player:
            print(f"ERROR: [Bag] ไม่พบข้อมูลผู้เล่นสำหรับ User ID: {user_id}")
            await ctx.send("❌ ไม่พบข้อมูลตัวละครของคุณ! พิมพ์ `!play` เพื่อสร้างตัวละครก่อนน้า")
            return

        raw_inv = player.get("inventory", "")
        clean_inv = str(raw_inv)
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            clean_inv = clean_inv.replace(char, "")
            
        # print(f"DEBUG: [Bag] User {user_id} เปิดกระเป๋า | ข้อมูลดิบใน DB: '{raw_inv}' | คลีนแล้ว: '{clean_inv}'")

        inv_array = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []

        embed = discord.Embed(
            title=f"🎒 กระเป๋าเดินทางของ {ctx.author.display_name}",
            description=f"💰 **เงินสดกลาง:** {player.get('cash', 0):,} ทอง",
            color=discord.Color.blue()
        )

        if not inv_array:
            embed.add_field(name="📦 ไอเทมในกระเป๋า", value="*~ กระเป๋าว่างเปล่า ไม่มีไอเทมเลย ~*", inline=False)
        else:
            item_counts = Counter(inv_array)
            bag_list_text = ""
            
            for item_id, count in item_counts.items():
                if item_id in ITEM_CONFIG:
                    item_name = ITEM_CONFIG[item_id]["name"]
                    # 🛠️ เพิ่ม [เลข ID] ไว้ด้านหน้าให้ผู้เล่นรู้ว่าต้องพิมพ์ !use เลขอะไร
                    bag_list_text += f"**[{item_id}]** {item_name} x`{count}` ชิ้น\n"
                else:
                    print(f"WARNING: [Bag] พบ Item ID '{item_id}' ในกระเป๋าผู้เล่น แต่ไม่มีใน ITEM_CONFIG!")
                    bag_list_text += f"**[{item_id}]** ❓ ไอเทมปริศนา x`{count}` ชิ้น\n"

            embed.add_field(name="📦 ไอเทมในกระเป๋า", value=bag_list_text, inline=False)

        # 💡 แนะนำเสริม: ใช้ display_avatar เพื่อป้องกันบั๊กเวลาคนไม่มีรูปโปรไฟล์
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)
    
    # ⏱️ เช็กเวลาออนไลน์ของตัวเอง
    @commands.command(name="mytime")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def check_my_time(self, ctx):
        player = player_model.get_player(ctx.author.id)
        if not player:
            return await ctx.send("❌ คุณยังไม่มีข้อมูลในระบบ!")
        
        total_minutes = player.get("total_online_time", 0)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        await ctx.send(f"👤 **{ctx.author.name}**\n⏱️ เวลาออนไลน์ทั้งหมดของคุณ: **{hours} ชั่วโมง {minutes} นาที**")

    # 🏆 เช็กอันดับ Top 10 เวลาออนไลน์
    @commands.command(name="toptime")
    @allowed_channels(["🏦ธนาคารกลาง🏦"])
    async def top_online_time(self, ctx):
        all_players = player_model.get_all_players() 
        
        if not all_players:
            return await ctx.send("❌ ยังไม่มีข้อมูลผู้เล่นในระบบ!")

        # เรียงลำดับจากมากไปน้อย
        top_players = sorted(all_players, key=lambda x: x.get("total_online_time", 0), reverse=True)[:10]
        
        embed = discord.Embed(title="🏆 10 อันดับนักผจญภัยที่ออนไลน์นานที่สุด", color=discord.Color.gold())
        
        msg = ""
        for i, p in enumerate(top_players, 1):
            user_id = p.get("user_id")
            time_m = p.get("total_online_time", 0)
            
            # ใช้ <@user_id> เพื่อแท็กชื่อผู้เล่นอัตโนมัติ
            msg += f"{i}. <@{user_id}> - `{time_m // 60} ชม. {time_m % 60} นาที`\n"
            
        embed.description = msg
        await ctx.send(embed=embed)
        
    # --- คำสั่ง !use <เลขไอเทม> ---
    @commands.command(name="use")
    async def use_item(self, ctx, item_id: str):
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        if not player:
            return await ctx.send("❌ ไม่พบข้อมูลตัวละครของคุณ!")

        # 1. ทำความสะอาดและดึง Array กระเป๋า
        raw_inv = player.get("inventory", "")
        clean_inv = str(raw_inv)
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            clean_inv = clean_inv.replace(char, "")
            
        inv_array = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []

        # 2. เช็กว่ามีไอเทมในกระเป๋าไหม
        if item_id not in inv_array:
            return await ctx.send(f"❌ คุณไม่มีไอเทมหมายเลข `{item_id}` ในกระเป๋า! (พิมพ์ `!bag` เพื่อเช็ก)")
            
        if item_id not in ITEM_CONFIG:
            return await ctx.send("❌ ไม่มีข้อมูลไอเทมนี้ในระบบเซิร์ฟเวอร์!")

        # ดึงข้อมูลจาก Config มาเตรียมไว้
        item_info = ITEM_CONFIG[item_id]
        item_name = item_info["name"]
        item_type = item_info.get("type", "unknown")

        # --- 3. ตรรกะผลลัพธ์ของไอเทม (Item Logic) ---
        msg = ""
        
        # 🧪 กรณี: ใช้ยาฮีล
        if item_id == "1":
            heal_amount = 50 
            armor_key = player.get("armor", "None")
            current_dur = player.get("armor_dur", 0)
            
            # ใช้ armor_info_stats เพื่อไม่ให้ชื่อตัวแปรซ้ำกัน
            armor_info_stats = ARMOR_STATS.get(armor_key, ARMOR_STATS.get("None", {}))
            
            armor_hp_bonus = armor_info_stats.get("hp", 0) if current_dur > 0 else 0
            max_hp_total = player.get("max_hp", 100) + armor_hp_bonus
            current_hp = player.get("hp", 0)
            
            if current_hp >= max_hp_total:
                return await ctx.send(f"❌ เลือดของคุณเต็มอยู่แล้ว! (`{current_hp}/{max_hp_total}`) ไม่สามารถใช้ {item_name} ได้")
                
            new_hp = min(current_hp + heal_amount, max_hp_total)
            player_model.update_player_field(user_id, "hp", new_hp)
            msg = f"🧪 คุณดื่ม **{item_name}** ฟื้นฟูพลังชีวิต! (HP: `{current_hp}` ➔ `{new_hp}/{max_hp_total}`)"

        # 🛠️ กรณี: ใช้ใบซ่อมแซม
        elif item_id == "2":
            armor_key = player.get("armor", "None")
            weapon_key = player.get("weapon", "None")
            
            armor_info_stats = ARMOR_STATS.get(armor_key, {})
            max_armor_dur = armor_info_stats.get("dur", 100)
            current_armor_dur = player.get("armor_dur", 0)
            
            weapon_info_stats = WEAPON_STATS.get(weapon_key, {})
            max_weapon_dur = weapon_info_stats.get("dur", 50)
            current_weapon_dur = player.get("weapon_dur", 0)
            
            needs_armor_repair = (armor_key != "None" and current_armor_dur < max_armor_dur)
            needs_weapon_repair = (weapon_key != "None" and current_weapon_dur < max_weapon_dur)
            
            if not needs_armor_repair and not needs_weapon_repair:
                return await ctx.send(f"❌ อุปกรณ์ทั้งหมดของคุณสภาพสมบูรณ์อยู่แล้ว (หรือไม่ได้สวมใส่)! ไม่สามารถใช้ {item_name} ได้")
            
            repaired_items = []
            if needs_armor_repair:
                player_model.update_player_field(user_id, "armor_dur", max_armor_dur)
                repaired_items.append(f"เกราะ **{armor_info_stats.get('name', armor_key)}** (`{max_armor_dur}/{max_armor_dur}`)")
                
            if needs_weapon_repair:
                player_model.update_player_field(user_id, "weapon_dur", max_weapon_dur)
                repaired_items.append(f"อาวุธ **{weapon_info_stats.get('name', weapon_key)}** (`{max_weapon_dur}/{max_weapon_dur}`)")
            
            repair_text = " และ ".join(repaired_items)
            msg = f"🛠️ คุณใช้ **{item_name}** ซ่อมแซม {repair_text} กลับมาสภาพสมบูรณ์!"

        # 🛡️ กรณี: สวมใส่ชุดเกราะ (อ่านค่า type อัตโนมัติจาก ITEM_CONFIG)
        elif item_type == "armor":
            equip_key = item_info["equip_key"]
            armor_stats = ARMOR_STATS.get(equip_key, {})
            max_dur = armor_stats.get("dur", 100)
            
            player_model.update_player_field(user_id, "armor", equip_key)
            player_model.update_player_field(user_id, "armor_dur", max_dur)
            
            # [เสริมความปลอดภัย] ป้องกันเลือดล้นเวลาเปลี่ยนเกราะที่บวก HP น้อยลง
            current_hp = player.get("hp", 0)
            new_max_hp = player.get("max_hp", 100) + armor_stats.get("hp", 0)
            if current_hp > new_max_hp:
                player_model.update_player_field(user_id, "hp", new_max_hp)
            
            msg = f"🛡️ คุณสวมใส่ **{item_name}** เรียบร้อยแล้ว! (ความคงทน: `{max_dur}/{max_dur}`)"

        # ⚔️ กรณี: สวมใส่อาวุธ
        elif item_type == "weapon":
            equip_key = item_info["equip_key"]
            weapon_stats = WEAPON_STATS.get(equip_key, {})
            max_dur = weapon_stats.get("dur", 50)
            
            player_model.update_player_field(user_id, "weapon", equip_key)
            player_model.update_player_field(user_id, "weapon_dur", max_dur)
            
            msg = f"⚔️ คุณสวมใส่ **{item_name}** เรียบร้อยแล้ว! (ความคงทน: `{max_dur}/{max_dur}`)"
        
        elif item_type == "bag":
            equip_key = item_info["equip_key"]
            bag_status = BAG_STATS.get(equip_key, {})
            bag_limit = bag_status.get("capacity", 10)

            player_model.update_player_field(user_id, "bag", equip_key)
            player_model.update_player_field(user_id, "capacity", bag_limit)
        
            msg = f"⚔️ คุณสวมใส่ **{item_name}** เรียบร้อยแล้ว! (ความจุกระเป๋า: `{bag_limit}`)"

        elif item_type == "drop":
            # 1. เช็กเคสพิเศษ: ใบชุบชีวิต (28) ต้องเช็กว่าตายไหม
            if item_id == "28":
                if player.get("hp") > 0 and player.get("current_state") != "death":
                    return await ctx.send("❌ คุณยังไม่ได้ตาย จะใช้ใบชุบชีวิตไปทำไมล่ะเนี่ย! เก็บไว้ใช้ตอนตายดีหน้า!")
                
                # ถ้าตายจริง ให้ชุบชีวิต
                max_hp = player.get("max_hp", 100)
                player_model.update_player_field(user_id, "hp", max_hp)
                player_model.update_player_field(user_id, "current_state", "idle")
                player_model.update_player_field(user_id, "last_event", "revive") # ใส่เพื่อให้ระบบสุ่มเหตุการณ์รู้ว่าเพิ่งชุบ
                
                await ctx.send("✨ คุณใช้ `💌ใบชุบชีวิต`! ฟื้นคืนชีพและฟื้นฟู HP เต็มแล้ว! พร้อมลุยต่อแล้วครับ!")
                # [ใส่คำสั่งลบไอเทมออกจากกระเป๋าที่นี่]

            # 2. เคสไอเทม Drop อื่นๆ (ต้องเป็น idle เท่านั้น)
            else:
                if player.get("current_state") != "idle":
                    return await ctx.send("❌ คุณไม่สามารถใช้ไอเทมนี้ได้ในขณะที่กำลังทำกิจกรรมอื่นอยู่ (ต้องอยู่ในสถานะว่างก่อนกดปุ่ม 🧭 เริ่มออกเดินทาง)!")

                drop_map = {
                    "22": "warp_village",
                    "23": "warp_dungeon",
                    "24": "mini_summon",
                    "25": "main_summon",
                    "26": "unbeatable_summon",
                    "27": "scan_box"
                }
                
                new_state = drop_map.get(item_id)
                if new_state:
                    player_model.update_player_field(user_id, "last_event", new_state)
                    # [ใส่คำสั่งลบไอเทมออกจากกระเป๋าที่นี่]
                    await ctx.send(f"✨ คุณได้เปิดใช้งาน `{item_name}` แล้ว! เตรียมพบกับเหตุการณ์ถัดไป...")
                else:
                    await ctx.send("❌ ไอเทมนี้ยังไม่ถูกตั้งค่าการใช้งาน!")
        ##ตั้งเงื่อไขว่าต้องสเตตัสฑรรมดาเท่านั้นถึงใช้ ใบบอสได้ 
        ##เวลาใช้ใบบอส เหตุการจะเป็นตีมอน และเหตุการลองจะเป็นเงื่อนไขบอส มั้ง ตั้งเงื่อไขคอมแบทตอนสุ่มมอน ถ้าสเตตัสนี้ เรทมอนอะไร

        # ถ้าไม่ตรงกับอะไรเลย
        else:
            return await ctx.send(f"❌ ไอเทม **{item_name}** ยังไม่สามารถกดใช้งานได้ในตอนนี้")

        # --- 4. หักไอเทมออกจากกระเป๋า ---
        inv_array.remove(item_id) 
        player_model.update_player_field(user_id, "inventory", ",".join(inv_array))
        
        await ctx.send(msg)
    
    @commands.command(name="drop")
    async def drop_item(self, ctx, item_id: str = None, amount: int = None):
        user_id = ctx.author.id
        player = player_model.get_player(user_id)
        
        if not player:
            return await ctx.send("❌ ไม่พบข้อมูลตัวละครของคุณ! พิมพ์ `!play` ก่อนนะ")

        # ---------------------------------------------------------
        # 1. 🧹 ถอดรหัสกระเป๋า (ใช้ Logic เดียวกับ !bag ของคุณอาเธอร์เป๊ะๆ)
        # ---------------------------------------------------------
        raw_inv = player.get("inventory", "")
        clean_inv = str(raw_inv)
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            clean_inv = clean_inv.replace(char, "")
            
        inv_array = clean_inv.split(",") if clean_inv and clean_inv not in ["None", "null"] else []
        inv_array = [i for i in inv_array if i] # กันเหนียว กรองพวกค่าว่างที่อาจจะหลุดมาทิ้งไป
        
        capacity = player.get("capacity", 10)

        # ---------------------------------------------------------
        # 2. 🧳 กรณีที่พิมพ์แค่ !drop (แสดงรายการกระเป๋า)
        # ---------------------------------------------------------
        if item_id is None:
            from collections import Counter
            item_counts = Counter(inv_array)
            
            embed = discord.Embed(title="🗑️ โยนไอเทมทิ้ง", color=discord.Color.red())
            embed.add_field(name="ความจุกระเป๋า", value=f"{len(inv_array)} / {capacity}", inline=False)
            
            if not inv_array:
                embed.description = "*~ กระเป๋าว่างเปล่า ไม่มีอะไรให้ทิ้ง ~*"
            else:
                drop_text = "💡 **วิธีใช้:** พิมพ์ `!drop [เลขไอเทม] [จำนวน]` เพื่อทิ้งของ\n\n**รายการที่มี:**\n"
                for i_id, count in item_counts.items():
                    if i_id in ITEM_CONFIG:
                        item_name = ITEM_CONFIG[i_id]["name"]
                        drop_text += f"**[{i_id}]** {item_name} x`{count}`\n"
                    else:
                        drop_text += f"**[{i_id}]** ❓ ไอเทมปริศนา x`{count}`\n"
                embed.description = drop_text
                
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        # ---------------------------------------------------------
        # 3. 🗑️ กรณีที่พิมพ์เพื่อทิ้งของ (เช่น !drop 22 1)
        # ---------------------------------------------------------
        if amount is None or amount <= 0:
            return await ctx.send("❌ โปรดระบุจำนวนที่ต้องการทิ้งให้ถูกต้อง เช่น `!drop 22 1`")

        # ตรวจสอบว่าในกระเป๋ามีของนี้พอไหม
        current_count = inv_array.count(item_id)
        if current_count < amount:
            item_name = ITEM_CONFIG.get(item_id, {}).get("name", f"ไอเทมรหัส {item_id}")
            return await ctx.send(f"❌ คุณมี {item_name} ไม่พอให้ทิ้ง! (ในกระเป๋ามีแค่ {current_count} ชิ้น)")

        # ทำการลบไอเทมตามจำนวนที่ระบุ
        for _ in range(amount):
            inv_array.remove(item_id)
            
        # บันทึกข้อมูลกลับลงฐานข้อมูล (inv_array เป็น list แล้ว update_player_field จะแปลงเป็น JSON ให้เอง)
        player_model.update_player_field(user_id, "inventory", inv_array)
        
        # แสดงข้อความยืนยัน
        item_name = ITEM_CONFIG.get(item_id, {}).get("name", "ไอเทมปริศนา")
        await ctx.send(f"🗑️ คุณได้โยน **{item_name}** ทิ้งไปจำนวน `{amount}` ชิ้นเรียบร้อยแล้ว!")
    
    @commands.command(name="give")
    async def give_item_to_player(self, ctx, member: discord.Member = None, item_id: str = None, amount: int = 1):
        # 1. เช็กความถูกต้องเบื้องต้น
        if member is None or item_id is None:
            return await ctx.send("❌ วิธีใช้: `!give @ชื่อเพื่อน [เลขไอเทม] [จำนวน]`\n💡 เช่น: `!give @Arthur 1 5`")
            
        if amount <= 0:
            return await ctx.send("❌ จำนวนไอเทมต้องมากกว่า 0!")
            
        if member.id == ctx.author.id:
            return await ctx.send("❌ คุณจะโอนของให้ตัวเองทำไมเนี่ย!")
            
        if member.bot:
            return await ctx.send("❌ บอทไม่ต้องการไอเทมของคุณหรอกนะ!")

        if item_id not in ITEM_CONFIG:
            return await ctx.send(f"❌ ไม่พบไอเทมรหัส `{item_id}` ในระบบ!")

        # 2. ดึงข้อมูลและถอดรหัสกระเป๋า "คนส่ง" (ตัวเราเอง)
        sender_id = ctx.author.id
        sender = player_model.get_player(sender_id)
        
        raw_inv_s = sender.get("inventory", "")
        clean_inv_s = str(raw_inv_s)
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            clean_inv_s = clean_inv_s.replace(char, "")
        sender_inv = clean_inv_s.split(",") if clean_inv_s and clean_inv_s not in ["None", "null"] else []
        sender_inv = [i for i in sender_inv if i]

        # ตรวจสอบว่าคนส่งมีของพอไหม
        sender_item_count = sender_inv.count(item_id)
        item_name = ITEM_CONFIG[item_id]["name"]
        
        if sender_item_count < amount:
            return await ctx.send(f"❌ คุณมี {item_name} ไม่พอโอน! (ในกระเป๋าคุณมีแค่ {sender_item_count} ชิ้น)")

        # 3. ดึงข้อมูลและถอดรหัสกระเป๋า "คนรับ" (เพื่อน)
        receiver = player_model.get_player(member.id)
        if not receiver:
            return await ctx.send(f"❌ ไม่พบข้อมูลของ {member.display_name} ในระบบ (เขาต้องเคยพิมพ์เริ่มเล่นเกมก่อน)")

        raw_inv_r = receiver.get("inventory", "")
        clean_inv_r = str(raw_inv_r)
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            clean_inv_r = clean_inv_r.replace(char, "")
        receiver_inv = clean_inv_r.split(",") if clean_inv_r and clean_inv_r not in ["None", "null"] else []
        receiver_inv = [i for i in receiver_inv if i]

        # เช็กความจุกระเป๋าคนรับ
        receiver_capacity = receiver.get("capacity", 10)
        if len(receiver_inv) + amount > receiver_capacity:
            free_space = receiver_capacity - len(receiver_inv)
            return await ctx.send(f"❌ กระเป๋าของ {member.display_name} เต็มแล้ว! (รับเพิ่มได้อีกแค่ {free_space} ชิ้น)")

        # 4. ทำการโอนย้ายไอเทม (หักจากเรา -> ย้ายไปเพื่อน)
        for _ in range(amount):
            sender_inv.remove(item_id)
            receiver_inv.append(item_id)

        # 5. บันทึกข้อมูลกลับลงฐานข้อมูลทั้ง 2 คน
        player_model.update_player_field(sender_id, "inventory", sender_inv)
        player_model.update_player_field(member.id, "inventory", receiver_inv)

        # 6. แจ้งเตือนความสำเร็จ
        await ctx.send(f"🤝 **โอนไอเทมสำเร็จ!**\nคุณได้มอบ `{item_name}` จำนวน `{amount}` ชิ้น ให้กับ {member.mention} เรียบร้อยแล้ว!")

    # ==========================================
    # ⚔️ คำสั่ง PVP (!att @ผู้ใช้)
    # ==========================================
    @allowed_channels(["⚒-แชทลานประลอง-⚒"]) # 🛠️ ใช้ Decorator บล็อกห้อง
    @not_arrested() # 🛠️ บล็อกคนติดคุก
    @commands.command(name="att")
    async def pvp_attack(self, ctx, member: discord.Member):
        if member.id == ctx.author.id:
            return await ctx.send("❌ คุณไม่สามารถเปิดฉากโจมตีตัวเองได้!")

        # โหลดข้อมูลผู้เล่นทั้งสองฝ่าย
        attacker = player_model.get_player(ctx.author.id)
        defender = player_model.get_player(member.id)

        if not attacker or not defender:
            return await ctx.send("❌ ไม่พบข้อมูลตัวละครของฝ่ายใดฝ่ายหนึ่งในฐานข้อมูล!")

        # 1. เช็กสถานะห้ามต่อสู้ (village หรือ death)
        if attacker.get("current_state") in ["village", "death"] or defender.get("current_state") in ["village", "death"]:
            return await ctx.send("❌ ไม่สามารถต่อสู้ได้เนื่องจากมีฝ่ายใดฝ่ายหนึ่งอยู่ในเซฟโซนหมู่บ้าน หรืออยู่ในสถานะเสียชีวิตแล้ว!")

        # 2. เช็กเงื่อนไขเลเวลต่ำกว่า 20
        if attacker.get("level", 0) < 20 or defender.get("level", 0) < 20:
            return await ctx.send("❌ ระบบ PVP รองรับเฉพาะผู้กล้าเลเวล 20 ขึ้นไปเท่านั้น! (และห้ามรังแกผู้เล่นเลเวลต่ำกว่า 20)")

        # 3. คำนวณความห่างของเลเวลเพื่อเพิ่มความยากในการทอย
        lv_diff = attacker.get("level", 0) - defender.get("level", 0)
        
        # แต้มเต๋าพื้นฐาน 1-20 บวกรวมแต้มโบนัสตามระดับเลเวล
        atk_bonus = lv_diff if lv_diff > 0 else 0
        def_bonus = abs(lv_diff) if lv_diff < 0 else 0

        atk_roll = random.randint(1, 20) + atk_bonus
        def_roll = random.randint(1, 20) + def_bonus

        # หาผู้ชนะจากการทอยเต๋า
        if atk_roll == def_roll:
            return await ctx.send(f"⚔️ **{ctx.author.display_name}** บุกโจมตี **{member.display_name}** แต่แต้มเต๋าเสมอกันที่ `{atk_roll}` แต้ม! ทั้งคู่ตั้งรับและปัดป้องอาวุธไว้ได้!")

        if atk_roll > def_roll:
            winner, loser = attacker, defender
            w_member, l_member = ctx.author, member
            base_dmg = atk_roll
        else:
            winner, loser = defender, attacker
            w_member, l_member = member, ctx.author
            base_dmg = def_roll

        # 4. คำนวณพลังโจมตีอาวุธผู้ชนะ และ พลังป้องกันเกราะผู้แพ้
        w_weapon = winner.get("weapon", "None")
        w_atk_bonus = WEAPON_STATS.get(w_weapon, {}).get("atk", 0)

        l_armor = loser.get("armor", "None")
        # ใช้ 20% ของ HP เกราะมาเป็นพลังป้องกันหักลบดาเมจ
        l_def_bonus = int(ARMOR_STATS.get(l_armor, {}).get("hp", 0) * 0.2)

        # สรุปความเสียหายรวม (ขั้นต่ำ 1 ดาเมจ)
        final_damage = max(1, base_dmg + w_atk_bonus - l_def_bonus)
        
        # หักลบพลังชีวิตผู้แพ้
        loser_current_hp = loser.get("hp", 100)
        loser_new_hp = max(0, loser_current_hp - final_damage)
        
        player_model.update_player_field(l_member.id, "hp", loser_new_hp)

        # 5. เช็กผลการตาย (HP เหลือ 0)
        death_status_text = ""
        if loser_new_hp <= 0:
            player_model.update_player_field(l_member.id, "current_state", "death")
            death_status_text = f"\n💀 **☠️ สิ้นชีพ!** พลังชีวิตของ {l_member.mention} หมดลงและเข้าสู่สถานะเสียชีวิต!"

        # ส่งข้อความสรุปผลการประลอง 1 เทิร์น
        embed = discord.Embed(
            title="⚔️ ผลการดวลศัสตราวุธ ลานประลอง ⚔️",
            description=f"**{w_member.display_name}** ทอยได้ `{base_dmg}` แต้ม ชนะการประลองในตานี้!\n"
                        f"💥 สร้างความเสียหายใส่ **{l_member.display_name}** จำนวน `💥 {final_damage}` หน่วย\n"
                        f"🩸 พลังชีวิตของ {l_member.display_name}: `{loser_current_hp}` ➔ `{loser_new_hp}`{death_status_text}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # ==========================================
    # 👻 ระบบดักจับวิญญาณ (ห้ามคนตายพิมพ์แชทช่องอื่น)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        player = player_model.get_player(message.author.id)
        if not player:
            return

        if player.get("current_state") == "death":
            # 1. ยกเว้น: ถ้าเป็นแชทโลก
            if message.channel.name == "⌒🌍chat╯แชทโลก":
                return
            
            # 2. ยกเว้น: ถ้าผู้เล่นพิมพ์ !use 28 เพื่อใช้ใบชุบ (เช็กจากข้อความ)
            if message.content.strip() == "!use 28":
                return # ปล่อยผ่านให้ระบบคำสั่งไปทำงานต่อเอง
            
            # 3. ถ้าไม่ใช่แชทโลก และไม่ใช่การพิมพ์ใช้ใบชุบ ให้ลบข้อความ
            try:
                await message.delete()
            except discord.Forbidden:
                pass
                
            # 4. ส่งข้อความเตือน (เช็กสถานะ last_event)
            if player.get("last_event") != "death_warned":
                view = DeathRespawnView(message.author.id)
                warning_msg = await message.channel.send(
                    f"👻 {message.author.mention} **คุณเสียชีวิตอยู่!** วิญญาณไม่สามารถสื่อสารในช่องทางนี้ได้\n"
                    f"ต้องการจ่ายเงิน `1,000` ทอง เพื่อกลับไปเกิดใหม่ หรือใช้ใบชุบชีวิต (`!use 28`) หรือไม่?",
                    view=view
                )
                view.message = warning_msg
                player_model.update_player_field(message.author.id, "last_event", "death_warned")

# 🚨 ลบอันที่ซ้ำออกเหลือแค่อันเดียว
async def setup(bot):
    await bot.add_cog(PlayerCommands(bot))