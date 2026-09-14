"""Live streaming stats API — 直播场次手动录入与周/月汇总。"""

import re
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session as SqlSession
from ..models import get_db, LiveStream

router = APIRouter()

# 数值字段：前端 number 输入天然允许小数（如时长 81.8），后端统一四舍五入成整数，
# 避免 Pydantic int_from_float 直接 422 导致整条记录保存失败。
# 字段中文名用于报错提示。
NUM_FIELDS = {
    "duration_min": "时长（分钟）",
    "viewers": "观看人次",
    "peak_online": "峰值在线",
    "engagement": "互动量",
    "new_followers": "新增粉丝",
    "leads_count": "留资线索",
}


class LiveIn(BaseModel):
    live_date: str
    platform: str
    account: str = ""
    title: str = ""
    duration_min: int = 0
    viewers: int = 0
    peak_online: int = 0
    engagement: int = 0
    new_followers: int = 0
    leads_count: int = 0
    note: str = ""

    @field_validator(*NUM_FIELDS, mode="before")
    @classmethod
    def _lenient_int(cls, v, info):
        """空串/None → 0；小数（"81.8"/81.8）→ 四舍五入；"1,234" → 1234。"""
        if v is None or (isinstance(v, str) and not v.strip()):
            return 0
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, int):
            return v
        try:
            return int(round(float(str(v).strip().replace(",", "").replace("，", ""))))
        except (TypeError, ValueError):
            label = NUM_FIELDS.get(info.field_name, info.field_name)
            raise ValueError(f"「{label}」需要填写数字，当前填的是：{v}")

    @field_validator("live_date", mode="before")
    @classmethod
    def _norm_date(cls, v):
        """兼容 2026/09/10、2026.09.10、2026年9月10日、ISO 时间戳等写法。"""
        if isinstance(v, datetime):
            return v.date().isoformat()
        if isinstance(v, date):
            return v.isoformat()
        s = str(v or "").strip()
        s = (s.replace("年", "-").replace("月", "-").replace("日", "")
               .replace("/", "-").replace(".", "-").replace("T", " "))
        m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return s


def _parse_week(week: str) -> tuple[date, date]:
    """'2026-W37' → (Monday, Sunday)。容忍误传日期（2026-09-07 → 该日所在周的周一）。"""
    s = (week or "").strip()
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", s)
    if not m:
        iso = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if iso:
            try:
                d = date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
            except ValueError:
                raise HTTPException(status_code=422, detail=f"无效周次：{week}")
            monday = d - timedelta(days=d.weekday())
            return monday, monday + timedelta(days=6)
        raise HTTPException(status_code=422, detail=f"周次格式应为 YYYY-Www，收到：{week}")
    year, week_no = int(m.group(1)), int(m.group(2))
    try:
        monday = date.fromisocalendar(year, week_no, 1)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"无效周次：{week}")
    return monday, monday + timedelta(days=6)


def _parse_month(month: str) -> tuple[date, date]:
    """'2026-09' → (1号, 月末)。"""
    m = re.fullmatch(r"(\d{4})-(\d{2})", month or "")
    if not m:
        raise HTTPException(status_code=422, detail=f"月份格式应为 YYYY-MM，收到：{month}")
    start = date(int(m.group(1)), int(m.group(2)), 1)
    nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, nxt - timedelta(days=1)


def _period_range(mode: str, week: str, month: str) -> tuple[date, date]:
    if mode == "month":
        if month:
            return _parse_month(month)
        today = date.today()
        return today.replace(day=1), today
    if week:
        return _parse_week(week)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


@router.get("/live")
def get_live(
    mode: str = Query("week"),
    week: str = Query(""),
    month: str = Query(""),
    db: SqlSession = Depends(get_db),
):
    """直播数据统计：按周/月汇总 + 明细列表。"""
    start, end = _period_range(mode, week, month)
    rows = (
        db.query(LiveStream)
        .filter(LiveStream.live_date >= start, LiveStream.live_date <= end)
        .order_by(LiveStream.live_date.desc(), LiveStream.id.desc())
        .all()
    )
    items = [
        {
            "id": r.id,
            "live_date": r.live_date.isoformat(),
            "platform": r.platform,
            "account": r.account or "",
            "title": r.title or "",
            "duration_min": r.duration_min or 0,
            "viewers": r.viewers or 0,
            "peak_online": r.peak_online or 0,
            "engagement": r.engagement or 0,
            "new_followers": r.new_followers or 0,
            "leads_count": r.leads_count or 0,
            "note": r.note or "",
        }
        for r in rows
    ]
    summary = {
        "count": len(items),
        "duration_min": sum(i["duration_min"] for i in items),
        "viewers": sum(i["viewers"] for i in items),
        "peak_online": max((i["peak_online"] for i in items), default=0),
        "engagement": sum(i["engagement"] for i in items),
        "new_followers": sum(i["new_followers"] for i in items),
        "leads_count": sum(i["leads_count"] for i in items),
    }
    return {
        "mode": mode,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "summary": summary,
        "rows": items,
    }


@router.post("/live")
def create_live(body: LiveIn, db: SqlSession = Depends(get_db)):
    try:
        d = date.fromisoformat(body.live_date)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"无效日期：{body.live_date}")
    fields = body.model_dump()
    fields["live_date"] = d
    record = LiveStream(**fields)
    db.add(record)
    db.commit()
    return {"ok": True, "id": record.id}


@router.put("/live/{live_id}")
def update_live(live_id: int, body: LiveIn, db: SqlSession = Depends(get_db)):
    record = db.query(LiveStream).filter(LiveStream.id == live_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="直播记录不存在")
    try:
        d = date.fromisoformat(body.live_date)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"无效日期：{body.live_date}")
    for k, v in {**body.model_dump(), "live_date": d}.items():
        setattr(record, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/live/{live_id}")
def delete_live(live_id: int, db: SqlSession = Depends(get_db)):
    record = db.query(LiveStream).filter(LiveStream.id == live_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="直播记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
