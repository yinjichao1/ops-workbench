"""Content API — detail, calendar."""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..models import get_db
from ..models.content import ContentDetail, ContentCalendar

router = APIRouter()


# ---------- Content Detail ----------
class ContentIn(BaseModel):
    platform: str
    publish_date: str
    content_type: str
    title: str
    url: str = ""
    is_promoted: int = 0
    promote_amount: float = 0.0
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    bookmarks: int = 0
    completion_rate: float = 0.0
    reads: int = 0
    conversion_count: int = 0
    is_viral: int = 0
    author: str = ""
    notes: str = ""


class ContentUpdateIn(BaseModel):
    title: Optional[str] = None
    impressions: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    bookmarks: Optional[int] = None
    completion_rate: Optional[float] = None
    reads: Optional[int] = None
    conversion_count: Optional[int] = None
    is_viral: Optional[int] = None
    notes: Optional[str] = None


@router.get("/detail")
def list_content(
    platform: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    content_type: Optional[str] = None,
    is_viral: Optional[int] = None,
    author: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """查询内容明细列表。"""
    q = db.query(ContentDetail)
    if platform:
        q = q.filter(ContentDetail.platform == platform)
    if start_date:
        q = q.filter(ContentDetail.publish_date >= date.fromisoformat(start_date))
    if end_date:
        q = q.filter(ContentDetail.publish_date <= date.fromisoformat(end_date))
    if content_type:
        q = q.filter(ContentDetail.content_type == content_type)
    if is_viral is not None:
        q = q.filter(ContentDetail.is_viral == is_viral)
    if author:
        q = q.filter(ContentDetail.author == author)

    total = q.count()
    rows = q.order_by(ContentDetail.publish_date.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

    return {
        "data": [
            {c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"}
            | {"id": r.id, "publish_date": str(r.publish_date),
               "created_at": str(r.created_at) if r.created_at else None}
            for r in rows
        ],
        "total": total,
        "page": page,
    }


@router.post("/detail")
def create_content(body: ContentIn, db: Session = Depends(get_db)):
    """录入内容明细。"""
    record = ContentDetail(**body.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "id": record.id}


@router.put("/detail/{content_id}")
def update_content(content_id: int, body: ContentUpdateIn, db: Session = Depends(get_db)):
    """更新内容表现数据。"""
    record = db.query(ContentDetail).filter(ContentDetail.id == content_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/detail/{content_id}")
def delete_content(content_id: int, db: Session = Depends(get_db)):
    record = db.query(ContentDetail).filter(ContentDetail.id == content_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    db.delete(record)
    db.commit()
    return {"ok": True}


# ---------- Content Calendar ----------
class CalendarIn(BaseModel):
    title: str
    platform: str
    content_type: str
    status: str = "待策划"
    scheduled_date: str
    assignee: str = ""
    description: str = ""
    related_topic_id: Optional[int] = None


class CalendarUpdateIn(BaseModel):
    title: Optional[str] = None
    platform: Optional[str] = None
    content_type: Optional[str] = None
    status: Optional[str] = None
    scheduled_date: Optional[str] = None
    assignee: Optional[str] = None
    description: Optional[str] = None
    related_topic_id: Optional[int] = None


@router.get("/calendar")
def list_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """查询排期。默认排除「已发布」状态。"""
    q = db.query(ContentCalendar).filter(ContentCalendar.status != "已发布")
    if start_date:
        q = q.filter(ContentCalendar.scheduled_date >= date.fromisoformat(start_date))
    if end_date:
        q = q.filter(ContentCalendar.scheduled_date <= date.fromisoformat(end_date))
    if platform:
        q = q.filter(ContentCalendar.platform == platform)
    if status:
        q = q.filter(ContentCalendar.status == status)
    rows = q.order_by(ContentCalendar.scheduled_date.asc()).all()
    return {
        "data": [
            {
                "id": r.id,
                "title": r.title,
                "platform": r.platform,
                "content_type": r.content_type,
                "status": r.status,
                "scheduled_date": str(r.scheduled_date),
                "assignee": r.assignee,
                "description": r.description,
                "related_topic_id": r.related_topic_id,
            }
            for r in rows
        ]
    }


@router.post("/calendar")
def create_calendar_entry(body: CalendarIn, db: Session = Depends(get_db)):
    """创建排期条目。"""
    data = body.model_dump()
    data["scheduled_date"] = datetime.strptime(data["scheduled_date"], "%Y-%m-%d").date()
    record = ContentCalendar(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "id": record.id}


@router.put("/calendar/{entry_id}")
def update_calendar_entry(entry_id: int, body: CalendarUpdateIn, db: Session = Depends(get_db)):
    """更新排期状态等。"""
    record = db.query(ContentCalendar).filter(ContentCalendar.id == entry_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "scheduled_date" and v:
            v = date.fromisoformat(v)
        setattr(record, k, v)
    db.commit()

    # 如果状态变成"已发布"，检查关联的任务是否自动完成
    if body.status == "已发布" and record.related_content_id is None:
        from .tasks import _auto_complete_task  # noqa: F811
        _auto_complete_task(db, entry_id)

    return {"ok": True}


@router.delete("/calendar/{entry_id}")
def delete_calendar_entry(entry_id: int, db: Session = Depends(get_db)):
    """删除排期条目。"""
    record = db.query(ContentCalendar).filter(ContentCalendar.id == entry_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    db.delete(record)
    db.commit()
    return {"ok": True}
