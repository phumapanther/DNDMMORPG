import random
from controller.bot_brain import BlackjackBot
from controller import db_manager
import json

def train_alpha_bot(iterations=5000):
    print(f"[LOG] [TRAINER] 🚀 เริ่มต้นกระบวนการฝึกสอน AlphaBot จำนวน {iterations} รอบ...")
    
    # โหลดสมองบอท
    bot = BlackjackBot()
    
    for i in range(iterations):
        # จำลองสถานการณ์ (State)
        p_score = random.randint(12, 24)
        d_upcard = random.randint(1, 10)
        
        # บอทตัดสินใจ (ให้สุ่มเยอะหน่อยในช่วงแรกด้วย epsilon=0.5)
        action = bot.get_action(p_score, d_upcard, epsilon=0.5)
        
        # เงื่อนไขการให้คะแนน (Reward Logic)
        reward = 0
        if action == "!hit":
            if p_score + random.randint(1, 10) > 24:
                reward = -1.0 # โดนทำโทษ (Bust)
            else:
                reward = 0.2 # ได้รางวัลนิดหน่อยที่จั่วแล้วไม่เกิน
        else: # Stand (!c)
            if p_score > 18: 
                reward = 0.8 # ชมเชยที่พอในแต้มที่ดี
            else:
                reward = -0.5 # ทำโทษที่พอในแต้มที่น้อยเกินไป
        
        # สั่งให้บอทเรียนรู้จากผลลัพธ์
        bot.learn(p_score, d_upcard, action, reward)
        
        if (i + 1) % 1000 == 0:
            print(f"[LOG] [TRAINER] ⚙️ เทรนไปแล้ว {i+1} รอบ...")

    # บันทึกความจำลงฐานข้อมูลหลังจากเทรนเสร็จ
    memory_json = json.dumps(bot.q_table)
    db_manager.save_bot_memory(memory_json, 'AlphaBot')
    print(f"[LOG] [TRAINER] ✅ เทรนบอทสำเร็จและบันทึกความจำลง Database เรียบร้อย!")

if __name__ == "__main__":
    train_alpha_bot(5000)