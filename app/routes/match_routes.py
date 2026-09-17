"""岗位匹配工具留资 API —— /match/ 工具的公开提交通道。

- POST /api/public/match/submit   考生留资提交（公开、免认证，复用 nginx /api/public/ 白名单）
- GET  /api/match/overview        匹配工具线索总览（需认证，供管理端）
- GET  /api/match/list            线索明细，支持分页（需认证）
- GET  /api/match/export          导出 CSV（需认证）

存储到独立表 match_leads，与 leads / form_submissions 完全隔离。
"""
import csv
import io
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session as SqlSession

from ..models import get_db, MatchLead

router = APIRouter()

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
DEGREE_LABEL = {2: "大专", 3: "本科", 4: "硕士", 5: "博士"}

# ── 投放渠道（platform）─────────────────────────────────────────────
# ⚠️ 命名约定：本模块的 platform = **投放平台**（线索从哪个平台来）；
#    collect_routes 里的 channel = **收集入口**（form / match / exam）。
#    两者都常被口语称作"渠道"，但语义不同，代码里不要混用。
#
# 各投放渠道发专属链接：https://sigedianwang.cn/match/?ch=douyin
# 运营手打链接时写中文也能认（下面 ALIAS 兜底），避免"发错链接导致渠道全空"。
PLATFORM_LABELS = {
    "douyin": "抖音",
    "shipinhao": "微信视频号",
    "gzh": "微信公众号",
    "xhs": "小红书",
    "pengyouquan": "朋友圈",
    "qun": "社群/微信群",
    "ditui": "线下地推",
    "zhuanjie": "转介绍",
    "ziran": "自然流量",
}
PLATFORM_ALIAS = {
    "抖音": "douyin",
    "视频号": "shipinhao", "微信视频号": "shipinhao",
    "公众号": "gzh", "微信公众号": "gzh",
    "小红书": "xhs",
    "朋友圈": "pengyouquan",
    "社群": "qun", "微信群": "qun", "社群/微信群": "qun",
    "地推": "ditui", "线下地推": "ditui",
    "转介绍": "zhuanjie", "老带新": "zhuanjie",
    "自然流量": "ziran",
}
_PLATFORM_BAD = re.compile(r"[^a-z0-9_-]")


def norm_platform(v: str) -> str:
    """规范化投放渠道代号。

    - 中文 / 中文别名 → 标准代号（`抖音` → `douyin`）
    - 其余只保留 `[a-z0-9_-]`，截断 20 字符
    - **未知代号不丢弃**（允许临时活动用 `?ch=919` 这类自定义值，便于回溯），
      但必须过字符集与长度，防止脏数据进库
    """
    s = (v or "").strip()
    if not s:
        return ""
    if s in PLATFORM_ALIAS:                    # 中文原名
        return PLATFORM_ALIAS[s]
    low = s.lower()
    if low in PLATFORM_ALIAS:                  # 大小写变体
        return PLATFORM_ALIAS[low]
    if low in PLATFORM_LABELS:                 # 已是标准代号
        return low
    return _PLATFORM_BAD.sub("", low)[:20]


def platform_label(code: str) -> str:
    """代号 → 中文名，未登记的原样返回（便于发现自定义渠道），空值 → 未标注。"""
    if not code:
        return "未标注"
    return PLATFORM_LABELS.get(code, code)


# ── 简易内存限流（同 IP 10 分钟最多 5 次） ──
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
    if len(_RATE) > 5000:                     # 防止内存无限增长
        for k in [k for k, v in _RATE.items() if not v or now - v[-1] > _WINDOW]:
            _RATE.pop(k, None)
    return True


class MatchSubmitIn(BaseModel):
    name: str = ""
    phone: str = ""
    school: str = ""
    major: str = ""
    degree_level: int = 0
    year: str = ""
    province: str = ""
    group: str = ""
    season: str = ""
    # 投放渠道代号（前端从入口链接 ?ch= 读出来带过来的），空串 = 未标注
    platform: str = ""
    # 容错：前端可能尚未拿到匹配结果就提交，传 null/缺省一律按 0 处理
    match_total: Optional[int] = 0
    match_exact: Optional[int] = 0
    match_family: Optional[int] = 0
    match_review: Optional[int] = 0


@router.post("/public/match/submit")
def submit_match_lead(body: MatchSubmitIn, db: SqlSession = Depends(get_db),
                      request_ip: str = Query(default="", alias="_ip")):
    """考生留资提交。始终返回 HTTP 200，业务结果在 ok 字段。"""
    name = (body.name or "").strip()
    phone = (body.phone or "").strip()
    school = (body.school or "").strip()
    major = (body.major or "").strip()

    if not (name and phone and school and major):
        return {"ok": False, "error": "请填写 姓名 / 手机号 / 学校 / 专业"}
    if not PHONE_RE.match(phone):
        return {"ok": False, "error": "手机号格式不正确"}
    if len(name) > 50 or len(school) > 100 or len(major) > 100:
        return {"ok": False, "error": "字段长度超出限制"}

    plat = norm_platform(body.platform)

    # 同手机号当日重复提交 -> 更新，避免重复线索
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    exist = (
        db.query(MatchLead)
        .filter(MatchLead.phone == phone, MatchLead.created_at >= today_start)
        .first()
    )
    if exist:
        exist.school = school[:100]
        exist.major = major[:100]
        exist.degree_level = body.degree_level
        exist.grad_year = (body.year or "")[:10]
        exist.province = (body.province or "")[:20]
        exist.match_total = body.match_total
        # 渠道以**首次**为准（首次落地最接近真实来源）；
        # 但如果首次没带上（老链接/直接访问），这次带了就补上，避免渠道永远空着。
        if not exist.platform and plat:
            exist.platform = plat
        db.commit()
        return {"ok": True, "id": exist.id, "dup": True}

    rec = MatchLead(
        name=name[:50],
        phone=phone[:20],
        school=school[:100],
        major=major[:100],
        degree_level=body.degree_level,
        degree_label=DEGREE_LABEL.get(body.degree_level, ""),
        grad_year=(body.year or "")[:10],
        province=(body.province or "")[:20],
        group=(body.group or "")[:50],
        season=(body.season or "")[:50],
        match_total=body.match_total,
        match_exact=body.match_exact,
        match_family=body.match_family,
        match_review=body.match_review,
        source="match-tool",
        platform=plat,
        ip=request_ip[:45],
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"ok": True, "id": rec.id}


@router.get("/match/overview")
def match_overview(db: SqlSession = Depends(get_db)):
    """线索总览：今日 / 累计 / 按学历 / 按月 / 热门专业与地区。"""
    today = func.date(MatchLead.created_at) == func.current_date()
    total = db.query(func.count(MatchLead.id)).scalar() or 0
    today_n = db.query(func.count(MatchLead.id)).filter(today).scalar() or 0

    by_deg = [
        {"label": lb or "未知", "count": c}
        for lb, c in db.query(MatchLead.degree_label, func.count(MatchLead.id))
        .group_by(MatchLead.degree_label).order_by(func.count(MatchLead.id).desc()).all()
    ]
    by_prov = [
        {"label": p or "不限", "count": c}
        for p, c in db.query(MatchLead.province, func.count(MatchLead.id))
        .group_by(MatchLead.province).order_by(func.count(MatchLead.id).desc()).limit(10).all()
    ]
    top_major = [
        {"label": m, "count": c}
        for m, c in db.query(MatchLead.major, func.count(MatchLead.id))
        .group_by(MatchLead.major).order_by(func.count(MatchLead.id).desc()).limit(10).all()
    ]
    # 投放渠道分布（空串归到"未标注"，即历史数据 / 直接访问未带 ?ch= 的线索）
    by_platform = [
        {"code": c or "", "label": platform_label(c), "count": n}
        for c, n in db.query(MatchLead.platform, func.count(MatchLead.id))
        .group_by(MatchLead.platform).order_by(func.count(MatchLead.id).desc()).all()
    ]
    return {
        "ok": True, "total": total, "today": today_n,
        "by_degree": by_deg, "by_province": by_prov, "top_major": top_major,
        "by_platform": by_platform,
    }


@router.get("/match/list")
def match_list(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=500),
               keyword: str = "", platform: str = "",
               db: SqlSession = Depends(get_db)):
    """线索明细，支持按姓名/手机/学校/专业模糊搜索，可按投放渠道过滤。"""
    q = db.query(MatchLead)
    kw = (keyword or "").strip()
    if kw:
        like = "%%%s%%" % kw
        q = q.filter(
            MatchLead.name.like(like) | MatchLead.phone.like(like)
            | MatchLead.school.like(like) | MatchLead.major.like(like)
        )
    plat = norm_platform(platform) if platform else ""
    if plat:
        q = q.filter(MatchLead.platform == plat)
    total = q.count()
    rows = q.order_by(MatchLead.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "ok": True, "total": total, "page": page, "size": size,
        "items": [{
            "id": r.id, "name": r.name, "phone": r.phone, "school": r.school,
            "major": r.major, "degree": r.degree_label, "year": r.grad_year,
            "province": r.province, "match_total": r.match_total,
            "platform": r.platform or "", "platform_label": platform_label(r.platform),
            "time": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        } for r in rows],
    }


@router.get("/match/export")
def match_export(keyword: str = "", platform: str = "", db: SqlSession = Depends(get_db)):
    """导出 CSV（UTF-8 BOM，Excel 可直接打开）。可按投放渠道过滤。"""
    q = db.query(MatchLead)
    kw = (keyword or "").strip()
    if kw:
        like = "%%%s%%" % kw
        q = q.filter(MatchLead.name.like(like) | MatchLead.phone.like(like)
                     | MatchLead.school.like(like) | MatchLead.major.like(like))
    plat = norm_platform(platform) if platform else ""
    if plat:
        q = q.filter(MatchLead.platform == plat)
    rows = q.order_by(MatchLead.created_at.desc()).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["姓名", "手机号", "学校", "专业", "学历", "毕业年份",
                "意向地区", "投放渠道", "匹配岗位数", "招聘集团", "届次", "提交时间"])
    for r in rows:
        w.writerow([r.name, r.phone, r.school, r.major, r.degree_label, r.grad_year,
                    r.province, platform_label(r.platform), r.match_total, r.group, r.season,
                    r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""])
    data = "\ufeff" + buf.getvalue()
    return Response(
        content=data.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=match_leads.csv"},
    )
