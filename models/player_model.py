import sqlite3
import json

DB_NAME = "game_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. สร้างตารางพื้นฐาน (ถ้ายังไม่มี)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            cash INTEGER DEFAULT 500,
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
    
    # 🔍 ดึงรายชื่อคอลัมน์ปัจจุบันขึ้นมาสแกน เพื่อทำ Auto-Migration
    cursor.execute("PRAGMA table_info(players)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # 🎯 [Auto-Migration 1] เพิ่มคอลัมน์ exp (ถ้ายังไม่มีใน DB เก่า)
    if "exp" not in columns:
        try:
            cursor.execute("ALTER TABLE players ADD COLUMN exp INTEGER DEFAULT 0;")
            print("📊 [SQL Migration] เพิ่มคอลัมน์ 'exp' สำเร็จ!")
        except sqlite3.OperationalError:
            pass

    # 🎯 [Auto-Migration 2] เพิ่มคอลัมน์ rank มารองรับระบบยศดิสคอร์ด (ถ้ายังไม่มีใน DB เก่า)
    if "rank" not in columns:
        try:
            cursor.execute("ALTER TABLE players ADD COLUMN rank TEXT DEFAULT 'F';")
            print("📊 [SQL Migration] เพิ่มคอลัมน์ 'rank' เข้าสู่ฐานข้อมูลเก่าสำเร็จ!")
        except sqlite3.OperationalError:
            pass
            
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # 🔥 ใช้ระบบดึงข้อมูลแบบ Dict-Key ป้องกันเรื่องจำลำดับ Row พลาด
    cursor = conn.cursor()
    
    # 🌟 [ปรับจุดนี้] ใช้ * เพื่อสั่งดึงข้อมูลมา "ทุกคอลัมน์" ที่มีอยู่ในตาราง players ทันที!
    cursor.execute("""
        SELECT * FROM players WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        # ตรง INSERT นี้เรายังต้องระบุฟิลด์ชัดเจนเผื่อเวลาสร้างไอดีใหม่ให้ระบบรู้ว่ายัดค่าลงช่องไหนครับ
        cursor.execute("""
            INSERT INTO players (user_id, level, exp, rank, hp, max_hp, cash, bank, inventory, armor, current_state, last_event, last_death, village_cooldown, dungeon_steps, total_online_time) 
            VALUES (?, 1, 0, 'F', 100, 100, 500, 0, '[]', 'None', 'idle', 'none', NULL, 0, 0, 0)
        """, (user_id,))
        conn.commit()
        conn.close()
        return {
            "level": 1, "exp": 0, "rank": "F", "hp": 100, "max_hp": 100, "cash": 500, "bank": 0,
            "inventory": [], "armor": "None", "current_state": "idle", "last_event": "none", "last_death": None, "village_cooldown": 0, "dungeon_steps": 0,
            "total_online_time": 0
        }
    
    conn.close()
    
    # แปลง Row วัตถุให้เป็น Standard Python Dictionary เพื่อให้ไฟล์อื่นดึงไป .get() ได้ไม่เออร์เรอร์
    p_dict = dict(row)
    p_dict["inventory"] = json.loads(p_dict["inventory"])
    return p_dict

def update_player_field(user_id, field, value):
    """ฟังก์ชันอัปเดตฟิลด์เดี่ยว (ดึงกลับมาช่วยซัพพอร์ตระบบเก่าไม่ให้พัง)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if isinstance(value, list):
        value = json.dumps(value)
    cursor.execute(f"UPDATE players SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def increment_player_field(user_id, field, amount=1):
    """ฟังก์ชันสำหรับบวกเพิ่มค่าในฐานข้อมูลโดยเฉพาะ (เช่น บวกเวลา, บวกเงิน) โดยไม่สนค่าเดิมในบอท"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # สั่งให้ SQL เอาค่าเดิมในคอลัมน์นั้น ๆ มาบวกเพิ่มตามจำนวนที่ส่งมาทันที
    cursor.execute(f"UPDATE players SET {field} = {field} + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_player_fields(user_id, updates: dict):
    """ฟังก์ชันอัปเดตฟิลด์หลายๆ ตัวพร้อมกันในคิวรีเดียว ช่วยลดปัญหาคอขวด DB หน่วง"""
    if not updates: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    set_clauses = []
    values = []
    for field, value in updates.items():
        if isinstance(value, list):
            value = json.dumps(value)
        set_clauses.append(f"{field} = ?")
        values.append(value)
        
    values.append(user_id)
    sql = f"UPDATE players SET {', '.join(set_clauses)} WHERE user_id = ?"
    cursor.execute(sql, values)
    conn.commit()
    conn.close()

def add_exp(user_id, exp_to_add):
    """ฟังก์ชันคำนวณ EXP โครงสร้างใหม่ รองรับลูปเคลียร์เกมใน 3 เดือน (Max Lv.100)"""
    player = get_player(user_id) 
    
    current_exp = player.get("exp", 0) + exp_to_add
    current_level = player.get("level", 1)
    max_hp = player.get("max_hp", 100)
    
    level_up_occurred = False
    
    while True:
        if current_level >= 100:
            current_exp = 0 # ล็อกเมื่อเลเวลเต็ม 100
            break
            
        # 🎯 สูตรเสพสมดุล: (เลเวลปัจจุบัน ยกกำลัง 2) คูณด้วย 70
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

# ─── 🏅 ฟังก์ชันคำนวณระบบยศอัตโนมัติ (Rank System) ───

def calculate_rank(level):
    """คำนวณหากลุ่มยศที่ถูกต้องตามเกณฑ์เลเวล"""
    if level >= 100: return "SSS"
    elif level >= 80: return "A"
    elif level >= 50: return "B"
    elif level >= 20: return "C"
    elif level >= 10: return "D"
    elif level >= 5: return "E"
    else: return "F"

def check_and_update_rank(user_id, current_level):
    """ตรวจสอบยศปัจจุบันใน DB ถ้าเลเวลถึงเกณฑ์ใหม่ ให้ทำการอัปเดตลงตารางทันที"""
    player = get_player(user_id)
    if not player:
        return False, "F"
    
    old_rank = player.get("rank", "F")
    new_rank = calculate_rank(current_level)
    
    if old_rank != new_rank:
        update_player_field(user_id, "rank", new_rank)
        return True, new_rank
        
    return False, old_rank