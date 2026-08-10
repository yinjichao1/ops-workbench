"""Monthly KPI target API."""

from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session as SqlSession
from sqlalchemy.exc import IntegrityError
from ..models import get_db, MonthlyTarget

router = APIRouter()


class TargetIn(BaseModel):
    year: int
    month: int
    platform: str
    target_new_followers: int = 0
    target_plays_reads: int = 0
    target_publish_count: int = 0
    target_engagement: int = 0


@router.get("/targets")
def get_targets(year: int = Query(...), month: int = Query(...), db: SqlSession = Depends(get_db)):
    rows = db.query(MonthlyTarget).filter(MonthlyTarget.year == year, MonthlyTarget.month == month).all()
    return {
        "data": [
            {
                "platform": r.platform,
                "target_new_followers": r.target_new_followers,
                "target_plays_reads": r.target_plays_reads,
                "target_publish_count": r.target_publish_count,
                "target_engagement": r.target_engagement,
            }
            for r in rows
        ]
    }


@router.post("/targets")
def upsert_target(body: TargetIn, db: SqlSession = Depends(get_db)):
    existing = (
        db.query(MonthlyTarget)
        .filter(
            MonthlyTarget.year == body.year,
            MonthlyTarget.month == body.month,
            MonthlyTarget.platform == body.platform,
        )
        .first()
    )
    if existing:
        existing.target_new_followers = body.target_new_followers
        existing.target_plays_reads = body.target_plays_reads
        existing.target_publish_count = body.target_publish_count
        existing.target_engagement = body.target_engagement
        existing.updated_at = date.today()
    else:
        record = MonthlyTarget(**body.model_dump(), updated_at=date.today())
        db.add(record)
    db.commit()
    return {"ok": True}


@router.post("/targets/bulk")
def upsert_targets_bulk(body: list[TargetIn], db: SqlSession = Depends(get_db)):
    for item in body:
        existing = (
            db.query(MonthlyTarget)
            .filter(
                MonthlyTarget.year == item.year,
                MonthlyTarget.month == item.month,
                MonthlyTarget.platform == item.platform,
            )
            .first()
        )
        if existing:
            existing.target_new_followers = item.target_new_followers
            existing.target_plays_reads = item.target_plays_reads
            existing.target_publish_count = item.target_publish_count
            existing.target_engagement = item.target_engagement
            existing.updated_at = date.today()
        else:
            record = MonthlyTarget(**item.model_dump(), updated_at=date.today())
            db.add(record)
    db.commit()
    return {"ok": True, "count": len(body)}