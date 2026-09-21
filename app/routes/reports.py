"""Report generation API — 周报/月报."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..models import get_db
from ..models.platform_metrics import PlatformDailyMetrics
from ..models.content import ContentDetail, ContentCalendar, Task
from ..models.lead import Lead, LeadDeal

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

## 四、线索与成单转化

{lead_deal}

---

## 五、核心指标达成分析

{kpi_analysis}

---

## 六、问题与不足

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

## 七、优化策略与行动计划

> 【自动生成模板，请根据实际情况修改】

| 策略 | 具体行动 | 时间节点 | 责任人 |
|------|---------|---------|--------|
| | | | |

---

## 八、下周工作计划（联动任务管理与内容排期）

{next_week_plan}

---

## 九、下周期目标与KPI规划

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


def _next_week_range(today: date):
    """下周：下周一 ~ 下周日。"""
    this_monday = today - timedelta(days=today.weekday())
    next_monday = this_monday + timedelta(weeks=1)
    return next_monday, next_monday + timedelta(days=6)


# ============ 线索 / 成单 章节 ============

def _pct(a, b):
    return round(a / b * 100, 1) if b else 0.0


def _qoq(this_val, last_val):
    """环比：上期为 0 时显示 —，持平显示「持平」，避免除零。"""
    if not last_val:
        return "—"
    if this_val == last_val:
        return "持平"
    arrow = "↑" if this_val > last_val else "↓"
    return f"{arrow}{abs(round((this_val - last_val) / last_val * 100, 1))}%"


def _money(v):
    v = round(float(v or 0), 2)
    return f"¥{v:,.0f}" if v == int(v) else f"¥{v:,.2f}"


def _blank(v):
    return v if v not in (None, "") else "—"


def _lead_deal_section(db: Session, start: date, end: date,
                       last_start: date, last_end: date,
                       today: date, report_type: str, period: str) -> str:
    """「线索与成单转化」章节：线索总览 / 分渠道全链路 / 细分来源 / 分校区 / 每日趋势。"""
    from .leads import _parse_sub_source  # 复用看板的「备注细分渠道」口径

    lines = []

    # ---------- 本周期线索 ----------
    rows = db.query(Lead).filter(Lead.date >= start, Lead.date <= end).all()
    total = len(rows)
    valid = sum(1 for r in rows if r.validity == "有效")
    invalid = sum(1 for r in rows if r.validity == "无效")
    pending = sum(1 for r in rows if r.validity == "待定")
    contact_sum = sum(r.contact_count or 0 for r in rows)
    high_contact = sum(1 for r in rows if (r.contact_count or 0) >= 3)

    last_rows = db.query(Lead).filter(Lead.date >= last_start, Lead.date <= last_end).all()
    last_total = len(last_rows)

    # ---------- 本周期成单 ----------
    deals = (
        db.query(LeadDeal)
        .filter(LeadDeal.deal_date >= start, LeadDeal.deal_date <= end)
        .all()
    )
    deal_count = len(deals)
    deal_amount = round(sum(d.amount or 0 for d in deals), 2)
    deal_avg = round(deal_amount / deal_count, 2) if deal_count else 0

    # ---------- 4.1 总览 ----------
    avg_contact = round(contact_sum / total, 1) if total else 0
    lines.append("### 4.1 线索总览\n")
    lines.append(
        f"本{period}新增线索 **{total}** 条"
        f"（有效 **{valid}** / 无效 {invalid} / 待定 {pending}，"
        f"有效率 **{_pct(valid, total)}%**），环比 {_qoq(total, last_total)}；"
        f"累计沟通 **{contact_sum}** 次，人均沟通 **{avg_contact}** 次，"
        f"高意向（沟通 ≥3 次）**{high_contact}** 人。\n"
    )
    lines.append(
        f"本{period}成单 **{deal_count}** 单，成交金额 **{_money(deal_amount)}**，"
        f"客单价 **{_money(deal_avg)}**，线索→成单转化率 **{_pct(deal_count, total)}%**。\n"
    )

    # 本月累计（周报里用于看月度进度；月报周期本身就是本月，不再重复）
    if report_type == "weekly":
        m_start = today.replace(day=1)
        m_lead = db.query(Lead).filter(Lead.date >= m_start, Lead.date <= today).all()
        m_total = len(m_lead)
        m_valid = sum(1 for r in m_lead if r.validity == "有效")
        m_deal = (
            db.query(LeadDeal)
            .filter(LeadDeal.deal_date >= m_start, LeadDeal.deal_date <= today)
            .all()
        )
        m_amount = round(sum(d.amount or 0 for d in m_deal), 2)
        m_customers = len({(d.name or "").strip() for d in m_deal if (d.name or "").strip()})
        lines.append(
            f"> **本月累计**（{m_start} 至 {today}）：线索 **{m_total}** 条"
            f"（有效 **{m_valid}** 条，有效率 **{_pct(m_valid, m_total)}%**）；"
            f"成单 **{len(m_deal)}** 单（去重客户 {m_customers} 人），"
            f"成交金额 **{_money(m_amount)}**。\n"
        )
    else:
        m_start = start  # 月报：本月累计即本周期

    # ---------- 4.2 分渠道全链路（来源维度，与成单可对齐） ----------
    src_bucket = {}

    def _bucket(name):
        return src_bucket.setdefault(
            name or "其他",
            {"total": 0, "有效": 0, "无效": 0, "待定": 0, "i1": 0, "i3": 0, "i5": 0,
             "deal": 0, "amount": 0.0},
        )

    for r in rows:
        b = _bucket(r.source)
        b["total"] += 1
        b["有效" if r.validity == "有效" else ("无效" if r.validity == "无效" else "待定")] += 1
        it = r.intent or 0
        if it == 1:
            b["i1"] += 1
        elif it == 3:
            b["i3"] += 1
        elif it == 5:
            b["i5"] += 1
    for d in deals:
        b = _bucket(d.source)
        b["deal"] += 1
        b["amount"] += d.amount or 0

    lines.append("### 4.2 分渠道线索与成单\n")
    if src_bucket:
        lines.append("| 来源 | 线索数 | 有效 | 无效 | 待定 | 有效率 | 意向1 | 意向3 | 意向5 | 成单 | 转化率 | 成交金额 |")
        lines.append("|------|--------|------|------|------|--------|-------|-------|-------|------|--------|----------|")
        for name, b in sorted(src_bucket.items(), key=lambda x: -x[1]["total"]):
            lines.append(
                f"| {name} | {b['total']} | {b['有效']} | {b['无效']} | {b['待定']} | "
                f"{_pct(b['有效'], b['total'])}% | {b['i1']} | {b['i3']} | {b['i5']} | "
                f"{b['deal']} | {_pct(b['deal'], b['total'])}% | {_money(b['amount'])} |"
            )
        # 合计行
        lines.append(
            f"| **合计** | **{total}** | **{valid}** | **{invalid}** | **{pending}** | "
            f"**{_pct(valid, total)}%** | "
            f"**{sum(b['i1'] for b in src_bucket.values())}** | "
            f"**{sum(b['i3'] for b in src_bucket.values())}** | "
            f"**{sum(b['i5'] for b in src_bucket.values())}** | "
            f"**{deal_count}** | **{_pct(deal_count, total)}%** | **{_money(deal_amount)}** |"
        )
        lines.append("")
    else:
        lines.append(f"本{period}暂无线索与成单记录。\n")

    # ---------- 4.3 备注细分来源（Top 8） ----------
    sub_bucket = {}
    for r in rows:
        subs = _parse_sub_source(r.source, r.note or "")
        name = subs[0][1] if subs else (r.source or "其他")
        b = sub_bucket.setdefault(name, {"total": 0, "有效": 0})
        b["total"] += 1
        if r.validity == "有效":
            b["有效"] += 1

    if sub_bucket:
        top = sorted(sub_bucket.items(), key=lambda x: -x[1]["total"])[:8]
        lines.append("### 4.3 细分来源 Top（按备注识别）\n")
        lines.append("| 细分来源 | 线索数 | 有效 | 有效率 |")
        lines.append("|---------|--------|------|--------|")
        for name, b in top:
            lines.append(f"| {name} | {b['total']} | {b['有效']} | {_pct(b['有效'], b['total'])}% |")
        if len(sub_bucket) > len(top):
            lines.append(f"| *（其余 {len(sub_bucket) - len(top)} 个来源）* | "
                         f"{sum(b['total'] for _, b in sorted(sub_bucket.items(), key=lambda x: -x[1]['total'])[8:])} | — | — |")
        lines.append("")

    # ---------- 4.4 分校区 ----------
    cam_bucket = {}
    for r in rows:
        c = r.campus or r.owner or "未分配"
        b = cam_bucket.setdefault(c, {"total": 0, "有效": 0, "deal": 0, "amount": 0.0})
        b["total"] += 1
        if r.validity == "有效":
            b["有效"] += 1
    for d in deals:
        c = d.campus or "未分配"
        b = cam_bucket.setdefault(c, {"total": 0, "有效": 0, "deal": 0, "amount": 0.0})
        b["deal"] += 1
        b["amount"] += d.amount or 0

    if cam_bucket:
        lines.append("### 4.4 分校区线索与成单\n")
        lines.append("| 校区 | 线索数 | 有效 | 有效率 | 成单 | 转化率 | 成交金额 |")
        lines.append("|------|--------|------|--------|------|--------|----------|")
        for name, b in sorted(cam_bucket.items(), key=lambda x: -x[1]["total"]):
            lines.append(
                f"| {name} | {b['total']} | {b['有效']} | {_pct(b['有效'], b['total'])}% | "
                f"{b['deal']} | {_pct(b['deal'], b['total'])}% | {_money(b['amount'])} |"
            )
        lines.append("")

    # ---------- 4.5 每日线索趋势（仅周报，月报天数太多不列） ----------
    if report_type == "weekly":
        by_day = {}
        for r in rows:
            by_day[r.date.isoformat()] = by_day.get(r.date.isoformat(), 0) + 1
        # 补齐整周 7 天（无数据的日期显示 0，方便看断档）
        days = [(start + timedelta(days=i)).isoformat() for i in range(7)]
        lines.append("### 4.5 每日线索趋势\n")
        lines.append("| 日期 | " + " | ".join(d[5:].replace("-", "/") for d in days) + " |")
        lines.append("|------|" + "------|" * len(days))
        lines.append("| 线索数 | " + " | ".join(str(by_day.get(d, 0)) for d in days) + " |")
        lines.append("")

    lines.append("> 【请补充线索质量、渠道投放与转化效率的复盘结论】\n")
    return "\n".join(lines)


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

    # Collect data（周报排除每月1号月记录，月报只取1号月记录，避免相互污染）
    from sqlalchemy import extract
    day_filter = (
        (extract("day", PlatformDailyMetrics.date) != 1)
        if report_type == "weekly"
        else (extract("day", PlatformDailyMetrics.date) == 1)
    )
    rows = (
        db.query(PlatformDailyMetrics)
        .filter(
            PlatformDailyMetrics.date >= start,
            PlatformDailyMetrics.date <= end,
            day_filter,
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
                day_filter,
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

    # 周期概述补充：线索与成单（转化侧一句话摘要）
    _ld_rows = db.query(Lead).filter(Lead.date >= start, Lead.date <= end).all()
    _ld_total = len(_ld_rows)
    _ld_valid = sum(1 for r in _ld_rows if r.validity == "有效")
    _ld_deals = (
        db.query(LeadDeal)
        .filter(LeadDeal.deal_date >= start, LeadDeal.deal_date <= end)
        .all()
    )
    _ld_amount = round(sum(d.amount or 0 for d in _ld_deals), 2)
    overview += (
        f"\n\n转化侧：新增线索 **{_ld_total}** 条"
        f"（有效 **{_ld_valid}** 条，有效率 **{_pct(_ld_valid, _ld_total)}%**）；"
        f"成单 **{len(_ld_deals)}** 单，成交金额 **{_money(_ld_amount)}**，"
        f"线索→成单转化率 **{_pct(len(_ld_deals), _ld_total)}%**。"
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

    # 下周工作计划：联动内容排期 + 任务管理
    next_start, next_end = _next_week_range(today)
    cals = (
        db.query(ContentCalendar)
        .filter(ContentCalendar.scheduled_date >= next_start, ContentCalendar.scheduled_date <= next_end)
        .order_by(ContentCalendar.scheduled_date.asc(), ContentCalendar.platform.asc())
        .all()
    )
    tasks = (
        db.query(Task)
        .filter(Task.due_date >= next_start, Task.due_date <= next_end)
        .order_by(Task.due_date.asc())
        .all()
    )
    plan_lines = [f"> 自动联动内容排期（{len(cals)} 条）与任务管理（{len(tasks)} 项），生成后可继续编辑\n"]
    # 内容排期
    if cals:
        plan_lines.append(f"### 📅 下周内容排期（{next_start} 至 {next_end}，共 {len(cals)} 条）\n")
        plan_lines.append("| 日期 | 平台 | 账号 | 类型 | 标题 | 状态 |")
        plan_lines.append("|------|------|------|------|------|------|")
        for c in cals:
            plan_lines.append(
                f"| {c.scheduled_date} | {c.platform} | {c.account or '—'} | "
                f"{c.content_type} | {c.title} | {c.status} |"
            )
        plan_lines.append("")
    else:
        plan_lines.append(f"### 📅 下周内容排期\n下周（{next_start} 至 {next_end}）暂无排期。\n")
    # 任务管理
    if tasks:
        plan_lines.append(f"### ✅ 下周任务（{len(tasks)} 项）\n")
        plan_lines.append("| 截止日期 | 优先级 | 任务 | 负责人 | 状态 |")
        plan_lines.append("|---------|--------|------|--------|------|")
        for t in tasks:
            plan_lines.append(
                f"| {t.due_date} | {t.priority} | {t.title} | {t.assignee or '—'} | {t.status} |"
            )
        plan_lines.append("")
    else:
        plan_lines.append("### ✅ 下周任务\n下周暂无到期任务。\n")
    plan_lines.append("### 📝 补充安排（自由编辑）\n（待填写）\n")
    next_week_plan = "\n".join(plan_lines)

    # 线索与成单章节（周期口径与平台指标保持一致）
    if report_type == "weekly":
        ld_last_start, ld_last_end = start - timedelta(weeks=1), end - timedelta(weeks=1)
    else:
        ld_last_start = (start - timedelta(days=1)).replace(day=1)
        ld_last_end = start - timedelta(days=1)
    lead_deal = _lead_deal_section(
        db, start, end, ld_last_start, ld_last_end, today, report_type, period
    )

    report = REPORT_TEMPLATE.format(
        period=period,
        start=str(start),
        end=str(end),
        overview=overview,
        platform_details=platform_details,
        data_overview=data_overview,
        lead_deal=lead_deal,
        kpi_analysis=kpi_analysis,
        next_week_plan=next_week_plan,
        next_plan=next_plan,
    )

    return {"markdown": report}
