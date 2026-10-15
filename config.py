# config.py — valan bot + api config
import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
GUILD_ID       = int(os.getenv("GUILD_ID", "0"))
PANEL_USERNAME = os.getenv("PANEL_USERNAME", "valannnnnnnnnnnnnnnnnnnnnnnnnn")

API_HOST   = os.getenv("API_HOST", "127.0.0.1")
API_PORT   = int(os.getenv("API_PORT", "8080"))
API_PUBLIC = os.getenv("API_PUBLIC", "https://api.valan.shop")
API_SELF   = os.getenv("API_SELF",   "http://127.0.0.1:8080")
DB_PATH    = os.getenv("DB_PATH", "valan.db")

MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "6"))
MAX_TIME       = int(os.getenv("MAX_TIME", "250"))

MHDDOS_DIR = os.getenv("MHDDOS_DIR", "/home/ubuntu/MJ")

EMO_STAR   = os.getenv("EMO_STAR",   "<a:1000030144:1559280351254151199>")
EMO_WALLET = os.getenv("EMO_WALLET", "<:1000035915:1559174417097953340>")
EMO_BOLT   = os.getenv("EMO_BOLT",   "<:1000035915:1559174417097953340>")
EMO_BUTTON = os.getenv("EMO_BUTTON", "<:1000039186:1559961315642966026>")

PANEL_COLOR = 0x2b2d31

FORBIDDEN_TLDS = (".th", ".go.th", ".ac.th", ".mi.th", ".gov", ".go.jp")

# Free Fire endpoints (Garena)
FF_ENDPOINTS = [
    "ff01.garena.com",
    "ff02.garena.com",
    "ff03.garena.com",
]

# Discord voice UDP range — ใช้ยิง VC
DISCORD_VOICE_PORT_MIN = 50000
DISCORD_VOICE_PORT_MAX = 50050