"""Report generation API — 周报/月报."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..models import get_db
from ..models.platform_metrics import PlatformDailyMetrics
from ..models.content import ContentDetail

router = APIRouter()

PLATFORMS = ["抖音", "视频号", "公众号", "小红书"]

REPORT_TEMPLATE = """# {period}新媒体运营汇报

## 一、周期概述

汇报周期：**{start} 至 {end}**

{overview}

---

## 二、各平台日常运营与内容输出详情

{platform_details}

---

## 三、各平台数据总览

{data_overview}

---

## 四、核心指标达成分析

{kpi_analysis}

---

## 五、问题与不足

> 【自动生成模板，请根据实际情况修改】

### 内容层面
（待填写）

### 流量层面
（待填写）

### 转化层面
（待填写）

### 运营执行层面
（待填写）

---

## 六、优化策略与行动计划

> 【自动生成模板，请根据实际情况修改】

| 策略 | 具体行动 | 时间节点 | 责任人 |
|------|---------|---------|--------|
| | | | |

---

## 七、下周期目标与KPI规划

{next_plan}

---
*本报告由新媒体运营工作台自动生成*
"""


def _week_range(today: date):
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _last_week_range(today: date):
    monday, sunday = _week_range(today)
    return monday - timedelta(weeks=1), sunday - timedelta(weeks=1)


def _month_range(today: date):
    start = today.replace(day=1)
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    if end > today:
        end = today
    return start, end


def _last_month_range(today: date):
    last_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_end = today.replace(day=1) - timedelta(days=1)
    return last_start, last_end


@router.get("")
def generate_report(
    report_type: str = Query("weekly", pattern="^(weekly|monthly)$"),
    week: str = Query("", description="指定周期（周报传周一日期 YYYY-MM-DD；月报传 YYYY-MM-01），默认上周/上月"),
    db: Session = Depends(get_db),
):
    """生成周报或月报 Markdown。周报默认取上周数据。"""
    today = date.today()

    if report_type == "weekly":
        if week:
            start = date.fromisoformat(week)
        else:
            start, _ = _last_week_range(today)  # 默认上周
        end = start + timedelta(days=6)
        period = "周"
    else:
        if week:
            start = date.fromisoformat(week)
            end = (date(start.year + 1, 1, 1) - timedelta(days=1)) if start.month == 12 else (date(start.year, start.month + 1, 1) - timedelta(days=1))
            if end > today:
                end = today
        else:
            start, end = _last_month_range(today)  # 默认上月
        period = "月"

    # Collect data
    rows = (
        db.query(PlatformDailyMetrics)
        .filter(
            PlatformDailyMetrics.date >= start,
            PlatformDailyMetrics.date <= end,
        )
        .all()
    )

    # Per-platform aggregation
    platform_stats = {}
    for plat in PLATFORMS:
        plat_rows = [r for r in rows if r.platform == plat]
        if not plat_rows:
            continue

        def s(field):
            return sum(getattr(r, field) or 0 for r in plat_rows)

        content_count = (
            db.query(ContentDetail)
            .filter(
                ContentDetail.platform == plat,
                ContentDetail.publish_date >= start,
                ContentDetail.publish_date <= end,
            )
            .count()
        )

        latest_followers = plat_rows[-1].followers if plat_rows else 0

        platform_stats[plat] = {
            "followers": latest_followers,
            "new_followers": s("new_followers"),
            "plays": s("plays"),
            "reads": s("reads"),
            "note_reads": s("note_reads"),
            "likes": s("likes"),
            "comments": s("comments"),
            "shares": s("shares"),
            "bookmarks": s("bookmarks"),
            "publish_count": s("publish_count"),
            "content_count": content_count,
            "conversion_count": s("conversion_count"),
            "ad_spend": s("ad_spend"),
        }

        # Last period comparison
        if report_type == "weekly":
            last_start = start - timedelta(weeks=1)
            last_end = end - timedelta(weeks=1)
        else:
            last_start = (start - timedelta(days=1)).replace(day=1)
            last_end = start - timedelta(days=1)

        last_rows = (
            db.query(PlatformDailyMetrics)
            .filter(
                PlatformDailyMetrics.platform == plat,
                PlatformDailyMetrics.date >= last_start,
                PlatformDailyMetrics.date <= last_end,
            )
            .all()
        )

        def ls(field):
            return sum(getattr(r, field) or 0 for r in last_rows)

        def qoq(this_val, last_val):
            if last_val == 0:
                return "—"
            return f"{'↑' if this_val >= last_val else '↓'}{abs(round((this_val - last_val) / last_val * 100, 1))}%"

        ps = platform_stats[plat]
        ps["followers_qoq"] = qoq(ps["new_followers"], ls("new_followers"))
        total_plays_this = ps["plays"] + ps["reads"] + ps["note_reads"]
        total_plays_last = ls("plays") + ls("reads") + ls("note_reads")
        ps["plays_qoq"] = qoq(total_plays_this, total_plays_last)
        total_engage_this = ps["likes"] + ps["comments"] + ps["shares"] + ps["bookmarks"]
        total_engage_last = ls("likes") + ls("comments") + ls("shares") + ls("bookmarks")
        ps["engage_qoq"] = qoq(total_engage_this, total_engage_last)

    # Build report sections
    total_followers = sum(ps["new_followers"] for ps in platform_stats.values())
    total_plays = sum(ps["plays"] + ps["reads"] + ps["note_reads"] for ps in platform_stats.values())
    total_engage = sum(ps["likes"] + ps["comments"] + ps["shares"] + ps["bookmarks"] for ps in platform_stats.values())
    total_publish = sum(ps["publish_count"] for ps in platform_stats.values())

    overview = (
        f"本{period}四平台累计新增粉丝 **{total_followers}**，"
        f"总曝光/阅读量 **{total_plays}**，"
        f"总互动量 **{total_engage}**，"
        f"内容发布 **{total_publish}** 条。"
    )

    # Platform details
    platform_details = ""
    for plat in PLATFORMS:
        ps = platform_stats.get(plat)
        if not ps:
            platform_details += f"### {plat}\n本{period}暂无数据。\n\n"
            continue
        platform_details += (
            f"### {plat}\n"
            f"- 发布内容：**{ps['content_count']}** 条\n"
            f"- 新增粉丝：**{ps['new_followers']}**（环比 {ps['followers_qoq']}）\n"
            f"- 曝光/阅读：**{ps['plays'] + ps['reads'] + ps['note_reads']}**（环比 {ps['plays_qoq']}）\n"
            f"- 互动量：**{ps['likes'] + ps['comments'] + ps['shares'] + ps['bookmarks']}**（环比 {ps['engage_qoq']}）\n"
        )
        if ps["conversion_count"]:
            platform_details += f"- 转化数：**{ps['conversion_count']}**\n"
        if ps["ad_spend"]:
            platform_details += f"- 投流消耗：**{ps['ad_spend']}** 元\n"
        platform_details += "\n"

    # Data overview table
    data_overview = (
        "| 平台 | 总粉丝 | 新增粉丝 | 环比 | 曝光/阅读 | 环比 | 互动量 | 环比 | 发布数 |\n"
        "|------|--------|---------|------|----------|------|--------|------|--------|\n"
    )
    for plat in PLATFORMS:
        ps = platform_stats.get(plat)
        if not ps:
            continue
        plays_total = ps["plays"] + ps["reads"] + ps["note_reads"]
        engage_total = ps["likes"] + ps["comments"] + ps["shares"] + ps["bookmarks"]
        data_overview += (
            f"| {plat} | {ps['followers']} | {ps['new_followers']} | {ps['followers_qoq']} | "
            f"{plays_total} | {ps['plays_qoq']} | {engage_total} | {ps['engage_qoq']} | "
            f"{ps['publish_count']} |\n"
        )

    # KPI analysis (simple auto-generated)
    kpi_analysis = "### 各平台达成情况\n\n"
    for plat in PLATFORMS:
        ps = platform_stats.get(plat)
        if not ps:
            continue
        kpi_analysis += (
            f"**{plat}**：新增粉丝 {ps['new_followers']}，"
            f"总曝光 {ps['plays'] + ps['reads'] + ps['note_reads']}，"
            f"互动 {ps['likes'] + ps['comments'] + ps['shares'] + ps['bookmarks']}。\n\n"
        )
    kpi_analysis += "> 【请补充各平台 KPI 达成率与波动原因分析】\n"

    # Next plan
    next_plan = "> 【请根据本周期表现制定下周期各平台目标与 KPI】\n"

    report = REPORT_TEMPLATE.format(
        period=period,
        start=str(start),
        end=str(end),
        overview=overview,
        platform_details=platform_details,
        data_overview=data_overview,
        kpi_analysis=kpi_analysis,
        next_plan=next_plan,
    )

    return {"markdown": report}
