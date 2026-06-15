import sqlite3
import json

DB_NAME = "game_data.db"

def init_db():
    """สร้างตารางข้อมูลเมื่อเปิดบอทครั้งแรกถ้ายังไม่มี"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # เพิ่มคอลัมน์ armorเก็บชื่อเกราะที่สวมใส่อยู่ (เริ่มต้นเป็น 'None' คือร่างเปล่า)
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
            last_death TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_player(user_id):
    """ดึงข้อมูลผู้เล่น ถ้าไม่มีให้สร้างโปรไฟล์ใหม่ทันที"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT level, hp, max_hp, cash, bank, inventory, armor, current_state, last_event, last_death FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute("INSERT INTO players (user_id, level, cash, armor) VALUES (?, 1, 500, 'None')", (user_id,))
        conn.commit()
        conn.close()
        return {
            "level": 1, "hp": 100, "max_hp": 100, "cash": 500, "bank": 0,
            "inventory": [], "armor": "None", "current_state": "idle", "last_event": "none", "last_death": None
        }
    
    conn.close()
    return {
        "level": row[0], "hp": row[1], "max_hp": row[2], "cash": row[3], "bank": row[4],
        "inventory": json.loads(row[5]), "armor": row[6], "current_state": row[7], "last_event": row[8], "last_death": row[9]
    }

def update_player_field(user_id, field, value):
    """อัปเดตข้อมูลรายช่อง"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if isinstance(value, list):
        value = json.dumps(value)
    cursor.execute(f"UPDATE players SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()