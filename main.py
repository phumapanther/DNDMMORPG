import discord
from discord.ext import commands
import asyncio
import sys
import os
from dotenv import load_dotenv
import models.player_model as player_model

# 🟢 1. โหลดไฟล์ .env เป็นสิ่งแรกสุด เพื่อให้ระบบรู้จัก Token
load_dotenv()

# 🔒 2. ดึงค่า Token ทั้ง 3 ตัวผ่าน Environment Variables
TOKEN_GAME       = os.getenv("ARTHUR_TOKEN")
TOKEN_CHAT_VOICE = os.getenv("PANDA_TOKEN")
TOKEN_ADMIN      = os.getenv("BOT_1984_TOKEN")

def create_bot(bot_type: str):
    """ฟังก์ชันเสกอินสแตนซ์บอทตามประเภทหน้าที่"""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True # 🌟 เปิดสิทธิ์แสกนรายชื่อในห้อง Voice

    bot = commands.Bot(command_prefix="!", intents=intents)
    bot.bot_type = bot_type

    @bot.event
    async def on_ready():
        player_model.init_db()
        
        # 🔄 [เพิ่มบรรทัดนี้] สั่งให้บอทลงทะเบียนและอัปเดตระบบสแลชคำสั่งเข้าเซิร์ฟเวอร์จริง
        try:
            synced = await bot.tree.sync()
            print(f"📊 [SYSTEM] ซิงค์ระบบคำสั่งสแลชสำเร็จทั้งหมด {len(synced)} คำสั่ง!")
        except Exception as e:
            print(f"⚠️ การซิงค์คำสั่งสแลชขัดข้อง: {e}")
            
        print(f"🟢 [SYSTEM ONLINE] บอทร่าง [{bot_type.upper()}] ออนไลน์แล้ว!")
        
    @bot.event
    async def on_setup():
        """โหลดโมดูลแยกตามสถานะการบายพาส"""
        try:
            # 🔄 [โหมดบายพาส] ถ้าเป็นบอทเกม (Arthur) ให้โหลดทั้งระบบเกม และระบบสแกนแชท/เสียง ควบสองตำแหน่งเลย!
            if bot_type == "game":
                await bot.load_extension("cogs.game_commands")
                print("⚔️ [Game Bot] โหลดระบบคำสั่งคอมแบทและร้านค้าสำเร็จ!")
                
                await bot.load_extension("cogs.voice_chat_tracker")
                print("🎙️ [Bypass Mode] โน้ตระบบลูปห้องเสียงและฟาร์มแชทมาให้ Arthur รันแทนชั่วคราวสำเร็จ!")
                
            elif bot_type == "chat":
                await bot.load_extension("cogs.voice_chat_tracker")
                print("🎙️ [Chat/Voice Bot] โหลดระบบลูปห้องเสียงและฟาร์มแชทสำเร็จ!")
                
            elif bot_type == "admin":
                print("👑 [Admin Bot] บอทตรวจสอบระบบ Standby พร้อมทำงาน!")
                
        except Exception as e:
            print(f"❌ [{bot_type.upper()}] โดนสกัดการโหลดโมดูล: {e}")

    async def custom_start(token):
        if not token:
            print(f"⚠️ [ERROR] ไม่พบค่า Token สำหรับบอทประเภท: {bot_type.upper()}")
            return
        async with bot:
            await on_setup()
            await bot.start(token)

    return custom_start

# 🚀 3. ฟังก์ชันควบคุมการจุดระเบิดเปิดบอท
async def main():
    print("⏳ กำลังเตรียมการเปิดระบบในโหมดบายพาส (บอทแรกตัวเดียว)...")
    
    # สั่งสร้างตัวรันบอทเกม (Arthur)
    run_game_bot = create_bot("game")

    # 🔥 [สั่งรันเฉพาะบอทแรก] บายพาสตัวที่ 2 และ 3 ออกไปก่อนชั่วคราว
    await asyncio.gather(
        run_game_bot(TOKEN_GAME),
        # run_chat_bot(TOKEN_CHAT_VOICE), # 💤 ปิดคอมเมนต์ไว้ชั่วคราว
        # run_admin_bot(TOKEN_ADMIN)      # 💤 ปิดคอมเมนต์ไว้ชั่วคราว
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 ปิดระบบการทำงานของบอทเรียบร้อยแล้วครับคุณอาเธอร์")