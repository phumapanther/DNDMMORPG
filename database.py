import sqlite3
import json

DB_NAME = "game_data.db"

def init_db():
    """สร้างตารางข้อมูลเมื่อเปิดบอทครั้งแรกถ้ายังไม่มี"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 🔧 แก้ไข syntax: เติมลูกน้ำ (,) ให้ครบทุกบรรทัด และเพิ่ม exp ที่จำเป็นต้องใช้
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
            current_state TEXT DEFAULT 'village',
            last_event TEXT DEFAULT 'none',
            last_death TEXT,
            village_cooldown INTEGER DEFAULT 0,
            dungeon_steps INTEGER DEFAULT 0,
            total_online_time INTEGER DEFAULT 0,
            arrest_until INTEGER DEFAULT 0,
            total_text INTEGER DEFAULT 0,
            event_text INTEGER DEFAULT 0,
            exp INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_player(user_id):
    """ดึงข้อมูลผู้เล่น ถ้าไม่มีให้สร้างโปรไฟล์ใหม่ทันที"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 💡 ทริคใหม่: ใช้ list เก็บชื่อคอลัมน์เพื่อความง่ายในการดึงข้อมูล
    columns = [
        "level", "hp", "max_hp", "cash", "bank", "inventory", "armor", 
        "current_state", "last_event", "last_death", "village_cooldown", 
        "dungeon_steps", "total_online_time", "arrest_until", 
        "total_text", "event_text", "exp"
    ]
    
    query = f"SELECT {', '.join(columns)} FROM players WHERE user_id = ?"
    cursor.execute(query, (user_id,))
    row = cursor.fetchone()
    
    if row is None:
        # ถ้ายังไม่มีข้อมูล ให้ INSERT แค่ user_id เดี๋ยวค่า DEFAULT ในตารางจะจัดการใส่ค่าเริ่มต้นที่เหลือให้เองทั้งหมด!
        cursor.execute("INSERT INTO players (user_id) VALUES (?)", (user_id,))
        conn.commit()
        # ดึงข้อมูลที่เพิ่งสร้างใหม่กลับมา เพื่อความชัวร์ 100%
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        
    conn.close()
    
    # จัดคู่ชื่อคอลัมน์กับข้อมูลอัตโนมัติ (ไม่ต้องมานั่งไล่ row[0], row[1] อีกต่อไป)
    player_data = dict(zip(columns, row))
    
    # แปลง inventory กลับเป็น list อย่างปลอดภัย
    try:
        player_data["inventory"] = json.loads(player_data["inventory"])
    except:
        player_data["inventory"] = []
        
    return player_data

def update_player_field(user_id, field, value):
    """อัปเดตข้อมูลรายช่อง"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if isinstance(value, list):
        value = json.dumps(value)
    cursor.execute(f"UPDATE players SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

# ==========================================
# ➕ ฟังก์ชันเสริมพิเศษป้องกันโค้ด Voice Chat พัง
# ==========================================
def increment_player_field(user_id, field, amount=1):
    """บวกเพิ่มค่าในฟิลด์ตัวเลขโดยตรง (ต้องมีไว้สำหรับระบบแจก EXP ห้องเสียง)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE players SET {field} = {field} + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()