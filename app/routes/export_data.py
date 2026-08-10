"""Export data as CSV."""

import csv
import io
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as SqlSession
from ..models import get_db, PlatformDailyMetrics

router = APIRouter()

PLATFORMS = ["抖音", "视频号", "公众号", "小红书"]
HEADERS = [
    "平台", "账号", "周次", "日期",
    "粉丝", "新增粉丝", "播放/阅读",
    "点赞", "评论", "分享", "收藏", "爱心",
    "主页访问", "完播率(%)", "互动量", "发布数"
]


def _get_export_data(db: SqlSession, start: date, end: date, platform: str = ""):
    q = db.query(PlatformDailyMetrics).filter(
        PlatformDailyMetrics.date >= start,
        PlatformDailyMetrics.date <= end,
    )
    if platform:
        q = q.filter(PlatformDailyMetrics.platform == platform)
    return q.order_by(PlatformDailyMetrics.date.desc(), PlatformDailyMetrics.platform, PlatformDailyMetrics.account).all()


def _write_csv(rows: list[PlatformDailyMetrics]) -> io.StringIO:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    for r in rows:
        engagement = (r.likes or 0) + (r.comments or 0) + (r.shares or 0) + (r.bookmarks or 0)
        plays = (r.plays or 0) + (r.reads or 0) + (r.note_reads or 0)
        week_cn = _week_cn(r.date) if r.date else ""
        writer.writerow([
            r.platform, r.account or "", week_cn, r.date.isoformat() if r.date else "",
            r.followers or 0, r.new_followers or 0, plays,
            r.likes or 0, r.comments or 0, r.shares or 0,
            r.bookmarks or 0, r.hearts or 0,
            r.in_views or 0, f"{r.completion_rate or 0:.1f}",
            engagement, r.publish_count or 0,
        ])
    output.seek(0)
    return output


def _week_cn(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}年W{iso[1]}"


@router.get("/export")
def export_data(
    mode: str = Query("week", description="week 或 month"),
    platform: str = Query("", description="平台，空=全部"),
    week_val: str = Query("", description="YYYY-MM-DD (周一)"),
    month_val: str = Query("", description="YYYY-MM"),
    db: SqlSession = Depends(get_db),
):
    """导出 CSV：按周或按月。"""
    today = date.today()

    if mode == "week":
        if week_val:
            start = date.fromisoformat(week_val)
        else:
            # 默认上周
            wd = today - timedelta(days=(today.weekday() + 7) % 7 + 7)
            start = wd
        end = start + timedelta(days=6)
        label = f"{start.isoformat()}_{end.isoformat()}"
    else:
        if month_val:
            parts = month_val.split("-")
            start = date(int(parts[0]), int(parts[1]), 1)
        else:
            # 默认上月
            if today.month == 1:
                start = date(today.year - 1, 12, 1)
            else:
                start = date(today.year, today.month - 1, 1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        label = f"{start.isoformat()}_{end.isoformat()}"

    rows = _get_export_data(db, start, end, platform)
    csv_data = _write_csv(rows)

    response = StreamingResponse(
        iter([csv_data.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
    )
    response.headers["Content-Disposition"] = (
        f"attachment; filename=ops_{mode}_{label}.csv"
    )
    return response