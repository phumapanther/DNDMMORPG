import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import models.player_model as player_model

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
# 🌟 [เพิ่มบรรทัดนี้] เปิดสิทธิ์ให้บอทมองเห็นและแสกนรายชื่อคนที่นั่งอยู่ในห้อง Voice
intents.voice_states = True 

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    player_model.init_db() # เรียกใช้ Model เพื่อรันดาเบส
    
    # โฟลว์การดึงโฟลเดอร์ cogs เข้ามาร่วมประมวลผล
    try:
        await bot.load_extension("cogs.game_commands")
        print("✅ โหลดโมดูลระบบคำนวณและควบคุม (Controller) สำเร็จ!")
    except Exception as e:
        print(f"❌ โดนสกัดการโหลด Cog: {e}")

    print(f'🤖 บอทออนไลน์แล้ว! ชื่อ: {bot.user.name}')
    print('----------------------------------------------------')

BOT_TOKEN = os.getenv("ARTHUR_TOKEN")
bot.run(BOT_TOKEN)