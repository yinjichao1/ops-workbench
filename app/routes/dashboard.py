"""Dashboard API — overview cards, trends, comparisons."""

from collections import defaultdict
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import get_db, MonthlyTarget
from ..models.platform_metrics import PlatformDailyMetrics
from ..models.content import ContentDetail
from ..routes.data import parse_week

router = APIRouter()

PLATFORMS = ["抖音", "视频号", "公众号", "小红书"]


def _week_str(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _week_cn(d: date) -> str:
    first_day = d.replace(day=1)
    first_mon = first_day + timedelta(days=(7 - first_day.weekday()) % 7)
    if first_mon.month != d.month:
        first_mon = d.replace(day=1)
        while first_mon.weekday() != 0:
            first_mon += timedelta(days=1)
    if d < first_mon:
        prev_month = first_day - timedelta(days=1)
        prev_first = prev_month.replace(day=1)
        prev_mon = prev_first + timedelta(days=(7 - prev_first.weekday()) % 7)
        if prev_mon.month != prev_first.month:
            prev_mon = prev_first
            while prev_mon.weekday() != 0:
                prev_mon += timedelta(days=1)
        wn = ((d - prev_mon).days // 7) + 1
        return f"{prev_mon.year}年{prev_mon.month}月第{wn}周"
    wn = ((d - first_mon).days // 7) + 1
    return f"{d.year}年{d.month}月第{wn}周"


ACCOUNTS = {
    "抖音": ["思格电网", "安哥", "范校", "东北电气人都认"],
    "视频号": ["思格电网", "范校"],
    "公众号": ["思格电网"],
    "小红书": ["小格", "学姐"],
}


def _week_range(today: date):
    """Monday-Sunday of current week."""
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _last_week_range(today: date):
    monday, sunday = _week_range(today)
    return monday - timedelta(weeks=1), sunday - timedelta(weeks=1)


def _month_range(today: date):
    return today.replace(day=1), today


@router.get("/overview")
def dashboard_overview(
    start_week: str = Query(""),
    end_week: str = Query(""),
    db: Session = Depends(get_db),
):
    """首页总览：可选周次筛选，默认上周。"""
    today = date.today()
    if start_week and end_week:
        this_mon = parse_week(start_week)
        this_tue = parse_week(end_week) + timedelta(days=6)
        last_mon = this_mon - timedelta(weeks=1)
        last_tue = this_tue - timedelta(weeks=1)
    else:
        # 默认显示上周
        last_mon, last_tue = _week_range(today)
        this_mon = last_mon - timedelta(weeks=1)
        this_tue = last_tue - timedelta(weeks=1)
        # swap: this变成上周, last变成前一周
        this_mon, last_mon = last_mon, this_mon
        this_tue, last_tue = last_tue, this_tue

    # Available weeks for filter
    all_weeks = (
        db.query(PlatformDailyMetrics.date)
        .distinct()
        .order_by(PlatformDailyMetrics.date.desc())
        .limit(20)
        .all()
    )
    available_weeks = [{"iso": _week_str(r[0]), "cn": _week_cn(r[0])} for r in all_weeks]

    result = []

    for plat in PLATFORMS:
        this_week = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.platform == plat,
                PlatformDailyMetrics.date >= this_mon,
                PlatformDailyMetrics.date <= this_tue,
            )
            .all()
        )

        last_week = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.platform == plat,
                PlatformDailyMetrics.date >= last_mon,
                PlatformDailyMetrics.date <= last_tue,
            )
            .all()
        )

        # Aggregate
        def sum_field(rows, field):
            return sum(getattr(r, field) or 0 for r in rows)

        def avg_field(rows, field):
            vals = [getattr(r, field) or 0 for r in rows]
            return sum(vals) / len(vals) if vals else 0

        tw = {
            k: sum_field(this_week, k)
            for k in ["followers", "likes", "comments", "shares", "new_followers",
                       "publish_count", "plays", "reads", "note_reads", "bookmarks",
                       "hearts", "in_views", "completion_rate"]
        }
        lw = {
            k: sum_field(last_week, k)
            for k in tw
        }
        # completion_rate is avg not sum
        tw["completion_rate"] = avg_field(this_week, "completion_rate")

        # Engagement total
        total_engage_this = tw["likes"] + tw["comments"] + tw["shares"] + tw["bookmarks"]
        total_engage_last = lw["likes"] + lw["comments"] + lw["shares"] + lw["bookmarks"]

        # Plays/reads total
        plays_reads_this = tw["plays"] + tw["reads"] + tw["note_reads"]
        plays_reads_last = lw["plays"] + lw["reads"] + lw["note_reads"]

        # Latest followers
        latest = (
            db.query(PlatformDailyMetrics)
            .filter(PlatformDailyMetrics.platform == plat)
            .order_by(PlatformDailyMetrics.date.desc())
            .first()
        )
        followers_now = latest.followers if latest else 0

        def qoq(val_this, val_last):
            if val_last == 0:
                return 0
            return round((val_this - val_last) / val_last * 100, 1)

        # Top 5 content for this platform this week
        top5 = (
            db.query(ContentDetail)
            .filter(
                ContentDetail.platform == plat,
                ContentDetail.publish_date >= this_mon,
                ContentDetail.publish_date <= this_tue,
            )
            .order_by(ContentDetail.likes.desc())
            .limit(5)
            .all()
        )

        result.append({
            "platform": plat,
            "followers": followers_now,
            "followers_wow": qoq(tw["new_followers"], lw["new_followers"]),
            "new_followers": tw["new_followers"],
            "plays_reads": plays_reads_this,
            "plays_reads_wow": qoq(plays_reads_this, plays_reads_last),
            "likes": tw["likes"],
            "comments": tw["comments"],
            "shares": tw["shares"],
            "bookmarks": tw["bookmarks"],
            "hearts": tw["hearts"],
            "in_views": tw["in_views"],
            "completion_rate": tw["completion_rate"],
            "engagement": total_engage_this,
            "engagement_wow": qoq(total_engage_this, total_engage_last),
            "publish_count": tw["publish_count"],
            "publish_wow": qoq(tw["publish_count"], lw["publish_count"]),
            "top5": [
                {"id": c.id, "title": c.title, "likes": c.likes,
                 "comments": c.comments, "shares": c.shares}
                for c in top5
            ],
        })

    return {"data": result, "week": f"{this_mon} ~ {this_tue}", "available_weeks": available_weeks}


@router.get("/trend")
def dashboard_trend(
    platform: str = Query(...),
    account: str = Query(""),
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """平台趋势：指定天数每周核心指标。可按账号过滤。"""
    today = date.today()
    since = today - timedelta(days=days)

    q = (
        db.query(PlatformDailyMetrics)
        .filter(
            PlatformDailyMetrics.platform == platform,
            PlatformDailyMetrics.date >= since,
            PlatformDailyMetrics.date <= today,
        )
    )
    if account:
        q = q.filter(PlatformDailyMetrics.account == account)
    rows = q.order_by(PlatformDailyMetrics.date.asc()).all()

    # 按周聚合
    from collections import defaultdict
    if not account:
        grouped = defaultdict(lambda: {"followers": 0, "likes": 0, "comments": 0, "shares": 0, "new_followers": 0, "plays": 0, "reads": 0, "note_reads": 0, "bookmarks": 0, "completion_rate": 0, "engagement_rate": 0, "count": 0, "accounts": set()})
        for r in rows:
            k = r.date
            g = grouped[k]
            g["followers"] = max(g["followers"], r.followers or 0)
            g["likes"] += r.likes or 0
            g["comments"] += r.comments or 0
            g["shares"] += r.shares or 0
            g["new_followers"] += r.new_followers or 0
            g["plays"] += r.plays or 0
            g["reads"] += r.reads or 0
            g["note_reads"] += r.note_reads or 0
            g["bookmarks"] += r.bookmarks or 0
            g["completion_rate"] = max(g["completion_rate"], r.completion_rate or 0)
            g["engagement_rate"] = max(g["engagement_rate"], r.engagement_rate or 0)
            g["count"] += 1
            g["accounts"].add(r.account or "")
        trend_data = [
            {
                "week": _week_str(k),
                "week_cn": _week_cn(k),
                "date": str(k),
                "account": "、".join(sorted(v["accounts"])),
                "followers": v["followers"],
                "likes": v["likes"],
                "comments": v["comments"],
                "shares": v["shares"],
                "new_followers": v["new_followers"],
                "plays": v["plays"],
                "reads": v["reads"],
                "note_reads": v["note_reads"],
                "bookmarks": v["bookmarks"],
                "completion_rate": v["completion_rate"],
                "engagement_rate": v["engagement_rate"],
            }
            for k, v in sorted(grouped.items())
        ]
    else:
        trend_data = [
            {
                "week": _week_str(r.date),
                "date": str(r.date),
                "account": r.account or "",
                "followers": r.followers,
                "likes": r.likes or 0,
                "comments": r.comments or 0,
                "shares": r.shares or 0,
                "new_followers": r.new_followers or 0,
                "plays": r.plays or 0,
                "reads": r.reads or 0,
                "note_reads": r.note_reads or 0,
                "bookmarks": r.bookmarks or 0,
                "completion_rate": r.completion_rate or 0,
                "engagement_rate": r.engagement_rate or 0,
            }
            for r in rows
        ]

    return {
        "platform": platform,
        "account": account or "(全部账号)",
        "accounts": ACCOUNTS.get(platform, ["主号"]),
        "trend": trend_data,
    }


@router.get("/kpi")
def dashboard_kpi(db: Session = Depends(get_db)):
    """本月 KPI 进度。优先使用用户在 targets 表中设置的目标，未设则回落到上月数据。"""
    today = date.today()
    this_start, _ = _month_range(today)
    last_start = (this_start - timedelta(days=1)).replace(day=1)
    last_end = this_start - timedelta(days=1)

    # 拉本月所有平台目标
    targets = {
        r.platform: r
        for r in db.query(MonthlyTarget).filter(
            MonthlyTarget.year == today.year,
            MonthlyTarget.month == today.month,
        ).all()
    }

    result = []
    for plat in PLATFORMS:
        this_month = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.platform == plat,
                PlatformDailyMetrics.date >= this_start,
                PlatformDailyMetrics.date <= today,
            )
            .all()
        )
        last_month = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.platform == plat,
                PlatformDailyMetrics.date >= last_start,
                PlatformDailyMetrics.date <= last_end,
            )
            .all()
        )

        def s(rows, field):
            return sum(getattr(r, field) or 0 for r in rows)

        followers_actual = s(this_month, "new_followers")
        plays_actual = s(this_month, "plays") + s(this_month, "reads") + s(this_month, "note_reads")
        publish_actual = s(this_month, "publish_count")
        engagement_actual = (
            s(this_month, "likes") + s(this_month, "comments")
            + s(this_month, "shares") + s(this_month, "bookmarks")
        )

        # 优先用设置的目标，没设就回落到上月
        t = targets.get(plat)
        if t and t.target_new_followers > 0:
            followers_target = t.target_new_followers
        else:
            followers_target = max(s(last_month, "new_followers"), 1)

        if t and t.target_plays_reads > 0:
            plays_target = t.target_plays_reads
        else:
            plays_target = max(
                s(last_month, "plays") + s(last_month, "reads") + s(last_month, "note_reads"),
                1,
            )

        if t and t.target_publish_count > 0:
            publish_target = t.target_publish_count
        else:
            publish_target = max(s(last_month, "publish_count"), 1)

        if t and t.target_engagement > 0:
            engagement_target = t.target_engagement
        else:
            engagement_target = max(
                s(last_month, "likes") + s(last_month, "comments")
                + s(last_month, "shares") + s(last_month, "bookmarks"),
                1,
            )

        result.append({
            "platform": plat,
            "followers_kpi": {"actual": followers_actual, "target": followers_target, "pct": round(followers_actual / followers_target * 100, 1)},
            "plays_kpi": {"actual": plays_actual, "target": plays_target, "pct": round(plays_actual / plays_target * 100, 1)},
            "publish_kpi": {"actual": publish_actual, "target": publish_target, "pct": round(publish_actual / publish_target * 100, 1)},
            "engagement_kpi": {"actual": engagement_actual, "target": engagement_target, "pct": round(engagement_actual / engagement_target * 100, 1)},
            "has_target": t is not None,
        })

    return {"data": result, "year": today.year, "month": today.month}


@router.get("/platform-detail")
def platform_detail(
    platform: str = Query(...),
    account: str = Query("", description="账号，留空返回该平台所有账号汇总"),
    week: str = Query("", description="周次 '2026-W32' 或 'YYYY-MM-DD'，默认上周"),
    db: Session = Depends(get_db),
):
    """平台→账号级联明细：默认显示上周数据。"""
    today = date.today()
    if week:
        this_mon = parse_week(week)
        this_sun = this_mon + timedelta(days=6)
        last_mon = this_mon - timedelta(weeks=1)
        last_sun = this_sun - timedelta(weeks=1)
    else:
        last_mon, last_sun = _last_week_range(today)
        this_mon, this_sun = last_mon, last_sun
        last_mon, last_sun = this_mon - timedelta(weeks=1), this_sun - timedelta(weeks=1)

    # 本周数据
    base_q = (
        db.query(PlatformDailyMetrics)
        .filter(
            PlatformDailyMetrics.platform == platform,
            PlatformDailyMetrics.date >= this_mon,
            PlatformDailyMetrics.date <= this_sun,
        )
    )
    if account:
        base_q = base_q.filter(PlatformDailyMetrics.account == account)

    this_week_rows = base_q.all()

    # 上周对比
    last_q = (
        db.query(PlatformDailyMetrics)
        .filter(
            PlatformDailyMetrics.platform == platform,
            PlatformDailyMetrics.date >= last_mon,
            PlatformDailyMetrics.date <= last_sun,
        )
    )
    if account:
        last_q = last_q.filter(PlatformDailyMetrics.account == account)
    last_week_rows = last_q.all()

    def s(rows, field):
        return sum(getattr(r, field) or 0 for r in rows)

    # 平台聚合
    followers = s(this_week_rows, "followers")
    new_followers = s(this_week_rows, "new_followers")
    plays = s(this_week_rows, "plays") + s(this_week_rows, "reads") + s(this_week_rows, "note_reads")
    engagement = s(this_week_rows, "likes") + s(this_week_rows, "comments") + s(this_week_rows, "shares") + s(this_week_rows, "bookmarks")
    publish_count = s(this_week_rows, "publish_count")

    last_new = s(last_week_rows, "new_followers")
    last_plays = s(last_week_rows, "plays") + s(last_week_rows, "reads") + s(last_week_rows, "note_reads")
    last_engage = s(last_week_rows, "likes") + s(last_week_rows, "comments") + s(last_week_rows, "shares") + s(last_week_rows, "bookmarks")

    def pct(now, prev):
        if not prev:
            return 0
        return round((now - prev) / prev * 100, 1)

    aggregate = {
        "platform": platform,
        "followers": followers,
        "new_followers": new_followers,
        "new_followers_pct": pct(new_followers, last_new),
        "plays_reads": plays,
        "plays_reads_pct": pct(plays, last_plays),
        "engagement": engagement,
        "engagement_pct": pct(engagement, last_engage),
        "publish_count": publish_count,
        "accounts": ACCOUNTS.get(platform, ["主号"]),
    }

    # 各账号子卡（按账号聚合本周数据）
    accounts_data = []
    if not account:  # 只有当不指定特定账号时才返回各账号明细
        for acct in ACCOUNTS.get(platform, ["主号"]):
            acct_rows = [
                r for r in this_week_rows
                if (r.account or "") == acct
            ]
            if not acct_rows:
                # 即使没数据也返回账号，让前端可以展示「暂无数据」
                accounts_data.append({
                    "account": acct,
                    "followers": 0,
                    "new_followers": 0,
                    "plays_reads": 0,
                    "engagement": 0,
                    "publish_count": 0,
                    "has_data": False,
                })
                continue
            acct_followers = s(acct_rows, "followers")
            acct_new = s(acct_rows, "new_followers")
            acct_plays = s(acct_rows, "plays") + s(acct_rows, "reads") + s(acct_rows, "note_reads")
            acct_engage = s(acct_rows, "likes") + s(acct_rows, "comments") + s(acct_rows, "shares") + s(acct_rows, "bookmarks")
            acct_pub = s(acct_rows, "publish_count")

            # 单账号上周对比
            last_acct_rows = [
                r for r in last_week_rows
                if (r.account or "") == acct
            ]
            last_a_new = s(last_acct_rows, "new_followers")
            last_a_plays = s(last_acct_rows, "plays") + s(last_acct_rows, "reads") + s(last_acct_rows, "note_reads")
            last_a_engage = s(last_acct_rows, "likes") + s(last_acct_rows, "comments") + s(last_acct_rows, "shares") + s(last_acct_rows, "bookmarks")

            accounts_data.append({
                "account": acct,
                "followers": acct_followers,
                "new_followers": acct_new,
                "new_followers_pct": pct(acct_new, last_a_new),
                "plays_reads": acct_plays,
                "plays_reads_pct": pct(acct_plays, last_a_plays),
                "likes": s(acct_rows, "likes"),
                "comments": s(acct_rows, "comments"),
                "shares": s(acct_rows, "shares"),
                "bookmarks": s(acct_rows, "bookmarks"),
                "hearts": s(acct_rows, "hearts"),
                "in_views": s(acct_rows, "in_views"),
                "completion_rate": max(r.completion_rate or 0 for r in acct_rows) if acct_rows else 0,
                "engagement": acct_engage,
                "publish_count": acct_pub,
                "has_data": True,
            })

    return {"aggregate": aggregate, "accounts_data": accounts_data}
