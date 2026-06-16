import discord
from discord.ext import commands
import asyncio

class AdventureZone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── ⚔️ คำสั่งเปิดห้องผจญภัยส่วนตัว และลบทิ้งอัตโนมัติเมื่อเงียบครบ 1 นาที (!adv) ───
    @commands.command(name="adv")
    @commands.cooldown(1, 10.0, commands.BucketType.user) # ดักคูลดาวน์ป้องกันปั๊มห้องรัวๆ
    async def create_adventure_room(self, ctx):
        """คำสั่งสร้างห้องแชทผจญภัยออโต้ ถัดจากห้องเดิม ล็อกสิทธิ์ และลบทิ้งเมื่อไม่มีการเคลื่อนไหวใน 1 นาที"""
        guild = ctx.guild
        author = ctx.author
        current_channel = ctx.channel # ห้องที่พิมพ์คำสั่ง

        # ⏳ ส่งข้อความแจ้งเตือนเบื้องต้นว่ากำลังร่ายเวทสร้างห้อง
        status_msg = await ctx.send(f"⏳ **[สมาคมนักผจญภัย]** กำลังจัดเตรียมมิติส่วนตัวให้คุณ {author.mention}...")

        # 🛡️ เซ็ตค่า Permissions (ปิดคนอื่น เปิดให้คนใช้คำสั่งเห็นคนเดียว)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) # ให้ตัวบอทเห็นด้วย
        }

        try:
            # 📐 คำนวณตำแหน่งเพื่อให้ห้องใหม่สร้างอยู่ถัดลงมาจากห้องเดิมเป๊ะๆ
            new_position = current_channel.position + 1

            # 🛠️ สั่งสร้างห้องข้อความใหม่
            room_name = f"⚔️-มิติส่วนตัว-{author.name}"
            adv_channel = await guild.create_text_channel(
                name=room_name,
                category=current_channel.category,
                position=new_position,
                overwrites=overwrites,
                topic=f"ห้องผจญภัยส่วนตัวของ {author.name} | เงียบครบ 1 นาทีห้องจะปิดตัวลงทันที"
            )

            # 🎨 สร้าง Embed ต้อนรับเมื่อเปิดประตูมิติสำเร็จ
            embed = discord.Embed(
                title=f"🌲 มิติผจญภัยส่วนตัวของ {author.name}",
                description=(
                    f"ยินดีต้อนรับคุณ {author.mention} เข้าสู่ห้องจำลองการเดินทาง!\n"
                    f"🔒 **ห้องนี้เป็นห้องลับ:** มีเพียงคุณและผู้ดูแลระบบเท่านั้นที่มองเห็นเนื้อหาในนี้\n\n"
                    f"⚠️ **[ระบบทำลายตัวเองทำงาน]:** หากไม่มีการพิมพ์ข้อความใด ๆ ในห้องนี้เป็นเวลา **1 นาที** ห้องนี้จะสลายหายไปทันทีครับ!"
                ),
                color=0x319795
            )
            embed.set_thumbnail(url=author.display_avatar.url)
            await adv_channel.send(embed=embed)

            # 🧼 อัปเดตข้อความห้องเดิม ส่งลิงก์วาร์ปให้คนเล่นคลิกเด้งไปห้องใหม่
            await status_msg.edit(content=f"✨ **[ประตูมิติเปิดออกแล้ว!]** คุณ {author.mention} สามารถเคลื่อนย้ายไปยังห้องผจญภัยได้ที่นี่ ➡️ {adv_channel.mention}")

            # ==========================================================
            # ⏱️ [ระบบดักเวลาออโต้รีเซ็ตเมื่อมีคนพิมพ์แชท]
            # ==========================================================
            def check(message):
                # ดักจับว่ามีการพิมพ์ข้อความใดๆ ลงมาในห้องใหม่นี้หรือไม่
                return message.channel.id == adv_channel.id

            while True:
                try:
                    # บอทจะจ้องมองห้องนี้เป็นเวลา 60 วินาที (1 นาที)
                    # ถ้าระหว่าง 60 วิ มีคนพิมพ์อะไรลงมา ลูปจะวนเริ่มนับ 1 ใหม่ทันที (ต่อเวลาให้)
                    await self.bot.wait_for('message', check=check, timeout=60.0)
                    print(f"🔄 [Adventure Zone] ห้อง {room_name} มีการเคลื่อนไหว ระบบต่อเวลาให้เพิ่มอีก 1 นาที")
                
                except asyncio.TimeoutError:
                    # 💥 เคสที่หลุด Timeout (เงียบเหงาครบ 60 วินาทีโดยไม่มีใครพิมพ์อะไรเลย)
                    print(f"💥 [Adventure Zone] ห้อง {room_name} เงียบเกิน 1 นาที ระบบสั่งทำลายห้องถาวร")
                    
                    # สั่งลบห้องแชทนี้ออกจากดิสคอร์ดทันที
                    await adv_channel.delete(reason="ห้องผจญภัยไม่มีการเคลื่อนไหวครบ 1 นาที")
                    
                    # ส่งข้อความบอกในห้องเก่า (ห้องหลักที่ใช้เปิดคำสั่ง) เพื่อให้รู้ว่าห้องปิดแล้ว
                    try:
                        await ctx.send(f"🌌 **[มิติสลาย]** มิติส่วนตัวของคุณ {author.mention} ได้สลายหายไปเรียบร้อยแล้วเนื่องจากไม่มีการเคลื่อนไหวครบ 1 นาที", delete_after=5.0)
                    except:
                        pass
                    break # หลุดออกจากลูปเพื่อจบบรรทัดการทำงาน

        except discord.Forbidden:
            await status_msg.edit(content="❌ **บอทเกิดข้อผิดพลาด:** บอทไม่มีสิทธิ์ในการจัดการห้องแชท (`Manage Channels`) กรุณาตรวจสอบสิทธิ์ยศของบอทด้วยครับ")
        except Exception as e:
            print(f"⚠️ เกิดข้อผิดพลาดในการสร้างห้อง !adv: {e}")

    # ─── 🚨 ดักจับ Error คูลดาวน์ของคำสั่ง !adv ───
    @create_adventure_room.error
    async def adv_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            pass
        elif isinstance(error, commands.CommandOnCooldown):
            try:
                await ctx.send(f"⏱️ **[มิติกำลังฟื้นฟู]** กรุณารออีก `{error.retry_after:.1f}` วินาที ถึงจะเปิดห้องผจญภัยใหม่ได้อีกครั้งครับ", delete_after=4.0)
            except:
                pass

# ฟังก์ชันโหลด Cog เข้าสู่ระบบบอทหลัก
async def setup(bot):
    await bot.add_cog(AdventureZone(bot))