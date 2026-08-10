"""Leads analysis API."""

from datetime import date, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session as SqlSession
from ..models import get_db, Lead

router = APIRouter()


class LeadIn(BaseModel):
    name: str = ""
    gender: str = ""
    phone: str = ""
    year: int = 2026
    month: int = 8
    date: str = ""
    status: str = ""
    source: str = ""
    validity: str = ""
    intent: int = 0
    school: str = ""
    grade: str = ""
    contact_count: int = 0
    owner: str = ""
    note: str = ""


@router.post("/leads/bulk")
def create_lead(body: LeadIn, db: SqlSession = Depends(get_db)):
    lead = Lead(
        name=body.name, gender=body.gender, phone=body.phone,
        year=body.year, month=body.month,
        date=date.fromisoformat(body.date) if body.date else date.today(),
        status=body.status, source=body.source, validity=body.validity,
        intent=body.intent, school=body.school, grade=body.grade,
        contact_count=body.contact_count, owner=body.owner, note=body.note,
    )
    db.add(lead)
    db.commit()
    return {"ok": True, "id": lead.id}


@router.get("/leads/summary")
def leads_summary(
    week_val: str = Query("", description="YYYY-MM-DD"),
    db: SqlSession = Depends(get_db),
):
    today = date.today()
    if week_val:
        start = date.fromisoformat(week_val)
    else:
        start = today - timedelta(days=(today.weekday() + 7) % 7 + 7)
    end = start + timedelta(days=6)

    rows = db.query(Lead).filter(Lead.date >= start, Lead.date <= end).all()
    total = len(rows)
    valid = sum(1 for r in rows if r.validity == "有效")
    invalid = sum(1 for r in rows if r.validity == "无效")
    pending = sum(1 for r in rows if r.validity == "待定")

    by_source = defaultdict(int)
    by_status = defaultdict(int)
    by_region = defaultdict(int)
    by_day = defaultdict(int)
    intent_dist = defaultdict(int)
    for r in rows:
        by_source[r.source or "其他"] += 1
        by_status[r.status or "未知"] += 1
        by_region[r.owner or "未知"] += 1
        intent_dist[r.intent or 0] += 1
        by_day[r.date.isoformat()] += 1

    contact_sum = sum(r.contact_count or 0 for r in rows)
    high_contact = sum(1 for r in rows if (r.contact_count or 0) >= 3)

    return {
        "week": f"{start} ~ {end}",
        "total": total,
        "valid": valid, "invalid": invalid, "pending": pending,
        "valid_rate": round(valid / total * 100, 1) if total else 0,
        "contact_total": contact_sum,
        "contact_avg": round(contact_sum / total, 1) if total else 0,
        "high_contact": high_contact,
        "by_source": [{"name": k, "count": v, "pct": round(v / total * 100, 1) if total else 0}
                      for k, v in sorted(by_source.items(), key=lambda x: -x[1])],
        "by_status": [{"name": k, "count": v} for k, v in by_status.items()],
        "by_region": [{"name": k, "count": v} for k, v in sorted(by_region.items(), key=lambda x: -x[1])],
        "by_day": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
        "intent_distribution": [{"level": k, "count": v} for k, v in sorted(intent_dist.items())],
    }
