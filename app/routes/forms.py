"""公开表单收集 API。

- POST /api/public/forms/submit  落地页门控提交（公开、免认证，nginx 白名单放行）
- GET  /api/forms/list           收集记录（工作台内查看，位于 Basic Auth 之后）
- POST /api/forms/delete         删除单条（误录/垃圾数据）
- GET  /api/forms/export         导出 CSV（UTF-8 BOM，Excel 直接打开不乱码）

存储到独立表 form_submissions，与 leads 的每周 CSV 替换互不影响。
"""

import csv
import io
import re

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func
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


@router.get("/forms/list")
def list_forms(
    limit: int = Query(500, le=2000),
    db: SqlSession = Depends(get_db),
):
    rows = (
        db.query(FormSubmission)
        .order_by(FormSubmission.id.desc())
        .limit(limit)
        .all()
    )
    total = db.query(func.count(FormSubmission.id)).scalar() or 0
    today_n = (
        db.query(func.count(FormSubmission.id))
        .filter(func.date(FormSubmission.created_at) == func.current_date())
        .scalar()
        or 0
    )
    return {
        "ok": True,
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
def export_forms(db: SqlSession = Depends(get_db)):
    rows = (
        db.query(FormSubmission)
        .order_by(FormSubmission.id.asc())
        .all()
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "提交时间", "姓名", "手机", "学校", "专业", "来源页"])
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
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="form_submissions.csv"'
        },
    )
