"""Topic ideas / 选题库 API."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..models import get_db
from ..models.content import TopicIdea, ContentCalendar
from datetime import date

router = APIRouter()


class TopicIn(BaseModel):
    title: str
    source: str = "灵感"
    platforms: str = ""
    priority: str = "中"
    status: str = "待评估"
    creator: str = ""
    notes: str = ""


class TopicUpdateIn(BaseModel):
    title: Optional[str] = None
    source: Optional[str] = None
    platforms: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
def list_topics(
    status: Optional[str] = None,
    source: Optional[str] = None,
    platform: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """选题列表 — 支持搜索筛选。"""
    q = db.query(TopicIdea)
    if status:
        q = q.filter(TopicIdea.status == status)
    if source:
        q = q.filter(TopicIdea.source == source)
    if platform:
        q = q.filter(TopicIdea.platforms.contains(platform))
    if keyword:
        q = q.filter(TopicIdea.title.contains(keyword))

    total = q.count()
    rows = (
        q.order_by(TopicIdea.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "data": [
            {
                "id": r.id,
                "title": r.title,
                "source": r.source,
                "platforms": r.platforms,
                "priority": r.priority,
                "status": r.status,
                "creator": r.creator,
                "notes": r.notes,
                "created_at": str(r.created_at),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
    }


@router.post("")
def create_topic(body: TopicIn, db: Session = Depends(get_db)):
    """创建选题。"""
    record = TopicIdea(**body.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "id": record.id}


@router.put("/{topic_id}")
def update_topic(topic_id: int, body: TopicUpdateIn, db: Session = Depends(get_db)):
    """更新选题。"""
    record = db.query(TopicIdea).filter(TopicIdea.id == topic_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    record = db.query(TopicIdea).filter(TopicIdea.id == topic_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    db.delete(record)
    db.commit()
    return {"ok": True}


@router.post("/{topic_id}/to-calendar")
def topic_to_calendar(
    topic_id: int,
    scheduled_date: str = Query(...),
    platform: str = Query(...),
    assignee: str = Query(""),
    db: Session = Depends(get_db),
):
    """选题转排期 — 一键将选题转为排期条目。"""
    topic = db.query(TopicIdea).filter(TopicIdea.id == topic_id).first()
    if not topic:
        return {"ok": False, "error": "topic not found"}

    # Determine content type based on platform
    type_map = {"抖音": "短视频", "视频号": "短视频", "公众号": "长文章", "小红书": "笔记"}
    content_type = type_map.get(platform, "图文")

    entry = ContentCalendar(
        title=topic.title,
        platform=platform,
        content_type=content_type,
        scheduled_date=date.fromisoformat(scheduled_date),
        assignee=assignee,
        description=topic.notes or "",
        related_topic_id=topic_id,
        status="待策划",
    )
    db.add(entry)
    # Mark topic as adopted
    topic.status = "已采纳"
    db.commit()
    db.refresh(entry)
    return {"ok": True, "calendar_id": entry.id}
