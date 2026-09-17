"""统一线索汇总 API —— 供「线索收集管理」页在同一张表里查看全部收集渠道。

背景：
- form_submissions（公开表单/落地页）、match_leads（岗位匹配工具）、exam_signups（919 模考报名）
  是三张独立表，字段各异，故不强合并，而是在展示层做统一视图。
- 管理页按「渠道」分 Tab：渠道 = 表单收集项目（page） + 匹配工具（match） + 模考（exam）。

⚠️ **两个"渠道"不是一回事**（2026-09-17 新增第二维，务必分清）：
| 概念 | 字段 | 取值 | 含义 |
|---|---|---|---|
| **收集入口** | `channel` | `match` / `exam` / `timeline28` … | 线索从哪个**页面/工具**收集来的 |
| **投放渠道** | `platform` | `douyin` / `shipinhao` / `gzh` / `xhs` … | 线索从哪个**平台**来的（入口链接 `?ch=` 参数） |
口语上都被叫"渠道"，但在代码与 UI 里必须分开命名。投放渠道目前**只有匹配工具（match）有**，
其余入口的历史与现有记录一律为「未标注」。

端点：
- GET /api/collect/overview   统一总览：各渠道今日/累计计数 + 匹配工具的投放渠道分布
- GET /api/collect/list       统一明细：按渠道过滤、可按投放渠道过滤，统一字段结构
- GET /api/collect/export     统一导出 CSV（UTF-8 BOM），按渠道/投放渠道过滤
- GET /api/collect/delete     删除单条（需带 source 以定位所属表）

与 /api/forms/* 并存，后者保持向后兼容（原表单页仍可直接使用）。
"""

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session as SqlSession

from ..models import get_db, ExamSignup, FormSubmission, MatchLead
# 投放渠道的中文名与规范化只维护一份（在 match_routes 里），此处直接复用
from .match_routes import platform_label, norm_platform

router = APIRouter()

# 固定渠道代号
MATCH_CHANNEL = "match"
MATCH_LABEL = "匹配工具线索收集"
EXAM_CHANNEL = "exam"
EXAM_LABEL = "模考线索收集"

# 表单项目代号 → 中文名（新项目上线时在此登记，前端 PAGE_LABELS 保持同步）
PAGE_LABELS = {
    "timeline28": "28届备考时间线",
    MATCH_CHANNEL: MATCH_LABEL,
    EXAM_CHANNEL: EXAM_LABEL,
}


def channel_label(code):
    """渠道代号转中文名，未登记的原样返回。"""
    if not code:
        return "未标注"
    return PAGE_LABELS.get(code, code)


class DeleteIn(BaseModel):
    id: int
    source: str = "form"          # form | match | exam


def _today_flag(col):
    return case((func.date(col) == func.current_date(), 1), else_=0)


@router.get("/collect/overview")
def collect_overview(db: SqlSession = Depends(get_db)):
    """统一总览：表单各项目 + 匹配工具，分别给出今日/累计计数。"""
    # ── 表单收集（按 page 分组） ──
    form_total = db.query(func.count(FormSubmission.id)).scalar() or 0
    form_today = (
        db.query(func.count(FormSubmission.id))
        .filter(func.date(FormSubmission.created_at) == func.current_date())
        .scalar()
        or 0
    )
    form_rows = (
        db.query(
            FormSubmission.page,
            func.count(FormSubmission.id),
            func.sum(_today_flag(FormSubmission.created_at)),
        )
        .group_by(FormSubmission.page)
        .order_by(func.count(FormSubmission.id).desc())
        .all()
    )

    channels = []
    for page_code, cnt, today_cnt in form_rows:
        channels.append(
            {
                "channel": page_code or "",
                "kind": "form",
                "label": channel_label(page_code),
                "total": int(cnt or 0),
                "today": int(today_cnt or 0),
            }
        )

    # ── 匹配工具 ──
    match_total = db.query(func.count(MatchLead.id)).scalar() or 0
    match_today = (
        db.query(func.count(MatchLead.id))
        .filter(func.date(MatchLead.created_at) == func.current_date())
        .scalar()
        or 0
    )
    # 投放渠道分布（仅匹配工具有这一维；空串 = 历史数据或未带 ?ch= 的直接访问）
    match_plat_rows = (
        db.query(
            MatchLead.platform,
            func.count(MatchLead.id),
            func.sum(_today_flag(MatchLead.created_at)),
        )
        .group_by(MatchLead.platform)
        .order_by(func.count(MatchLead.id).desc())
        .all()
    )
    match_platforms = [
        {"code": c or "", "label": platform_label(c),
         "total": int(n or 0), "today": int(t or 0)}
        for c, n, t in match_plat_rows
    ]
    channels.append(
        {
            "channel": MATCH_CHANNEL,
            "kind": "match",
            "label": MATCH_LABEL,
            "total": int(match_total),
            "today": int(match_today),
            "platforms": match_platforms,
        }
    )

    # ── 919 模考报名（exam_signups，与模考服务共库） ──
    exam_total = db.query(func.count(ExamSignup.id)).scalar() or 0
    exam_today = (
        db.query(func.count(ExamSignup.id))
        .filter(func.date(ExamSignup.created_at) == func.current_date())
        .scalar()
        or 0
    )
    channels.append(
        {
            "channel": EXAM_CHANNEL,
            "kind": "exam",
            "label": EXAM_LABEL,
            "total": int(exam_total),
            "today": int(exam_today),
        }
    )

    grand_total = int(form_total) + int(match_total) + int(exam_total)
    grand_today = int(form_today) + int(match_today) + int(exam_today)

    return {
        "ok": True,
        "form_total": int(form_total),
        "form_today": int(form_today),
        "match_total": int(match_total),
        "match_today": int(match_today),
        "exam_total": int(exam_total),
        "exam_today": int(exam_today),
        "total": grand_total,
        "today": grand_today,
        "channels": channels,
    }


def _form_rows(db, channel):
    q = db.query(FormSubmission)
    if channel and channel != "all":
        q = q.filter(FormSubmission.page == channel[:30])
    out = []
    for r in q.order_by(FormSubmission.id.desc()).limit(2000).all():
        out.append(
            {
                "id": r.id,
                "source": "form",
                "channel": r.page or "",
                "channel_label": channel_label(r.page),
                # 投放渠道只存在于匹配工具；表单来源统一"未标注"（保持统一结构，前端不必做兼容判断）
                "platform": "",
                "platform_label": "未标注",
                "name": r.name or "",
                "phone": r.phone or "",
                "school": r.school or "",
                "major": r.major or "",
                "degree": "",
                "year": "",
                "province": "",
                "grade": "",
                "score": None,
                "duration": 0,
                # 匹配工具专有字段，表单来源统一留空
                "match_total": None,
                "match_exact": None,
                "match_family": None,
                "match_review": None,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
        )
    return out


def _match_rows(db, keyword="", platform=""):
    """匹配工具渠道明细。platform 支持标准/<自定义>代号，特殊值 `none` = 只看未标注。"""
    q = db.query(MatchLead)
    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            MatchLead.name.like(like)
            | MatchLead.phone.like(like)
            | MatchLead.school.like(like)
            | MatchLead.major.like(like)
        )
    plat = (platform or "").strip()
    if plat == "none":                    # 约定：none = 未标注（历史数据 / 未带 ?ch= 的直接访问）
        q = q.filter((MatchLead.platform == "") | (MatchLead.platform.is_(None)))
    elif plat:
        q = q.filter(MatchLead.platform == norm_platform(plat))
    out = []
    for r in q.order_by(MatchLead.id.desc()).limit(2000).all():
        out.append(
            {
                "id": r.id,
                "source": "match",
                "channel": MATCH_CHANNEL,
                "channel_label": MATCH_LABEL,
                "platform": r.platform or "",
                "platform_label": platform_label(r.platform),
                "name": r.name or "",
                "phone": r.phone or "",
                "school": r.school or "",
                "major": r.major or "",
                "degree": r.degree_label or "",
                "year": r.grad_year or "",
                "province": r.province or "",
                "grade": "",
                "score": None,
                "duration": 0,
                "match_total": r.match_total,
                "match_exact": r.match_exact,
                "match_family": r.match_family,
                "match_review": r.match_review,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
        )
    return out


def _exam_rows(db):
    """919 模考报名记录（exam_signups）。"""
    out = []
    for r in db.query(ExamSignup).order_by(ExamSignup.id.desc()).limit(2000).all():
        out.append(
            {
                "id": r.id,
                "source": "exam",
                "channel": EXAM_CHANNEL,
                "channel_label": EXAM_LABEL,
                "platform": "",
                "platform_label": "未标注",
                "name": r.name or "",
                "phone": r.phone or "",
                "school": r.school or "",
                "major": "",
                "degree": "",
                "year": "",
                "province": "",
                "grade": r.grade or "",
                "score": r.score,
                "duration": r.duration or 0,
                "match_total": None,
                "match_exact": None,
                "match_family": None,
                "match_review": None,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
        )
    return out


@router.get("/collect/list")
def collect_list(
    channel: str = Query("all", description="渠道：all / 表单项目代号 / match / exam"),
    keyword: str = Query("", description="关键词，仅作用于匹配工具渠道"),
    platform: str = Query("", description="投放渠道：代号 / 中文名 / none（未标注）；空=全部"),
    db: SqlSession = Depends(get_db),
):
    """统一明细。channel=all 时合并三渠道；match/exam 返回各自表；其余按表单项目过滤。

    platform 只对匹配工具渠道有意义（其余入口没有这一维），在 all 视图里同样生效。
    """
    if channel == MATCH_CHANNEL:
        rows = _match_rows(db, keyword, platform)
    elif channel == EXAM_CHANNEL:
        rows = _exam_rows(db)
    elif channel and channel != "all":
        rows = _form_rows(db, channel)
    else:
        rows = _form_rows(db, "all") + _match_rows(db, keyword, platform) + _exam_rows(db)
        if (platform or "").strip():
            # 同导出：投放渠道只存在于匹配工具，按它筛选时只保留匹配工具行
            rows = [r for r in rows if r.get("source") == "match"]
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    # 汇总统计
    today = sum(1 for r in rows if r["created_at"].startswith(_today_str()))
    return {"ok": True, "channel": channel or "all", "total": len(rows), "today": today, "data": rows}


def _today_str():
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


@router.get("/collect/export")
def collect_export(
    channel: str = Query("all", description="渠道：all / 表单项目代号 / match / exam"),
    platform: str = Query("", description="投放渠道：代号 / 中文名 / none（未标注）；空=全部"),
    db: SqlSession = Depends(get_db),
):
    """统一导出。各渠道按自身字段结构导出（含渠道列与投放渠道列）。"""
    buf = io.StringIO()
    w = csv.writer(buf)
    plat = (platform or "").strip()
    # 文件名带上投放渠道，避免运营连着导多份时互相覆盖
    plat_suffix = ("_" + (plat if plat == "none" else norm_platform(plat))) if plat else ""

    if channel == EXAM_CHANNEL:
        w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "年级", "得分", "用时(秒)", "渠道"])
        for r in _exam_rows(db):
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], r["grade"],
                 r["score"], r["duration"], r["channel_label"]]
            )
        fname = "collect_exam.csv"
    elif channel == MATCH_CHANNEL:
        w.writerow(
            ["ID", "提交时间", "姓名", "手机", "学校", "专业", "学历", "毕业年份",
             "意向地区", "投放渠道", "匹配岗位数", "完全符合", "基本符合", "需人工确认"]
        )
        for r in _match_rows(db, "", plat):
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], r["major"],
                 r["degree"], r["year"], r["province"], r["platform_label"], r["match_total"],
                 r["match_exact"], r["match_family"], r["match_review"]]
            )
        fname = f"collect_match{plat_suffix}.csv"
    elif channel and channel != "all":
        w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "专业", "来源项目"])
        for r in _form_rows(db, channel):
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], r["major"],
                 r["channel_label"]]
            )
        fname = f"collect_{channel}.csv"
    else:
        # 全部：合并三渠道，用统一列（来源渠道 + 投放渠道 区分来源）
        rows = _form_rows(db, "all") + _match_rows(db, "", plat) + _exam_rows(db)
        if plat:
            # 投放渠道这一维只存在于匹配工具 —— 按它筛选时其余入口没有可比维度，
            # 全留着会得到"筛了抖音却混进表单线索"的假结果，故只保留匹配工具行。
            rows = [r for r in rows if r.get("source") == "match"]
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "专业/年级",
                    "来源渠道", "投放渠道", "来源表"])
        for r in rows:
            extra = r["major"] or r["grade"]
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], extra,
                 r["channel_label"], r.get("platform_label", "未标注"), r["source"]]
            )
        fname = f"collect_all{plat_suffix}.csv"
    content = buf.getvalue().encode("utf-8-sig")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/collect/delete")
def collect_delete(body: DeleteIn, db: SqlSession = Depends(get_db)):
    """删除单条。必须带 source，以定位记录所属的表。"""
    if body.source == "match":
        rec = db.query(MatchLead).filter(MatchLead.id == body.id).first()
    elif body.source == "exam":
        rec = db.query(ExamSignup).filter(ExamSignup.id == body.id).first()
    else:
        rec = db.query(FormSubmission).filter(FormSubmission.id == body.id).first()
    if not rec:
        return {"ok": False, "error": "记录不存在"}
    db.delete(rec)
    db.commit()
    return {"ok": True}
