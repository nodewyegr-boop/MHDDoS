# db.py — sqlite schema + helpers
import sqlite3, time, secrets, string
from config import DB_PATH

_conn = None

def conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _init(_conn)
    return _conn

def _init(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS vip (
        user_id    TEXT PRIMARY KEY,
        expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS api_keys (
        key        TEXT PRIMARY KEY,
        owner_id   TEXT,
        created_at INTEGER,
        expires_at INTEGER,
        active     INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS attacks (
        id          TEXT PRIMARY KEY,
        key         TEXT,
        target      TEXT,
        port        INTEGER,
        time        INTEGER,
        method      TEXT,
        status      TEXT,
        started_at  INTEGER,
        finished_at INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_attacks_key_status ON attacks(key, status);
    """)
    c.commit()

# ---- VIP ----
def is_vip(user_id):
    r = conn().execute(
        "SELECT expires_at FROM vip WHERE user_id=?", (str(user_id),)
    ).fetchone()
    if not r: return False
    return r[0] == 0 or r[0] > int(time.time())

def add_vip(user_id, expires_at):
    conn().execute(
        "INSERT OR REPLACE INTO vip(user_id,expires_at) VALUES (?,?)",
        (str(user_id), expires_at),
    ); conn().commit()

def remove_vip(user_id):
    conn().execute("DELETE FROM vip WHERE user_id=?", (str(user_id),))
    conn().commit()

def vip_expiry(user_id):
    r = conn().execute(
        "SELECT expires_at FROM vip WHERE user_id=?", (str(user_id),)
    ).fetchone()
    return r[0] if r else None

# ---- API keys ----
def _gen_key():
    a = string.ascii_letters + string.digits
    return ''.join(secrets.choice(a) for _ in range(20))

def create_key(owner_id, expires_at):
    for _ in range(8):
        k = _gen_key()
        try:
            conn().execute(
                "INSERT INTO api_keys(key,owner_id,created_at,expires_at,active) "
                "VALUES (?,?,?,?,1)",
                (k, str(owner_id), int(time.time()), expires_at),
            ); conn().commit()
            return k
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("key collision")

def get_key(key):
    return conn().execute(
        "SELECT key,owner_id,expires_at,active FROM api_keys WHERE key=?", (key,)
    ).fetchone()

def list_keys(owner_id):
    return conn().execute(
        "SELECT key,created_at,expires_at,active FROM api_keys "
        "WHERE owner_id=? ORDER BY created_at DESC",
        (str(owner_id),),
    ).fetchall()

# ---- attacks ----
def active_count(key):
    return conn().execute(
        "SELECT COUNT(*) FROM attacks WHERE key=? AND status='running'", (key,)
    ).fetchone()[0]

def create_attack(aid, key, target, port, t, method):
    conn().execute(
        "INSERT INTO attacks(id,key,target,port,time,method,status,started_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (aid, key, target, port, t, method, 'running', int(time.time())),
    ); conn().commit()

def finish_attack(aid):
    conn().execute(
        "UPDATE attacks SET status='finished', finished_at=? WHERE id=?",
        (int(time.time()), aid),
    ); conn().commit()

def get_attack(aid):
    return conn().execute("SELECT * FROM attacks WHERE id=?", (aid,)).fetchone()

def cleanup_stale():
    from config import MAX_TIME
    cutoff = int(time.time()) - (MAX_TIME + 60)
    conn().execute(
        "UPDATE attacks SET status='finished' WHERE status='running' "
        "AND started_at < ?", (cutoff,),
    ); conn().commit()