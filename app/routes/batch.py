"""Batch import endpoints for content/calendar/topics."""

from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as SqlSession
from ..models import get_db, ContentDetail, ContentCalendar, Task, TopicIdea

router = APIRouter()


class DetailBatchItem(BaseModel):
    platform: str = "抖音"
    content_type: str = "短视频"
    title: str = ""
    publish_date: str = ""
    url: str = ""
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    bookmarks: int = 0
    completion_rate: float = 0.0
    reads: int = 0
    is_viral: int = 0
    author: str = ""
    notes: str = ""


class CalendarBatchItem(BaseModel):
    title: str = ""
    platform: str = "抖音"
    content_type: str = "短视频"
    status: str = "待策划"
    scheduled_date: str = ""
    assignee: str = ""
    description: str = ""


class TopicBatchItem(BaseModel):
    title: str = ""
    platforms: str = ""
    status: str = "灵感"
    priority: str = "中"
    source: str = "灵感"
    creator: str = ""
    notes: str = ""


@router.post("/batch/detail")
def batch_create_detail(items: list[DetailBatchItem], db: SqlSession = Depends(get_db)):
    count = 0
    for item in items:
        try:
            d = ContentDetail(
                platform=item.platform,
                content_type=item.content_type,
                title=item.title,
                publish_date=datetime.strptime(item.publish_date, "%Y-%m-%d").date() if item.publish_date else None,
                url=item.url,
                impressions=item.impressions, likes=item.likes, comments=item.comments,
                shares=item.shares, bookmarks=item.bookmarks,
                completion_rate=item.completion_rate, reads=item.reads,
                is_viral=item.is_viral, author=item.author, notes=item.notes,
            )
            db.add(d)
            count += 1
        except Exception:
            pass
    db.commit()
    return {"ok": True, "count": count}


@router.post("/batch/calendar")
def batch_create_calendar(items: list[CalendarBatchItem], db: SqlSession = Depends(get_db)):
    count = 0
    for item in items:
        try:
            d = ContentCalendar(
                title=item.title,
                platform=item.platform,
                content_type=item.content_type,
                status=item.status,
                scheduled_date=datetime.strptime(item.scheduled_date, "%Y-%m-%d").date() if item.scheduled_date else None,
                assignee=item.assignee,
                description=item.description,
            )
            db.add(d)
            count += 1
        except Exception:
            pass
    db.commit()
    return {"ok": True, "count": count}


@router.post("/batch/topic")
def batch_create_topic(items: list[TopicBatchItem], db: SqlSession = Depends(get_db)):
    count = 0
    for item in items:
        try:
            d = TopicIdea(
                title=item.title,
                platforms=item.platforms,
                status=item.status,
                priority=item.priority,
                source=item.source,
                creator=item.creator,
                notes=item.notes,
            )
            db.add(d)
            count += 1
        except Exception:
            pass
    db.commit()
    return {"ok": True, "count": count}
