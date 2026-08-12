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
    mode: str = Query("week"),
    db: Session = Depends(get_db),
):
    """首页总览：可选周/月筛选，默认上周/上月。"""
    today = date.today()
    if start_week and end_week:
        if mode == "month":
            this_mon = date.fromisoformat(start_week).replace(day=1)
            next_m = this_mon.replace(day=28) + timedelta(days=4)
            this_tue = next_m - timedelta(days=next_m.day)
            last_mon = (this_mon - timedelta(days=1)).replace(day=1)
            last_tue = (last_mon.replace(day=28) + timedelta(days=4))
            last_tue = last_tue - timedelta(days=last_tue.day)
        else:
            this_mon = parse_week(start_week)
            this_tue = parse_week(end_week) + timedelta(days=6)
            last_mon = this_mon - timedelta(weeks=1)
            last_tue = this_tue - timedelta(weeks=1)
    else:
        if mode == "month":
            # 默认上月
            this_mon = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            next_m = this_mon.replace(day=28) + timedelta(days=4)
            this_tue = next_m - timedelta(days=next_m.day)
            last_mon = (this_mon - timedelta(days=1)).replace(day=1)
            last_tue = (last_mon.replace(day=28) + timedelta(days=4))
            last_tue = last_tue - timedelta(days=last_tue.day)
        else:
            # 默认显示上周
            this_mon, this_tue = _last_week_range(today)
            last_mon, last_tue = this_mon - timedelta(weeks=1), this_tue - timedelta(weeks=1)

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

        # 粉丝总数：取本周已录入数据中最大的粉丝数（粉丝只能增长）
        followers_now = max((r.followers or 0 for r in this_week), default=0)

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
    mode: str = Query("week", description="week 或 month"),
    db: Session = Depends(get_db),
):
    """平台趋势：按周显示最近 12 周度记录，按月显示最近 12 个月度记录，跟随看板维度。"""
    today = date.today()
    from sqlalchemy import extract

    def _month_cn(d):
        return f"{d.year}年{d.month}月"

    def _agg(rows):
        """对同一周期的多条记录聚合为单个指标 dict。"""
        g = {"followers": 0, "new_followers": 0, "plays": 0, "reads": 0, "note_reads": 0,
             "likes": 0, "comments": 0, "shares": 0, "bookmarks": 0, "hearts": 0,
             "in_views": 0, "completion_rate": 0, "publish_count": 0}
        for r in rows:
            g["followers"] = max(g["followers"], r.followers or 0)
            g["new_followers"] += r.new_followers or 0
            g["plays"] += r.plays or 0
            g["reads"] += r.reads or 0
            g["note_reads"] += r.note_reads or 0
            g["likes"] += r.likes or 0
            g["comments"] += r.comments or 0
            g["shares"] += r.shares or 0
            g["bookmarks"] += r.bookmarks or 0
            g["hearts"] += r.hearts or 0
            g["in_views"] += r.in_views or 0
            g["completion_rate"] = max(g["completion_rate"], r.completion_rate or 0)
            g["publish_count"] += r.publish_count or 0
        return g

    def _fmt(agg_map, labels):
        out = []
        for key in labels:
            g = agg_map.get(key)
            if not g:
                continue
            plays_reads = g["plays"] + g["reads"] + g["note_reads"]
            engagement = g["likes"] + g["comments"] + g["shares"] + g["bookmarks"]
            out.append({
                "label": _month_cn(key) if mode == "month" else _week_cn(key),
                "week_cn": _week_cn(key),
                "month_cn": _month_cn(key),
                "date": str(key),
                "followers": g["followers"],
                "new_followers": g["new_followers"],
                "plays_reads": plays_reads,
                "plays": g["plays"],
                "reads": g["reads"],
                "note_reads": g["note_reads"],
                "likes": g["likes"],
                "comments": g["comments"],
                "shares": g["shares"],
                "bookmarks": g["bookmarks"],
                "hearts": g["hearts"],
                "in_views": g["in_views"],
                "completion_rate": g["completion_rate"],
                "publish_count": g["publish_count"],
                "engagement": engagement,
            })
        return out

    if mode == "month":
        # 最近 12 个月（含当前月），只看月度记录（每月 1 号）
        month_keys = []
        for i in range(11, -1, -1):
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12
                y -= 1
            month_keys.append(date(y, m, 1))
        since = month_keys[0]
        q = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.platform == platform,
                PlatformDailyMetrics.date >= since,
                PlatformDailyMetrics.date <= today,
                extract("day", PlatformDailyMetrics.date) == 1,
            )
        )
        if account:
            q = q.filter(PlatformDailyMetrics.account == account)
        rows = q.order_by(PlatformDailyMetrics.date.asc()).all()
        by_key = defaultdict(list)
        for r in rows:
            by_key[date(r.date.year, r.date.month, 1)].append(r)
        agg_map = {k: _agg(v) for k, v in by_key.items()}
        trend_data = _fmt(agg_map, month_keys)
    else:
        # 最近 12 周，只看周度记录（非每月 1 号）
        this_monday = today - timedelta(days=today.weekday())
        week_keys = [this_monday - timedelta(weeks=i) for i in range(11, -1, -1)]
        since = week_keys[0]
        q = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.platform == platform,
                PlatformDailyMetrics.date >= since,
                PlatformDailyMetrics.date <= this_monday,
                extract("day", PlatformDailyMetrics.date) != 1,
            )
        )
        if account:
            q = q.filter(PlatformDailyMetrics.account == account)
        rows = q.order_by(PlatformDailyMetrics.date.asc()).all()
        by_key = defaultdict(list)
        for r in rows:
            by_key[r.date].append(r)
        agg_map = {k: _agg(v) for k, v in by_key.items()}
        trend_data = _fmt(agg_map, week_keys)

    return {
        "platform": platform,
        "account": account or "(全部账号)",
        "mode": mode,
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


@router.get("/hot-content")
def hot_content(
    mode: str = Query("week", description="week 或 month"),
    week: str = Query("", description="周次 '2026-W32' 或 'YYYY-MM-DD'"),
    month: str = Query("", description="月份 YYYY-MM，按月时使用"),
    db: Session = Depends(get_db),
):
    """本周热门：直接抓取内容明细，按平台取点赞 Top5。"""
    today = date.today()
    if mode == "month":
        if month:
            start_d = date.fromisoformat(f"{month}-01")
        else:
            start_d = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_m = start_d.replace(day=28) + timedelta(days=4)
        end_d = next_m - timedelta(days=next_m.day)
    elif week:
        start_d = parse_week(week)
        end_d = start_d + timedelta(days=6)
    else:
        start_d, end_d = _last_week_range(today)

    rows = (
        db.query(ContentDetail)
        .filter(
            ContentDetail.publish_date >= start_d,
            ContentDetail.publish_date <= end_d,
        )
        .all()
    )
    by_plat = defaultdict(list)
    for r in rows:
        by_plat[r.platform].append(r)

    result = {}
    for plat in PLATFORMS:
        items = sorted(by_plat.get(plat, []), key=lambda r: (r.likes or 0), reverse=True)[:5]
        result[plat] = [
            {
                "id": r.id,
                "title": r.title,
                "platform": r.platform,
                "author": r.author or "",
                "publish_date": str(r.publish_date),
                "likes": r.likes or 0,
                "impressions": r.impressions or 0,
                "comments": r.comments or 0,
                "shares": r.shares or 0,
                "is_viral": r.is_viral or 0,
            }
            for r in items
        ]
    return {"period": f"{start_d} ~ {end_d}", "data": result}


@router.get("/platform-detail")
def platform_detail(
    platform: str = Query(...),
    account: str = Query("", description="账号，留空返回该平台所有账号汇总"),
    week: str = Query("", description="周次 '2026-W32' 或 'YYYY-MM-DD'，默认上周"),
    mode: str = Query("week", description="week 或 month"),
    month: str = Query("", description="月份 YYYY-MM，按月时使用"),
    db: Session = Depends(get_db),
):
    """平台→账号级联明细：按周或按月独立统计。"""
    today = date.today()
    if mode == "month":
        if month:
            this_mon = date.fromisoformat(f"{month}-01")
        else:
            this_mon = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_month = this_mon.replace(day=28) + timedelta(days=4)
        this_sun = next_month - timedelta(days=next_month.day)
        last_mon = (this_mon - timedelta(days=1)).replace(day=1)
        last_next = last_mon.replace(day=28) + timedelta(days=4)
        last_sun = last_next - timedelta(days=last_next.day)
    elif week:
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
