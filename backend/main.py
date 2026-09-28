"""
电力央国企简历填写系统 · FastAPI 后端
学员端：/sume/            手机号白名单登录 → 填表 → 自动保存 → 提交
管理端：/sume/admin       管理口令登录 → 名单管理 / 简历查看 / docx 导出
"""
import io
import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, URLSafeTimedSerializer
from openpyxl import Workbook, load_workbook
from pydantic import BaseModel

import db
import notify
from config import (ADMIN_PASSWORD, EXPORT_DIR, FRONTEND_DIR, NOTIFY_EMAIL,
                    PHOTO_DIR, SECRET_KEY)
from docx_export import export_resume
from schema import MODULES, calc_progress

app = FastAPI(title="思格简历系统", docs_url=None, redoc_url=None)
serializer = URLSafeTimedSerializer(SECRET_KEY, salt="resume-admin")

MAX_UPLOAD_MB = 12
ALLOWED_IMG = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def _cdn_header(filename: str) -> dict:
    """构造带中文文件名的下载响应头（RFC 5987 编码，避免 latin-1 报错）"""
    from urllib.parse import quote
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}


@app.on_event("startup")
def _startup():
    db.init_db()


# ══════════════════════════════════════════════
#  管理端鉴权
# ══════════════════════════════════════════════

def _make_token() -> str:
    return serializer.dumps({"role": "admin", "t": db.now()})


def _require_admin(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    token = authorization[7:]
    try:
        data = serializer.loads(token, max_age=60 * 60 * 12)  # 12 小时
    except BadSignature:
        raise HTTPException(401, "登录已过期，请重新登录")
    if data.get("role") != "admin":
        raise HTTPException(403, "无权访问")
    return True


class AdminLogin(BaseModel):
    password: str


@app.post("/api/sume/admin/login")
def admin_login(body: AdminLogin):
    if body.password != ADMIN_PASSWORD:
        time.sleep(0.6)  # 减缓暴力尝试
        raise HTTPException(401, "管理口令错误")
    return {"ok": True, "token": _make_token()}


@app.get("/api/sume/admin/verify")
def admin_verify(_: bool = Header(False), authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    return {"ok": True}


# ══════════════════════════════════════════════
#  学员端
# ══════════════════════════════════════════════

class StudentLogin(BaseModel):
    phone: str


@app.post("/api/sume/login")
def student_login(body: StudentLogin):
    """手机号白名单校验"""
    phone = db.normalize_phone(body.phone)
    if not phone:
        raise HTTPException(400, "请输入正确的 11 位手机号")
    rec = db.wl_find(phone)
    if not rec:
        raise HTTPException(403, "未找到您的报名记录，请联系思格老师开通")
    if rec.get("status") == "banned":
        raise HTTPException(403, "该账号已停用，请联系思格老师")
    db.wl_touch_login(phone)
    rv = db.rv_get(phone)
    return {
        "ok": True,
        "phone": phone,
        "name": rec.get("name") or "",
        "has_resume": bool(rv),
        "status": (rv or {}).get("status", "none"),
        "progress": (rv or {}).get("progress", 0),
    }


class SaveBody(BaseModel):
    phone: str
    data: dict
    photos: dict = {}
    status: str = "draft"


@app.post("/api/sume/save")
def save_resume(body: SaveBody):
    phone = db.normalize_phone(body.phone)
    rec = db.wl_find(phone)
    if not rec or rec.get("status") == "banned":
        raise HTTPException(403, "无权保存")
    progress = calc_progress(body.data)
    r = db.rv_save(phone, body.data, body.photos, progress, body.status)

    notified = None
    if body.status == "submitted":
        notified = notify.notify_submission(phone, rec.get("name") or "", body.data, r["id"])
    return {"ok": True, "progress": progress, "status": r["status"],
            "notified": bool(notified and notified.get("sent")) if notified else None}


@app.get("/api/sume/load")
def load_resume(phone: str):
    phone = db.normalize_phone(phone)
    rec = db.wl_find(phone)
    if not rec:
        raise HTTPException(403, "无权访问")
    rv = db.rv_get(phone)
    if not rv:
        return {"ok": True, "data": {}, "photos": {}, "status": "none", "progress": 0}
    return {
        "ok": True,
        "data": json.loads(rv["data"] or "{}"),
        "photos": json.loads(rv["photos"] or "{}"),
        "status": rv["status"],
        "progress": rv["progress"],
        "updated_at": rv["updated_at"],
    }


@app.get("/api/sume/schema")
def get_schema():
    """表单结构（前端渲染用）"""
    return {"modules": MODULES}


@app.post("/api/sume/upload")
async def upload_file(phone: str = Form(...), kind: str = Form(...), file: UploadFile = File(...)):
    phone = db.normalize_phone(phone)
    rec = db.wl_find(phone)
    if not rec:
        raise HTTPException(403, "无权上传")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMG:
        raise HTTPException(400, f"仅支持图片格式：{', '.join(sorted(ALLOWED_IMG))}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"文件不能超过 {MAX_UPLOAD_MB}MB")

    safe_kind = "".join(ch for ch in kind if ch.isalnum() or ch in "_-") or "file"
    fname = f"{phone}_{safe_kind}_{db.now()}{ext}"
    dest = PHOTO_DIR / fname
    dest.write_bytes(content)

    rv = db.rv_get(phone)
    photos = json.loads(rv["photos"] or "{}") if rv else {}
    photos[safe_kind] = str(dest)
    data = json.loads(rv["data"] or "{}") if rv else {}
    db.rv_save(phone, data, photos, rv["progress"] if rv else 0,
               rv["status"] if rv else "draft")

    return {"ok": True, "kind": safe_kind, "url": f"/api/sume/photo/{fname}", "name": file.filename}


@app.get("/api/sume/photo/{fname}")
def get_photo(fname: str):
    safe = Path(fname).name
    p = PHOTO_DIR / safe
    if not p.exists():
        raise HTTPException(404, "图片不存在")
    return FileResponse(str(p))


# ══════════════════════════════════════════════
#  管理端 · 名单
# ══════════════════════════════════════════════

@app.get("/api/sume/admin/stats")
def admin_stats(authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    s = db.wl_stats()
    s["notify_pending"] = sum(1 for n in db.notify_list(500) if not n["sent"])
    return s


@app.get("/api/sume/admin/whitelist")
def admin_wl_list(keyword: str = "", authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    return {"items": db.wl_list(keyword)}


class WlAdd(BaseModel):
    phone: str
    name: str = ""
    remark: str = ""


@app.post("/api/sume/admin/whitelist/add")
def admin_wl_add(body: WlAdd, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    phone = db.normalize_phone(body.phone)
    if not phone:
        raise HTTPException(400, "手机号格式不正确（需 11 位，1 开头）")
    if not db.wl_add(phone, body.name, body.remark):
        raise HTTPException(400, "该手机号已在名单中")
    return {"ok": True, "phone": phone}


@app.post("/api/sume/admin/whitelist/import")
async def admin_wl_import(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    """导入 Excel/CSV：第1列手机号，第2列姓名（可选），第3列备注（可选）"""
    _require_admin(authorization)
    content = await file.read()
    rows = []
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv") or name.endswith(".txt"):
            text = content.decode("utf-8-sig", errors="ignore")
            for line in text.splitlines():
                if not line.strip():
                    continue
                parts = [x.strip().strip('"') for x in line.replace("\t", ",").split(",")]
                rows.append(parts)
        else:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            ws = wb.active
            for r in ws.iter_rows(values_only=True):
                if r and any(x is not None and str(x).strip() for x in r):
                    rows.append([("" if x is None else str(x)) for x in r])
    except Exception as e:
        raise HTTPException(400, f"文件解析失败：{e}")

    if not rows:
        raise HTTPException(400, "文件中没有数据")

    # 跳过表头
    head = "".join(str(x) for x in rows[0])
    if ("手机" in head) or ("电话" in head) or ("姓名" in head and "手机" in head):
        rows = rows[1:]
    if not rows:
        raise HTTPException(400, "文件中没有数据（仅检测到表头）")

    res = db.wl_bulk_add(rows)
    return {"ok": True, **res, "total_rows": len(rows)}


@app.post("/api/sume/admin/whitelist/delete")
def admin_wl_delete(body: dict, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    phone = body.get("phone", "")
    if not db.wl_delete(phone):
        raise HTTPException(404, "未找到该手机号")
    return {"ok": True}


@app.post("/api/sume/admin/whitelist/status")
def admin_wl_status(body: dict, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    phone, status = body.get("phone", ""), body.get("status", "active")
    if status not in ("active", "banned"):
        raise HTTPException(400, "状态不合法")
    if not db.wl_set_status(phone, status):
        raise HTTPException(404, "未找到该手机号")
    return {"ok": True}


@app.get("/api/sume/admin/whitelist/export")
def admin_wl_export(authorization: Optional[str] = Header(None)):
    """导出未填名单（便于催缴）"""
    _require_admin(authorization)
    items = db.wl_list()
    wb = Workbook()
    ws = wb.active
    ws.title = "学员名单"
    ws.append(["手机号", "姓名", "备注", "状态", "填写状态", "进度%", "最后填写时间"])
    for it in items:
        st = it.get("r_status")
        st_label = {"submitted": "已提交", "draft": "填写中"}.get(
            st, "未开始" if not st else st)
        if st != "submitted" and (it.get("r_progress") or 0) == 0:
            st_label = "未开始"
        ws.append([
            it.get("phone"), it.get("name"), it.get("remark"),
            "正常" if it.get("status") == "active" else "已停用",
            st_label,
            it.get("r_progress") or 0,
            time.strftime("%Y-%m-%d %H:%M", time.localtime(it["r_updated"])) if it.get("r_updated") else "",
        ])
    for col, w in zip("ABCDEFG", (14, 12, 20, 10, 12, 10, 18)):
        ws.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"学员名单_{time.strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_cdn_header(fn))


# ══════════════════════════════════════════════
#  管理端 · 简历
# ══════════════════════════════════════════════

@app.get("/api/sume/admin/resumes")
def admin_rv_list(keyword: str = "", status: str = "",
                  authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    items = db.rv_list(keyword, status)
    for it in items:
        it.pop("data", None)
        it.pop("photos", None)
    return {"items": items}


@app.get("/api/sume/admin/resume/{rid}")
def admin_rv_detail(rid: int, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    rv = db.rv_get_by_id(rid)
    if not rv:
        raise HTTPException(404, "简历不存在")
    photos = json.loads(rv.get("photos") or "{}")
    rv["photos"] = {k: f"/api/sume/photo/{Path(v).name}" for k, v in photos.items()}
    rv["data"] = json.loads(rv.get("data") or "{}")
    return rv


@app.get("/api/sume/admin/export/{rid}")
def admin_export_one(rid: int, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    rv = db.rv_get_by_id(rid)
    if not rv:
        raise HTTPException(404, "简历不存在")
    data = json.loads(rv.get("data") or "{}")
    photos = json.loads(rv.get("photos") or "{}")
    basic = data.get("basic") or {}
    # 老数据可能没存 phone（schema 后期才改 readonly 注入），导出时兜底回填登录手机号
    if not (basic.get("phone") or "").strip():
        basic["phone"] = rv.get("phone") or ""
        data["basic"] = basic
    name = basic.get("name") or rv.get("wl_name") or rv.get("phone") or "简历"
    path = export_resume(data, photos, f"{name}_简历")
    return FileResponse(str(path), filename=path.name)


@app.get("/api/sume/admin/export-all")
def admin_export_all(authorization: Optional[str] = Header(None)):
    """批量导出：所有已提交简历打包 zip"""
    _require_admin(authorization)
    items = db.rv_list(status="submitted")
    if not items:
        raise HTTPException(404, "暂无已提交的简历")
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for it in items:
            full = db.rv_get_by_id(it["id"])
            data = json.loads(full.get("data") or "{}")
            photos = json.loads(full.get("photos") or "{}")
            basic = data.get("basic") or {}
            if not (basic.get("phone") or "").strip():
                basic["phone"] = full.get("phone") or ""
                data["basic"] = basic
            name = basic.get("name") or full.get("wl_name") or full["phone"]
            try:
                p = export_resume(data, photos, f"{name}_简历")
                zf.write(str(p), f"{name}_{full['phone']}.docx")
                count += 1
            except Exception as e:
                zf.writestr(f"{name}_{full['phone']}_导出失败.txt", str(e))
    buf.seek(0)
    fn = f"全部简历_{time.strftime('%Y%m%d_%H%M')}.zip"
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={**_cdn_header(fn), "X-Export-Count": str(count)})


@app.get("/api/sume/admin/export-excel")
def admin_export_excel(authorization: Optional[str] = Header(None)):
    """导出全部简历为 Excel 汇总表（一人一行）"""
    _require_admin(authorization)
    items = [db.rv_get_by_id(i["id"]) for i in db.rv_list()]
    wb = Workbook()
    ws = wb.active
    ws.title = "简历汇总"
    ws.append(["手机号", "姓名", "性别", "政治面貌", "学校", "专业", "GPA", "排名",
               "应聘单位/岗位", "首选考试城市", "状态", "进度%", "提交时间"])
    for full in items:
        d = json.loads(full.get("data") or "{}")
        b = d.get("basic") or {}
        edu = (d.get("education") or {}).get("rows") or [{}]
        e0 = edu[0] if edu else {}
        it_ = d.get("intention") or {}
        ws.append([
            full["phone"], b.get("name", ""), b.get("gender", ""), b.get("political", ""),
            e0.get("school", ""), e0.get("major", ""), e0.get("gpa", ""), e0.get("rank", ""),
            it_.get("target", ""), it_.get("exam_city", ""),
            "已提交" if full["status"] == "submitted" else "草稿",
            full.get("progress", 0),
            time.strftime("%Y-%m-%d %H:%M", time.localtime(full["submitted_at"])) if full.get("submitted_at") else "",
        ])
    for col, w in zip("ABCDEFGHIJKLM", (14, 12, 8, 12, 22, 18, 10, 10, 26, 14, 10, 10, 18)):
        ws.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"简历汇总_{time.strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_cdn_header(fn))


@app.post("/api/sume/admin/resume/delete")
def admin_rv_delete(body: dict, authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    rid = int(body.get("id", 0))
    if not db.rv_delete(rid):
        raise HTTPException(404, "简历不存在")
    return {"ok": True}


# ══════════════════════════════════════════════
#  管理端 · 通知记录
# ══════════════════════════════════════════════

@app.get("/api/sume/admin/notifications")
def admin_notify_list(authorization: Optional[str] = Header(None)):
    _require_admin(authorization)
    rows = db.notify_list(200)
    for r in rows:
        try:
            r["payload"] = json.loads(r["payload"] or "{}")
        except Exception:
            r["payload"] = {}
    return {"items": rows, "notify_email": NOTIFY_EMAIL}


# ══════════════════════════════════════════════
#  静态页面
# ══════════════════════════════════════════════

def _page(name: str) -> HTMLResponse:
    p = FRONTEND_DIR / name
    if not p.exists():
        return HTMLResponse(f"<h1>页面缺失：{name}</h1>", status_code=500)
    return HTMLResponse(p.read_text(encoding="utf-8"))


@app.get("/", response_class=HTMLResponse)
@app.get("/sume", response_class=HTMLResponse)
@app.get("/sume/", response_class=HTMLResponse)
def page_student():
    return _page("index.html")


@app.get("/sume/admin", response_class=HTMLResponse)
@app.get("/sume/admin/", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
def page_admin():
    return _page("admin.html")


@app.get("/sume/guide", response_class=HTMLResponse)
def page_guide():
    return _page("guide.html")


@app.get("/health")
def health():
    return {"ok": True, "ts": db.now()}
