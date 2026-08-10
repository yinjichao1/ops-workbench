"""Data entry API — weekly entry + CSV import."""

import csv
import io
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..models import get_db
from ..models.platform_metrics import PlatformDailyMetrics

router = APIRouter()


def parse_week(w: str) -> date:
    """Parse '2026-W32' -> Monday date, or 'YYYY-MM-DD' -> date."""
    if "-W" in w:
        y, wk = w.split("-W")
        return date.fromisocalendar(int(y), int(wk), 1)
    return date.fromisoformat(w)


def week_to_str(d: date) -> str:
    """Convert date to 'YYYY-Www' format."""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def week_to_cn(d: date) -> str:
    """Convert date to Chinese format: '2026年8月第2周'."""
    # Find first Monday of the month
    first_day = d.replace(day=1)
    first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)
    if first_monday.month != d.month:
        first_monday = d.replace(day=1)
        while first_monday.weekday() != 0:
            first_monday += timedelta(days=1)
    if d < first_monday:
        # Belongs to previous month's week
        prev_month = first_day - timedelta(days=1)
        prev_first = prev_month.replace(day=1)
        prev_first_mon = prev_first + timedelta(days=(7 - prev_first.weekday()) % 7)
        if prev_first_mon.month != prev_first.month:
            prev_first_mon = prev_first
            while prev_first_mon.weekday() != 0:
                prev_first_mon += timedelta(days=1)
        week_num = ((d - prev_first_mon).days // 7) + 1
        return f"{prev_first_mon.year}年{prev_first_mon.month}月第{week_num}周"
    week_num = ((d - first_monday).days // 7) + 1
    return f"{d.year}年{d.month}月第{week_num}周"


# ---------- Pydantic schemas ----------
class DailyMetricIn(BaseModel):
    week: str  # "2026-W32" or "YYYY-MM-DD"
    platform: str
    account: str = ""
    followers: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    new_followers: int = 0
    publish_count: int = 0
    plays: int = 0
    completion_rate: float = 0.0
    ad_spend: float = 0.0
    reads: int = 0
    in_views: int = 0
    conversion_count: int = 0
    note_reads: int = 0
    bookmarks: int = 0
    engagement_rate: float = 0.0
    is_viral: int = 0


class BatchMetricsIn(BaseModel):
    records: list[DailyMetricIn]


# ---------- Manual entry ----------
@router.post("/metrics")
def create_metric(body: DailyMetricIn, db: Session = Depends(get_db)):
    """单条录入周数据。week 格式如 '2026-W32'。"""
    d = parse_week(body.week)
    existing = (
        db.query(PlatformDailyMetrics)
        .filter(
            PlatformDailyMetrics.date == d,
            PlatformDailyMetrics.platform == body.platform,
            PlatformDailyMetrics.account == (body.account or ""),
        )
        .first()
    )
    if existing:
        for k, v in body.model_dump(exclude={"week", "platform", "account"}).items():
            setattr(existing, k, v)
        db.commit()
        return {"ok": True, "updated": True, "id": existing.id, "week": week_to_str(d)}

    record = PlatformDailyMetrics(date=d, platform=body.platform, account=body.account or "")
    for k, v in body.model_dump(exclude={"week", "platform", "account"}).items():
        setattr(record, k, v)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "updated": False, "id": record.id, "week": week_to_str(d)}


@router.post("/metrics/batch")
def create_metrics_batch(body: BatchMetricsIn, db: Session = Depends(get_db)):
    """批量录入周数据。"""
    count = 0
    for item in body.records:
        d = parse_week(item.week)
        existing = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.date == d,
                PlatformDailyMetrics.platform == item.platform,
            )
            .first()
        )
        if existing:
            for k, v in item.model_dump(exclude={"week", "platform"}).items():
                setattr(existing, k, v)
        else:
            record = PlatformDailyMetrics(date=d, platform=item.platform)
            for k, v in item.model_dump(exclude={"week", "platform"}).items():
                setattr(record, k, v)
            db.add(record)
        count += 1
    db.commit()
    return {"ok": True, "count": count}


# ---------- CSV import ----------
@router.post("/metrics/import-csv")
def import_metrics_csv(
    file: UploadFile = File(...),
    platform: str = Query(...),
    db: Session = Depends(get_db),
):
    """从 CSV 导入日报数据。"""
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    count = 0

    field_map = {
        "周": "week", "粉丝数": "followers", "点赞": "likes",
        "评论": "comments", "分享": "shares", "新增粉丝": "new_followers",
        "发布数": "publish_count", "播放量": "plays", "完播率": "completion_rate",
        "投流消耗": "ad_spend", "阅读量": "reads", "在看": "in_views",
        "转化数": "conversion_count", "笔记阅读量": "note_reads",
        "收藏": "bookmarks", "互动率": "engagement_rate", "爆款": "is_viral",
    }

    for row in reader:
        data = {"platform": platform}
        for cn, en in field_map.items():
            val = row.get(cn, "").strip()
            if not val:
                continue
            if en == "week":
                try:
                    data[en] = val
                except ValueError:
                    continue
            elif en in ("completion_rate", "engagement_rate", "ad_spend"):
                data[en] = float(val) if val else 0.0
            elif en == "is_viral":
                data[en] = 1 if val.lower() in ("1", "true", "yes", "是") else 0
            else:
                data[en] = int(float(val)) if val else 0

        if "week" not in data:
            continue

        d = parse_week(data["week"])
        existing = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.date == d,
                PlatformDailyMetrics.platform == platform,
            )
            .first()
        )
        if existing:
            for k, v in data.items():
                if k not in ("week", "platform"):
                    setattr(existing, k, v)
        else:
            try:
                db.add(PlatformDailyMetrics(**data))
            except Exception:
                continue
        count += 1

    db.commit()
    return {"ok": True, "imported": count}


# ---------- Query ----------
@router.get("/metrics")
def list_metrics(
    platform: Optional[str] = None,
    account: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(90, le=365),
    db: Session = Depends(get_db),
):
    """查询周数据。"""
    q = db.query(PlatformDailyMetrics)
    if platform:
        q = q.filter(PlatformDailyMetrics.platform == platform)
    if account:
        q = q.filter(PlatformDailyMetrics.account == account)
    if start_date:
        q = q.filter(PlatformDailyMetrics.date >= parse_week(start_date))
    if end_date:
        q = q.filter(PlatformDailyMetrics.date <= parse_week(end_date))
    rows = q.order_by(PlatformDailyMetrics.date.desc()).limit(limit).all()

    return {
        "data": [
            {
                "id": r.id,
                "week": week_to_str(r.date),
                "week_cn": week_to_cn(r.date),
                "date": str(r.date),
                "platform": r.platform,
                "account": r.account or "",
                "followers": r.followers,
                "likes": r.likes,
                "comments": r.comments,
                "shares": r.shares,
                "new_followers": r.new_followers,
                "publish_count": r.publish_count,
                "plays": r.plays,
                "completion_rate": r.completion_rate,
                "ad_spend": r.ad_spend,
                "reads": r.reads,
                "in_views": r.in_views,
                "conversion_count": r.conversion_count,
                "note_reads": r.note_reads,
                "bookmarks": r.bookmarks,
                "engagement_rate": r.engagement_rate,
                "is_viral": r.is_viral,
            }
            for r in rows
        ]
    }


# ---------- Account Config ----------
ACCOUNTS = {
    "抖音": ["思格电网", "安哥", "范校", "东北电气人都认"],
    "视频号": ["思格电网", "范校"],
    "公众号": ["思格电网"],
    "小红书": ["小格", "学姐"],
}


@router.get("/accounts")
def list_accounts(platform: Optional[str] = None):
    """返回各平台账号列表。"""
    if platform:
        return {"accounts": ACCOUNTS.get(platform, ["主号"])}
    return {"accounts": ACCOUNTS}
