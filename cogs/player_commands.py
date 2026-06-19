import discord
from collections import Counter
from discord.ext import commands
import random
import models.player_model as player_model
import time
import sqlite3
from contextlib import contextmanager
from utils import not_arrested, allowed_channels
from views.profile_embed import ARMOR_STATS, GAME_CLASSES, WEAPON_STATS, ITEM_CONFIG

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
    async def toplvl(self, ctx):
        with self.get_db() as cursor:
            cursor.execute("SELECT user_id, level, exp FROM players ORDER BY level DESC, exp DESC LIMIT 10")
            rows = cursor.fetchall()

        msg = "⚔️ **10 อันดับผู้กล้าเลเวลสูง** ⚔️\n"
        for i, (uid, lvl, exp) in enumerate(rows, 1):
            name = await self.get_user_name(uid)
            msg += f"{i}. **{name}**: เลเวล `{lvl}` (EXP: `{exp}`)\n"
        await ctx.send(msg)
    
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
        
    # --- คำสั่ง !use <เลขไอเทม> ---
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

        # ถ้าไม่ตรงกับอะไรเลย
        else:
            return await ctx.send(f"❌ ไอเทม **{item_name}** ยังไม่สามารถกดใช้งานได้ในตอนนี้")

        # --- 4. หักไอเทมออกจากกระเป๋า ---
        inv_array.remove(item_id) 
        player_model.update_player_field(user_id, "inventory", ",".join(inv_array))
        
        await ctx.send(msg)

# 🚨 ลบอันที่ซ้ำออกเหลือแค่อันเดียว
async def setup(bot):
    await bot.add_cog(PlayerCommands(bot))