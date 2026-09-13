"""统一线索汇总 API —— 供「线索收集管理」页在同一张表里查看全部收集渠道。

背景：
- form_submissions（公开表单/落地页）与 match_leads（岗位匹配工具）是两张独立表，
  前者表窄、后者多带匹配档位数据，故不强合并，而是在展示层做统一视图。
- 管理页按「渠道」分 Tab：渠道 = 表单收集项目（page） + 匹配工具（match）。

端点：
- GET /api/collect/overview   统一总览：各渠道今日/累计计数（供 Tab 徽标与顶部统计）
- GET /api/collect/list       统一明细：按渠道过滤，统一字段结构
- GET /api/collect/export     统一导出 CSV（UTF-8 BOM），按渠道过滤
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

from ..models import get_db, FormSubmission, MatchLead

router = APIRouter()

# 匹配工具的固定渠道代号
MATCH_CHANNEL = "match"
MATCH_LABEL = "岗位匹配工具"

# 表单项目代号 → 中文名（新项目上线时在此登记，前端 PAGE_LABELS 保持同步）
PAGE_LABELS = {
    "timeline28": "28届备考时间线",
    MATCH_CHANNEL: MATCH_LABEL,
}


def channel_label(code):
    """渠道代号转中文名，未登记的原样返回。"""
    if not code:
        return "未标注"
    return PAGE_LABELS.get(code, code)


class DeleteIn(BaseModel):
    id: int
    source: str = "form"          # form | match


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
    channels.append(
        {
            "channel": MATCH_CHANNEL,
            "kind": "match",
            "label": MATCH_LABEL,
            "total": int(match_total),
            "today": int(match_today),
        }
    )

    return {
        "ok": True,
        "form_total": int(form_total),
        "form_today": int(form_today),
        "match_total": int(match_total),
        "match_today": int(match_today),
        "total": int(form_total) + int(match_total),
        "today": int(form_today) + int(match_today),
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
                "name": r.name or "",
                "phone": r.phone or "",
                "school": r.school or "",
                "major": r.major or "",
                "degree": "",
                "year": "",
                "province": "",
                # 匹配工具专有字段，表单来源统一留空
                "match_total": None,
                "match_exact": None,
                "match_family": None,
                "match_review": None,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
        )
    return out


def _match_rows(db, keyword=""):
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
    out = []
    for r in q.order_by(MatchLead.id.desc()).limit(2000).all():
        out.append(
            {
                "id": r.id,
                "source": "match",
                "channel": MATCH_CHANNEL,
                "channel_label": MATCH_LABEL,
                "name": r.name or "",
                "phone": r.phone or "",
                "school": r.school or "",
                "major": r.major or "",
                "degree": r.degree_label or "",
                "year": r.grad_year or "",
                "province": r.province or "",
                "match_total": r.match_total,
                "match_exact": r.match_exact,
                "match_family": r.match_family,
                "match_review": r.match_review,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
        )
    return out


@router.get("/collect/list")
def collect_list(
    channel: str = Query("all", description="渠道：all / 表单项目代号 / match"),
    keyword: str = Query("", description="关键词，仅作用于匹配工具渠道"),
    db: SqlSession = Depends(get_db),
):
    """统一明细。channel=match 时返回匹配工具线索（含匹配档位），否则返回表单收集记录。"""
    if channel == MATCH_CHANNEL:
        rows = _match_rows(db, keyword)
    else:
        rows = _form_rows(db, channel)
    # 汇总统计
    today = sum(1 for r in rows if r["created_at"].startswith(_today_str()))
    return {"ok": True, "channel": channel or "all", "total": len(rows), "today": today, "data": rows}


def _today_str():
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


@router.get("/collect/export")
def collect_export(
    channel: str = Query("all", description="渠道：all / 表单项目代号 / match"),
    db: SqlSession = Depends(get_db),
):
    """统一导出。channel=match 时导出匹配工具线索（含匹配档位列）。"""
    buf = io.StringIO()
    w = csv.writer(buf)

    if channel == MATCH_CHANNEL:
        w.writerow(
            ["ID", "提交时间", "姓名", "手机", "学校", "专业", "学历", "毕业年份",
             "意向地区", "匹配岗位数", "完全符合", "基本符合", "需人工确认", "渠道"]
        )
        for r in _match_rows(db):
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], r["major"],
                 r["degree"], r["year"], r["province"], r["match_total"], r["match_exact"],
                 r["match_family"], r["match_review"], r["channel_label"]]
            )
        fname = "collect_match.csv"
    else:
        w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "专业", "来源项目"])
        for r in _form_rows(db, channel):
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], r["major"],
                 r["channel_label"]]
            )
        fname = f"collect_{channel or 'all'}.csv"
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
    else:
        rec = db.query(FormSubmission).filter(FormSubmission.id == body.id).first()
    if not rec:
        return {"ok": False, "error": "记录不存在"}
    db.delete(rec)
    db.commit()
    return {"ok": True}
