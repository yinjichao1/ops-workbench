"""统一线索汇总 API —— 供「线索收集管理」页在同一张表里查看全部收集渠道。

背景：
- form_submissions（公开表单/落地页）、match_leads（岗位匹配工具）、exam_signups（919 模考报名）
  是三张独立表，字段各异，故不强合并，而是在展示层做统一视图。
- 管理页按「渠道」分 Tab：渠道 = 表单收集项目（page） + 匹配工具（match） + 模考（exam）。

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

from ..models import get_db, ExamSignup, FormSubmission, MatchLead

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
    channels.append(
        {
            "channel": MATCH_CHANNEL,
            "kind": "match",
            "label": MATCH_LABEL,
            "total": int(match_total),
            "today": int(match_today),
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
    db: SqlSession = Depends(get_db),
):
    """统一明细。channel=all 时合并三渠道；match/exam 返回各自表；其余按表单项目过滤。"""
    if channel == MATCH_CHANNEL:
        rows = _match_rows(db, keyword)
    elif channel == EXAM_CHANNEL:
        rows = _exam_rows(db)
    elif channel and channel != "all":
        rows = _form_rows(db, channel)
    else:
        rows = _form_rows(db, "all") + _match_rows(db, keyword) + _exam_rows(db)
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
    db: SqlSession = Depends(get_db),
):
    """统一导出。各渠道按自身字段结构导出（含渠道列）。"""
    buf = io.StringIO()
    w = csv.writer(buf)

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
             "意向地区", "匹配岗位数", "完全符合", "基本符合", "需人工确认", "渠道"]
        )
        for r in _match_rows(db):
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], r["major"],
                 r["degree"], r["year"], r["province"], r["match_total"], r["match_exact"],
                 r["match_family"], r["match_review"], r["channel_label"]]
            )
        fname = "collect_match.csv"
    elif channel and channel != "all":
        w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "专业", "来源项目"])
        for r in _form_rows(db, channel):
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], r["major"],
                 r["channel_label"]]
            )
        fname = f"collect_{channel}.csv"
    else:
        # 全部：合并三渠道，用统一列（渠道列区分来源）
        w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "专业/年级", "来源渠道", "来源表"])
        rows = _form_rows(db, "all") + _match_rows(db) + _exam_rows(db)
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        for r in rows:
            extra = r["major"] or r["grade"]
            w.writerow(
                [r["id"], r["created_at"], r["name"], r["phone"], r["school"], extra,
                 r["channel_label"], r["source"]]
            )
        fname = "collect_all.csv"
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
