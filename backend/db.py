"""
数据库层 · SQLite（零依赖，可平滑迁移到 PostgreSQL）
"""
import json
import sqlite3
import time
from contextlib import contextmanager

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS whitelist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phone       TEXT NOT NULL UNIQUE,
    name        TEXT DEFAULT '',
    remark      TEXT DEFAULT '',
    status      TEXT DEFAULT 'active',      -- active / banned
    created_at  INTEGER NOT NULL,
    last_login  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phone       TEXT NOT NULL UNIQUE,
    data        TEXT NOT NULL DEFAULT '{}',  -- JSON 全量表单数据
    photos      TEXT NOT NULL DEFAULT '{}',  -- JSON 附件路径
    status      TEXT DEFAULT 'draft',        -- draft / submitted
    progress    INTEGER DEFAULT 0,           -- 0-100
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL,
    submitted_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notify_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id   INTEGER NOT NULL,
    phone       TEXT NOT NULL,
    name        TEXT DEFAULT '',
    payload     TEXT DEFAULT '',
    sent        INTEGER DEFAULT 0,
    error       TEXT DEFAULT '',
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resumes_status ON resumes(status);
CREATE INDEX IF NOT EXISTS idx_whitelist_phone ON whitelist(phone);
"""


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def now() -> int:
    return int(time.time())


# ---------- 白名单 ----------

def wl_add(phone: str, name: str = "", remark: str = "") -> bool:
    """添加白名单，已存在则返回 False"""
    with connect() as conn:
        try:
            conn.execute(
                "INSERT INTO whitelist (phone, name, remark, created_at) VALUES (?,?,?,?)",
                (phone.strip(), name.strip(), remark.strip(), now()),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def wl_bulk_add(rows) -> dict:
    """批量导入 [(phone, name, remark), ...]"""
    ok, dup, bad = 0, 0, 0
    with connect() as conn:
        for item in rows:
            phone = (item[0] if len(item) > 0 else "") or ""
            name = (item[1] if len(item) > 1 else "") or ""
            remark = (item[2] if len(item) > 2 else "") or ""
            phone = normalize_phone(phone)
            if not phone:
                bad += 1
                continue
            try:
                conn.execute(
                    "INSERT INTO whitelist (phone, name, remark, created_at) VALUES (?,?,?,?)",
                    (phone, str(name).strip(), str(remark).strip(), now()),
                )
                ok += 1
            except sqlite3.IntegrityError:
                dup += 1
        conn.commit()
    return {"added": ok, "duplicated": dup, "invalid": bad}


def wl_delete(phone: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM whitelist WHERE phone=?", (normalize_phone(phone),))
        conn.commit()
        return cur.rowcount > 0


def wl_set_status(phone: str, status: str) -> bool:
    with connect() as conn:
        cur = conn.execute(
            "UPDATE whitelist SET status=? WHERE phone=?", (status, normalize_phone(phone))
        )
        conn.commit()
        return cur.rowcount > 0


def wl_find(phone: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM whitelist WHERE phone=?", (normalize_phone(phone),)
        ).fetchone()
        return dict(row) if row else None


def wl_list(keyword: str = ""):
    with connect() as conn:
        sql = """
            SELECT w.*, r.status AS r_status, r.progress AS r_progress,
                   r.updated_at AS r_updated, r.submitted_at AS r_submitted
            FROM whitelist w
            LEFT JOIN resumes r ON r.phone = w.phone
        """
        params = ()
        if keyword:
            sql += " WHERE w.phone LIKE ? OR w.name LIKE ? OR w.remark LIKE ?"
            kw = f"%{keyword}%"
            params = (kw, kw, kw)
        sql += " ORDER BY w.created_at DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def wl_touch_login(phone: str):
    with connect() as conn:
        conn.execute("UPDATE whitelist SET last_login=? WHERE phone=?", (now(), phone))
        conn.commit()


def wl_stats() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM whitelist WHERE status='active'").fetchone()["c"]
        banned = conn.execute("SELECT COUNT(*) c FROM whitelist WHERE status='banned'").fetchone()["c"]
        submitted = conn.execute(
            "SELECT COUNT(*) c FROM whitelist w JOIN resumes r ON r.phone=w.phone WHERE r.status='submitted'"
        ).fetchone()["c"]
        drafting = conn.execute(
            "SELECT COUNT(*) c FROM whitelist w JOIN resumes r ON r.phone=w.phone WHERE r.status='draft' AND r.progress>0"
        ).fetchone()["c"]
        return {
            "total": total,
            "banned": banned,
            "submitted": submitted,
            "drafting": drafting,
            "not_started": max(0, total - submitted - drafting),
        }


# ---------- 简历 ----------

def rv_get(phone: str):
    with connect() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE phone=?", (phone,)).fetchone()
        return dict(row) if row else None


def rv_save(phone: str, data: dict, photos: dict, progress: int, status: str = "draft") -> dict:
    ts = now()
    with connect() as conn:
        exist = conn.execute("SELECT id, status FROM resumes WHERE phone=?", (phone,)).fetchone()
        if exist:
            # 已提交的简历再次保存 -> 回到 draft 允许修改并重新提交
            new_status = status
            conn.execute(
                """UPDATE resumes SET data=?, photos=?, progress=?, updated_at=?, status=?,
                   submitted_at=CASE WHEN ?='submitted' THEN ? ELSE submitted_at END
                   WHERE phone=?""",
                (
                    json.dumps(data, ensure_ascii=False),
                    json.dumps(photos, ensure_ascii=False),
                    progress,
                    ts,
                    new_status,
                    new_status,
                    ts,
                    phone,
                ),
            )
            rid = exist["id"]
        else:
            cur = conn.execute(
                """INSERT INTO resumes (phone, data, photos, status, progress, created_at, updated_at, submitted_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    phone,
                    json.dumps(data, ensure_ascii=False),
                    json.dumps(photos, ensure_ascii=False),
                    status,
                    progress,
                    ts,
                    ts,
                    ts if status == "submitted" else 0,
                ),
            )
            rid = cur.lastrowid
        conn.commit()
    return {"id": rid, "status": status}


def rv_list(keyword: str = "", status: str = ""):
    with connect() as conn:
        sql = """
            SELECT r.*, w.name AS wl_name, w.remark AS wl_remark
            FROM resumes r LEFT JOIN whitelist w ON w.phone = r.phone
            WHERE 1=1
        """
        params = []
        if status:
            sql += " AND r.status=?"
            params.append(status)
        if keyword:
            sql += " AND (r.phone LIKE ? OR w.name LIKE ? OR r.data LIKE ?)"
            kw = f"%{keyword}%"
            params += [kw, kw, kw]
        sql += " ORDER BY r.updated_at DESC"
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    for r in rows:
        try:
            d = json.loads(r["data"] or "{}")
            r["basic_name"] = (d.get("basic") or {}).get("name", "")
            r["school"] = ((d.get("education") or {}).get("rows") or [{}])[0].get("school", "")
        except Exception:
            r["basic_name"] = ""
            r["school"] = ""
    return rows


def rv_get_by_id(rid: int):
    with connect() as conn:
        row = conn.execute(
            """SELECT r.*, w.name AS wl_name FROM resumes r
               LEFT JOIN whitelist w ON w.phone=r.phone WHERE r.id=?""",
            (rid,),
        ).fetchone()
        return dict(row) if row else None


def rv_delete(rid: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM resumes WHERE id=?", (rid,))
        conn.commit()
        return cur.rowcount > 0


# ---------- 通知 ----------

def notify_log_add(resume_id: int, phone: str, name: str, payload: dict, sent: int, error: str = ""):
    with connect() as conn:
        conn.execute(
            """INSERT INTO notify_log (resume_id, phone, name, payload, sent, error, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (resume_id, phone, name, json.dumps(payload, ensure_ascii=False), sent, error, now()),
        )
        conn.commit()


def notify_list(limit: int = 100):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notify_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def notify_mark_sent(nid: int, sent: int = 1, error: str = ""):
    with connect() as conn:
        conn.execute("UPDATE notify_log SET sent=?, error=? WHERE id=?", (sent, error, nid))
        conn.commit()


# ---------- 工具 ----------

def normalize_phone(raw) -> str:
    """清洗手机号：去掉空格/横线/+86 等，返回 11 位或空"""
    if raw is None:
        return ""
    s = str(raw).strip().replace(" ", "").replace("-", "").replace("+86", "")
    s = s.replace("－", "").replace("　", "")
    if s.endswith(".0"):
        s = s[:-2]
    if s.isdigit() and len(s) == 11 and s.startswith("1"):
        return s
    return ""
