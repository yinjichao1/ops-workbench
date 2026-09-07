"""公开表单收集 API。

- POST /api/public/forms/submit  落地页门控提交（公开、免认证，nginx 白名单放行）
- GET  /api/forms/overview       按来源项目分组的总览（今日/累计/各项目计数）
- GET  /api/forms/list           收集记录明细，可按来源项目 page 过滤
- POST /api/forms/delete         删除单条（误录/垃圾数据）
- GET  /api/forms/export         导出 CSV（UTF-8 BOM），可按来源项目 page 过滤

存储到独立表 form_submissions，与 leads 的每周 CSV 替换互不影响。
不同落地页/活动共用同一提交通道，但用 page 字段区分项目，
管理端按项目分类查看/导出，避免线索混在一起。
"""

import csv
import io
import re

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session as SqlSession

from ..models import get_db, FormSubmission

router = APIRouter()

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


class FormSubmitIn(BaseModel):
    name: str = ""
    phone: str = ""
    school: str = ""
    major: str = ""
    page: str = ""


class FormDeleteIn(BaseModel):
    id: int


@router.post("/public/forms/submit")
def submit_form(body: FormSubmitIn, db: SqlSession = Depends(get_db)):
    name = (body.name or "").strip()
    phone = (body.phone or "").strip()
    school = (body.school or "").strip()
    major = (body.major or "").strip()

    if not (name and phone and school and major):
        return {"ok": False, "error": "请完整填写 姓名 / 手机 / 学校 / 专业"}
    if len(name) > 50 or len(school) > 100 or len(major) > 50:
        return {"ok": False, "error": "字段长度超出限制"}
    if not PHONE_RE.match(phone):
        return {"ok": False, "error": "手机号格式不正确"}

    rec = FormSubmission(
        name=name[:50],
        phone=phone[:20],
        school=school[:100],
        major=major[:50],
        page=(body.page or "")[:30],
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"ok": True, "id": rec.id}


def _today_start():
    return func.date(FormSubmission.created_at) == func.current_date()


@router.get("/forms/overview")
def forms_overview(db: SqlSession = Depends(get_db)):
    """按来源项目分组的总览：供管理页 Tab 徽标与顶部统计。"""
    total = db.query(func.count(FormSubmission.id)).scalar() or 0
    today_n = (
        db.query(func.count(FormSubmission.id))
        .filter(_today_start())
        .scalar()
        or 0
    )
    # 按 page 分组计数（今日/累计），空 page 归为 "__none__"，前端映射为「未标注」
    today_flag = case(
        (func.date(FormSubmission.created_at) == func.current_date(), 1),
        else_=0,
    )
    rows = (
        db.query(
            FormSubmission.page,
            func.count(FormSubmission.id),
            func.sum(today_flag),
        )
        .group_by(FormSubmission.page)
        .order_by(func.count(FormSubmission.id).desc())
        .all()
    )
    pages = []
    for page_code, cnt, today_cnt in rows:
        pages.append(
            {
                "page": page_code or "",
                "total": int(cnt or 0),
                "today": int(today_cnt or 0),
            }
        )
    return {"ok": True, "total": total, "today": today_n, "pages": pages}


@router.get("/forms/list")
def list_forms(
    page: str = Query("", description="来源项目代号，空或 all 表示全部"),
    limit: int = Query(500, le=2000),
    db: SqlSession = Depends(get_db),
):
    q = db.query(FormSubmission)
    if page and page != "all":
        q = q.filter(FormSubmission.page == page[:30])

    total = q.count()
    today_n = q.filter(_today_start()).count()
    rows = q.order_by(FormSubmission.id.desc()).limit(limit).all()
    return {
        "ok": True,
        "page": page or "all",
        "total": total,
        "today": today_n,
        "data": [
            {
                "id": r.id,
                "name": r.name or "",
                "phone": r.phone or "",
                "school": r.school or "",
                "major": r.major or "",
                "page": r.page or "",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ],
    }


@router.post("/forms/delete")
def delete_form(body: FormDeleteIn, db: SqlSession = Depends(get_db)):
    rec = db.query(FormSubmission).filter(FormSubmission.id == body.id).first()
    if not rec:
        return {"ok": False, "error": "记录不存在"}
    db.delete(rec)
    db.commit()
    return {"ok": True}


@router.get("/forms/export")
def export_forms(
    page: str = Query("", description="来源项目代号，空或 all 表示全部"),
    db: SqlSession = Depends(get_db),
):
    q = db.query(FormSubmission)
    if page and page != "all":
        q = q.filter(FormSubmission.page == page[:30])

    rows = q.order_by(FormSubmission.id.asc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "专业", "来源项目"])
    for r in rows:
        w.writerow([
            r.id,
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            r.name or "",
            r.phone or "",
            r.school or "",
            r.major or "",
            r.page or "",
        ])
    content = buf.getvalue().encode("utf-8-sig")
    fname = f"forms_{page or 'all'}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
