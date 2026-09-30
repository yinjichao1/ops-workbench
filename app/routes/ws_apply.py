"""网申模拟系统 API —— 网申模拟工具的公开提交通道 + 管理端查询。

- POST /api/public/apply/submit   考生网申档案提交（公开、免认证，复用 nginx /api/public/ 白名单）
- GET  /api/apply/list            档案列表，分页+搜索（需认证，Basic Auth 之后）
- GET  /api/apply/detail/{id}     完整档案 + 多行明细（需认证）
- GET  /api/apply/export          导出 CSV（需认证）
- DELETE /api/apply/{id}          删除档案及对应线索摘要（需认证，用于清理测试数据）

存储：
- ws_archives       完整档案 JSON 快照 + 摘要列（附件 base64 剥离、证件照保留）
- ws_archive_items  多行明细子表（教育经历/家庭成员等逐行）
- leads             同步写一条摘要线索（source="网申模拟"），失败不影响档案保存
"""
import json
import csv
import io
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session as SqlSession

from ..models import get_db, WsArchive, WsArchiveItem, Lead

router = APIRouter()

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
MAX_ARCHIVE_JSON = 2 * 1024 * 1024        # 落库 JSON 上限 2MB（附件 base64 已剥离）
SECTION_KEYS = [
    "education", "family", "language", "computer", "certificate",
    "practice", "paper", "research", "award", "attachment",
]
LEVEL_SHORT = {
    "博士研究生毕业": "博士", "硕士研究生毕业": "硕士",
    "大学本科毕业": "本科", "大学专科毕业": "大专",
    "博士研究生": "博士", "硕士研究生": "硕士",
    "大学本科": "本科", "大学专科": "大专",
    "本科": "本科", "专科": "大专", "硕士": "硕士", "博士": "博士",
}
SOURCE_LEADS = "网申模拟"

# ── 简易内存限流（同 IP 10 分钟最多 5 次，与 match 工具同款） ──
_RATE = {}
_WINDOW = timedelta(minutes=10)
_MAX = 5


def _rate_ok(ip: str) -> bool:
    now = datetime.now()
    hits = [t for t in _RATE.get(ip, []) if now - t < _WINDOW]
    if len(hits) >= _MAX:
        _RATE[ip] = hits
        return False
    hits.append(now)
    _RATE[ip] = hits
    if len(_RATE) > 5000:
        for k in [k for k, v in _RATE.items() if not v or now - v[-1] > _WINDOW]:
            _RATE.pop(k, None)
    return True


def _client_ip(request: Request) -> str:
    """取真实 IP：nginx 反代场景优先 X-Forwarded-For 首段。"""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()[:45]
    return (request.client.host if request.client else "")[:45]


def _clean_archive(archive: dict) -> dict:
    """落库前清洗：附件剥离 base64 内容（保留元信息），防请求体/存储膨胀。"""
    a = dict(archive or {})
    atts = a.get("attachment")
    if isinstance(atts, list):
        cleaned = []
        for row in atts:
            if isinstance(row, dict):
                r = dict(row)
                if r.get("file"):
                    r["file"] = ""          # 附件内容不入库，只留名称/类型/大小
                cleaned.append(r)
            else:
                cleaned.append(row)
        a["attachment"] = cleaned
    return a


def _derive_summary(archive: dict, fallback: dict) -> dict:
    """从档案提取摘要：优先教育经历最高记录，缺失时回退前端 summary。"""
    edu = archive.get("education") if isinstance(archive.get("education"), list) else []
    top = edu[0] if edu and isinstance(edu[0], dict) else {}
    level_raw = (top.get("level") or fallback.get("level") or "").strip()
    return {
        "name": (fallback.get("name") or "").strip()[:50],
        "phone": (fallback.get("phone") or "").strip()[:20],
        "email": (fallback.get("email") or "").strip()[:100],
        "school": (top.get("school") or fallback.get("school") or "").strip()[:100],
        "major": (top.get("major") or fallback.get("major") or "").strip()[:100],
        "level": level_raw[:20],
        "grad_date": (fallback.get("gradDate") or "").strip()[:20],
    }


class ApplySubmitIn(BaseModel):
    summary: dict = {}
    archive: dict = {}
    # 投放渠道代号（前端从入口链接 ?ch= 读出来带过来的），空串 = 未标注
    platform: str = ""


def _int0(v) -> int:
    """容错取整：None/脏值一律 0，超范围截断。"""
    try:
        return max(0, min(1000, int(v)))
    except (TypeError, ValueError):
        return 0


@router.post("/public/apply/submit")
def submit_apply(body: ApplySubmitIn, request: Request,
                 db: SqlSession = Depends(get_db)):
    """网申档案提交。始终返回 HTTP 200，业务结果在 ok 字段。"""
    ip = _client_ip(request)
    if not _rate_ok(ip):
        return {"ok": False, "error": "提交过于频繁，请稍后再试"}

    archive = _clean_archive(body.archive if isinstance(body.archive, dict) else {})
    s = _derive_summary(archive, body.summary if isinstance(body.summary, dict) else {})
    if not (s["name"] and s["phone"]):
        return {"ok": False, "error": "缺少姓名或手机号，无法提交"}
    if not PHONE_RE.match(s["phone"]):
        return {"ok": False, "error": "手机号格式不正确"}
    stats = {
        "score": _int0(body.summary.get("score")),
        "complete": _int0(body.summary.get("complete")),
        "hard": _int0(body.summary.get("hard")),
        "risk": _int0(body.summary.get("risk")),
        "tip": _int0(body.summary.get("tip")),
    }

    try:
        archive_json = json.dumps(archive, ensure_ascii=False)
    except (TypeError, ValueError):
        return {"ok": False, "error": "档案数据格式有误"}
    if len(archive_json.encode("utf-8")) > MAX_ARCHIVE_JSON:
        return {"ok": False, "error": "档案数据过大，请减小上传附件后重试"}

    plat = (body.platform or "").strip().lower()[:20]

    # 同手机号当日重复提交 → 更新（避免重复线索），渠道以首次为准
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    exist = (
        db.query(WsArchive)
        .filter(WsArchive.phone == s["phone"], WsArchive.created_at >= today_start)
        .first()
    )
    if exist:
        exist.name, exist.email = s["name"], s["email"]
        exist.school, exist.major, exist.level = s["school"], s["major"], s["level"]
        exist.grad_date = s["grad_date"]
        exist.archive_json = archive_json
        exist.ip = ip
        exist.score = stats["score"]
        exist.complete_pct = stats["complete"]
        exist.hard_count = stats["hard"]
        exist.risk_count = stats["risk"]
        exist.tip_count = stats["tip"]
        if not exist.platform and plat:
            exist.platform = plat
        db.commit()
        _save_items(db, exist.id, archive)
        _upsert_lead_summary(db, s)
        return {"ok": True, "id": exist.id, "dup": True}

    rec = WsArchive(
        archive_json=archive_json, ip=ip, platform=plat,
        score=stats["score"], complete_pct=stats["complete"],
        hard_count=stats["hard"], risk_count=stats["risk"], tip_count=stats["tip"],
        **s,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    _save_items(db, rec.id, archive)
    _upsert_lead_summary(db, s)
    return {"ok": True, "id": rec.id}


def _save_items(db: SqlSession, archive_id: int, archive: dict):
    """多行明细落子表（同档案重复提交时先清后写）。"""
    try:
        db.query(WsArchiveItem).filter(WsArchiveItem.archive_id == archive_id).delete()
        for sec in SECTION_KEYS:
            rows = archive.get(sec)
            if not isinstance(rows, list):
                continue
            for i, row in enumerate(rows[:50]):   # 单模块上限 50 行，防滥用
                db.add(WsArchiveItem(
                    archive_id=archive_id, section=sec, sort=i,
                    data_json=json.dumps(row, ensure_ascii=False)[:8000],
                ))
        db.commit()
    except Exception:
        db.rollback()    # 明细失败不影响主档案


def _upsert_lead_summary(db: SqlSession, s: dict):
    """写线索摘要到 leads 表（source=网申模拟）。任何失败都不影响档案保存。

    注意：leads 表每周 CSV 按周替换，摘要行可能随当周替换被清掉——
    完整档案永远以 ws_archives 为准，这里只求进入每周线索流。
    """
    try:
        grade = LEVEL_SHORT.get(s["level"], s["level"][:10])
        exist = (
            db.query(Lead)
            .filter(Lead.phone == s["phone"], Lead.source == SOURCE_LEADS,
                    Lead.date == date.today())
            .first()
        )
        if exist:
            exist.name, exist.school, exist.grade = s["name"], s["school"], grade
            db.commit()
            return
        db.add(Lead(
            name=s["name"], phone=s["phone"], school=s["school"], grade=grade,
            date=date.today(), source=SOURCE_LEADS, status="未跟进",
            note=f"网申模拟提交 学历:{s['level'] or '未填'} 毕业时间:{s['grad_date'] or '未填'}",
        ))
        db.commit()
    except Exception:
        db.rollback()


@router.get("/apply/list")
def apply_list(page: int = 1, size: int = 50, keyword: str = "",
               platform: str = "", db: SqlSession = Depends(get_db)):
    """档案列表（需认证）。分页 + 姓名/手机/学校/专业模糊搜索。"""
    page = max(1, page)
    size = min(max(1, size), 500)
    q = db.query(WsArchive)
    kw = (keyword or "").strip()
    if kw:
        like = "%%%s%%" % kw
        q = q.filter(WsArchive.name.like(like) | WsArchive.phone.like(like)
                     | WsArchive.school.like(like) | WsArchive.major.like(like))
    plat = (platform or "").strip().lower()
    if plat:
        q = q.filter(WsArchive.platform == plat)
    total = q.count()
    rows = q.order_by(WsArchive.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "ok": True, "total": total, "page": page, "size": size,
        "items": [{
            "id": r.id, "name": r.name, "phone": r.phone, "email": r.email,
            "school": r.school, "major": r.major, "level": r.level,
            "grad_date": r.grad_date, "score": r.score,
            "hard": r.hard_count, "risk": r.risk_count, "tip": r.tip_count,
            "complete": r.complete_pct, "platform": r.platform or "",
            "time": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        } for r in rows],
    }


@router.get("/apply/detail/{archive_id}")
def apply_detail(archive_id: int, db: SqlSession = Depends(get_db)):
    """完整档案 + 多行明细（需认证）。"""
    rec = db.query(WsArchive).filter(WsArchive.id == archive_id).first()
    if not rec:
        return {"ok": False, "error": "档案不存在"}
    try:
        archive = json.loads(rec.archive_json or "{}")
    except ValueError:
        archive = {}
    items = {}
    for it in (db.query(WsArchiveItem)
               .filter(WsArchiveItem.archive_id == archive_id)
               .order_by(WsArchiveItem.section, WsArchiveItem.sort).all()):
        try:
            payload = json.loads(it.data_json or "{}")
        except ValueError:
            payload = {}
        items.setdefault(it.section, []).append(payload)
    return {"ok": True, "summary": {
        "id": rec.id, "name": rec.name, "phone": rec.phone, "email": rec.email,
        "school": rec.school, "major": rec.major, "level": rec.level,
        "grad_date": rec.grad_date, "score": rec.score,
        "hard": rec.hard_count, "risk": rec.risk_count, "tip": rec.tip_count,
        "complete": rec.complete_pct, "platform": rec.platform or "",
        "ip": rec.ip, "time": rec.created_at.strftime("%Y-%m-%d %H:%M") if rec.created_at else "",
    }, "archive": archive, "items": items}


@router.get("/apply/export")
def apply_export(keyword: str = "", platform: str = "",
                 db: SqlSession = Depends(get_db)):
    """导出 CSV（UTF-8 BOM，Excel 可直接打开）。"""
    q = db.query(WsArchive)
    kw = (keyword or "").strip()
    if kw:
        like = "%%%s%%" % kw
        q = q.filter(WsArchive.name.like(like) | WsArchive.phone.like(like)
                     | WsArchive.school.like(like) | WsArchive.major.like(like))
    plat = (platform or "").strip().lower()
    if plat:
        q = q.filter(WsArchive.platform == plat)
    rows = q.order_by(WsArchive.created_at.desc()).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["姓名", "手机号", "邮箱", "学校", "专业", "学历", "毕业时间",
                "体检评分", "硬伤", "风险", "提示", "完整度%", "渠道", "提交时间"])
    for r in rows:
        w.writerow([r.name, r.phone, r.email, r.school, r.major, r.level, r.grad_date,
                    r.score, r.hard_count, r.risk_count, r.tip_count, r.complete_pct,
                    r.platform or "未标注",
                    r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""])
    data = "\ufeff" + buf.getvalue()
    return Response(
        content=data.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=ws_apply.csv"},
    )


@router.delete("/apply/{archive_id}")
def apply_delete(archive_id: int, db: SqlSession = Depends(get_db)):
    """删除档案 + 明细 + 对应线索摘要行（需认证，用于清理测试数据）。"""
    rec = db.query(WsArchive).filter(WsArchive.id == archive_id).first()
    if not rec:
        return {"ok": False, "error": "档案不存在"}
    db.query(WsArchiveItem).filter(WsArchiveItem.archive_id == archive_id).delete()
    # 只删本模块写入的摘要行（source=网申模拟 且 姓名+手机号 双重匹配），不碰其他线索
    deleted_leads = (
        db.query(Lead)
        .filter(Lead.source == SOURCE_LEADS, Lead.phone == rec.phone, Lead.name == rec.name)
        .delete()
    )
    db.delete(rec)
    db.commit()
    return {"ok": True, "id": archive_id, "leads_removed": deleted_leads}
