# player_model.py
import sqlite3
import json
import time # อย่าลืม import time เข้ามานะครับ

DB_NAME = "game_data.db"

# 🌟 [จุดปรับแต่งก้อนเดียวจบ] กำหนดสเตตัสเริ่มต้นของ "ผู้เล่นใหม่" ทั้งหมดไว้ที่นี่
# อนาคตอยากเพิ่มฟิลด์ หรือปรับเงินเริ่มต้น (เช่น จาก 500 เป็น 1000) มาแก้ตรงนี้ได้เลยครับ!
NEW_PLAYER_DEFAULTS = {
    "level": 1,
    "exp": 0,
    "rank": "F",
    "hp": 100,
    "max_hp": 100,
    "cash": 20000,
    "bank": 0,
    "inventory": "[]",
    # 🛡️ ระบบไอเทมสวมใส่
    "armor": "None",
    "armor_dur": 100,      # ตามค่า None ใน ARMOR_STATS
    "weapon": "Wooden_Weapon",
    "weapon_dur": 50,      # ตามค่า Wooden_Weapon ใน WEAPON_STATS
    # สถานะอื่นๆ
    "current_state": "idle",
    "last_event": "none",
    "last_death": None,
    "village_cooldown": 0,
    "dungeon_steps": 0,
    "total_online_time": 0,
    "arrest_until": 0
}
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. สร้างตารางพื้นฐาน
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            cash INTEGER DEFAULT 20000,
            bank INTEGER DEFAULT 0,
            inventory TEXT DEFAULT '[]',
            armor TEXT DEFAULT 'None',
            current_state TEXT DEFAULT 'idle',
            last_event TEXT DEFAULT 'none',
            last_death TEXT,
            village_cooldown INTEGER DEFAULT 0,
            dungeon_steps INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()
    
    # 2. รันระบบอัปเดตโครงสร้างคอลัมน์ให้อัตโนมัติ (ขยายตาม NEW_PLAYER_DEFAULTS)
    auto_update_schema()

def get_player(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        # 🤖 ลอจิกอัจฉริยะ: ประกอบร่างคำสั่ง INSERT อัตโนมัติตาม NEW_PLAYER_DEFAULTS บนสุด
        fields = ["user_id"] + list(NEW_PLAYER_DEFAULTS.keys())
        placeholders = ["?"] * len(fields)
        
        # ดึงค่าจากตัวแปรด้านบนมาเตรียมยัดลง DB
        values = [user_id]
        for key, val in NEW_PLAYER_DEFAULTS.items():
            # ดักเคสพิเศษพวกตัวแปรเลขที่อยากให้ยืดหยุ่นในโค้ด
            if key == "cash": val = NEW_PLAYER_DEFAULTS["cash"]
            values.append(val)
            
        sql_insert = f"INSERT INTO players ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
        
        cursor.execute(sql_insert, values)
        conn.commit()
        conn.close()
        
        init_profile = NEW_PLAYER_DEFAULTS.copy()
        
        # 🛠️ จุดที่ 1: ยกเลิกการใช้ json.loads สำหรับผู้เล่นใหม่
        raw_inv = str(init_profile.get("inventory", ""))
        for char in ["(", ")", "[", "]", "'", '"', " "]:
            raw_inv = raw_inv.replace(char, "")
        init_profile["inventory"] = raw_inv
        
        return init_profile
    
    conn.close()
    
    p_dict = dict(row)
    
    # 🛠️ จุดที่ 2: ยกเลิกการใช้ json.loads สำหรับผู้เล่นเก่า (แก้บั๊กที่ทำบอทดับ)
    raw_inv = str(p_dict.get("inventory", ""))
    for char in ["(", ")", "[", "]", "'", '"', " "]:
        raw_inv = raw_inv.replace(char, "")
    p_dict["inventory"] = raw_inv
    
    return p_dict

# ─── 💾 โซนฟังก์ชันจัดการสเตตัสความปลอดภัย ───

def update_player_field(user_id, field, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if isinstance(value, list) or isinstance(value, dict):
        value = json.dumps(value)
    cursor.execute(f"UPDATE players SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def increment_player_field(user_id, field, amount=1):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE players SET {field} = {field} + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_player_fields(user_id, updates: dict):
    if not updates: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    set_clauses = []
    values = []
    for field, value in updates.items():
        if isinstance(value, list) or isinstance(value, dict):
            value = json.dumps(value)
        set_clauses.append(f"{field} = ?")
        values.append(value)
        
    values.append(user_id)
    sql = f"UPDATE players SET {', '.join(set_clauses)} WHERE user_id = ?"
    cursor.execute(sql, values)
    conn.commit()
    conn.close()

def add_exp(user_id, exp_to_add):
    player = get_player(user_id) 
    current_exp = player.get("exp", 0) + exp_to_add
    current_level = player.get("level", 1)
    max_hp = player.get("max_hp", 100)
    level_up_occurred = False
    
    while True:
        if current_level >= 100:
            current_exp = 0
            break
        required_exp = (current_level ** 2) * 70
        if current_exp >= required_exp:
            current_exp -= required_exp
            current_level += 1
            max_hp += 20 
            level_up_occurred = True
        else:
            break
            
    update_player_field(user_id, "exp", current_exp)
    update_player_field(user_id, "level", current_level)
    if level_up_occurred:
        update_player_field(user_id, "max_hp", max_hp)
        update_player_field(user_id, "hp", max_hp) 
    return level_up_occurred, current_level, current_exp

def calculate_rank(level):
    if level >= 100: return "SSS"
    elif level >= 80: return "A"
    elif level >= 50: return "B"
    elif level >= 20: return "C"
    elif level >= 10: return "D"
    elif level >= 5: return "E"
    else: return "F"

def check_and_update_rank(user_id, current_level):
    player = get_player(user_id)
    if not player: return False, "F"
    old_rank = player.get("rank", "F")
    new_rank = calculate_rank(current_level)
    if old_rank != new_rank:
        update_player_field(user_id, "rank", new_rank)
        return True, new_rank
    return False, old_rank

# ─── ⚙️ โซนระบบขยายข้อมูลอัตโนมัติสำหรับอนาคต (Scalability Zone) ───

def auto_update_schema():
    """ระบบตรวจจับคอลัมน์อัตโนมัติ อิงจากตาราง NEW_PLAYER_DEFAULTS"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(players);")
    columns = [row[1] for row in cursor.fetchall()]
    
    # ดักจับคอลัมน์เผื่อเก่าที่จำเป็นต้องมี
    if "exp" not in columns:
        try: cursor.execute("ALTER TABLE players ADD COLUMN exp INTEGER DEFAULT 0;")
        except: pass
    if "rank" not in columns:
        try: cursor.execute("ALTER TABLE players ADD COLUMN rank TEXT DEFAULT 'F';")
        except: pass

    # ลูปสแกนหาตัวแปรใหม่ ๆ ในคลังจอง NEW_PLAYER_DEFAULTS ถ้าไม่มีในเครื่องคลาวด์ จะยัดคำสั่งงอกคอลัมน์ให้เองทันที
    for col_name, default_val in NEW_PLAYER_DEFAULTS.items():
        if col_name not in columns:
            col_type = "TEXT" if isinstance(default_val, str) else "INTEGER"
            d_val = f"'{default_val}'" if isinstance(default_val, str) else default_val
            if default_val is None: d_val = "NULL"
            
            try:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_type} DEFAULT {d_val};")
                print(f"⚙️ [FUTURE-MIGRATION] งอกคอลัมน์ใหม่ '{col_name}' สำเร็จ!")
            except Exception as e:
                print(f"⚠️ [MIGRATION ERROR] ไม่สามารถงอกฟิลด์ {col_name} ได้: {e}")
                
    conn.commit()
    conn.close()

def execute_custom_game_logic(user_id, action_type, **kwargs):
    """
    🔮 [จุดเตรียมพร้อมเพิ่มคำสั่งใหม่ในอนาคต]
    คุณอาเธอร์สามารถมาเขียนดักพวกคำสั่ง Event แปลก ๆ หรือเงื่อนไขใหม่ที่นี่ได้เลยโดยไม่กระทบโครงสร้างหลัก
    """
    player = get_player(user_id)
    if not player: return False
    
    if action_type == "custom_buff":
        # ตัวอย่างลอจิก: สั่งเพิ่มพลังงานหรือบัฟในอนาคต
        pass
        
    return True

# เพิ่มฟังก์ชันนี้ใน player_model.py
def check_jail_status(user_id):
    player = get_player(user_id)
    if player and player["current_state"] == "arrested":
        # ถ้าเวลาปัจจุบัน เกินกว่าเวลาที่กำหนดใน DB
        if time.time() >= player["arrest_until"]:
            update_player_fields(user_id, {"current_state": "idle", "arrest_until": 0})
            return True # หลุดจากคุกแล้ว
    return False # ยังติดคุกอยู่

from discord.ext import tasks

@tasks.loop(minutes=1.0)
async def jail_checker(self):
    # ดึงทุกคนที่สถานะเป็น 'arrested'
    conn = sqlite3.connect("game_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM players WHERE current_state = 'arrested' AND arrest_until <= ?", (time.time(),))
    jailed_players = cursor.fetchall()
    
    for row in jailed_players:
        user_id = row[0]
        # สั่งปลดคุก
        update_player_fields(user_id, {"current_state": "idle", "arrest_until": 0})
        print(f"🔓 ปลดคุกผู้เล่น {user_id} อัตโนมัติ")
    conn.close()

def execute_raw_sql(sql):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()  # ต้องมีบรรทัดนี้ ไม่งั้นข้อมูลไม่เซฟ
    conn.close()