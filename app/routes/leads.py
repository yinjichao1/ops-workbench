"""Leads analysis API."""

from datetime import date, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session as SqlSession
from ..models import get_db, Lead
from io import BytesIO
import re

router = APIRouter()

STATUS_MAP = {"跟进中.": "跟进中", "跟进中": "跟进中", "未跟进": "未跟进", "无需跟进": "无需跟进"}
SOURCE_MAP = {"微信视频号": "微信视频号"}


def _last_week_range(today: date):
    """返回上周的周一和周日（date, date）。"""
    days_since_mon = today.weekday()
    last_mon = today - timedelta(days=days_since_mon + 7)
    return last_mon, last_mon + timedelta(days=6)  # 确保匹配


@router.delete("/leads/clear")
def clear_leads(db: SqlSession = Depends(get_db)):
    """清空所有线索数据。"""
    db.query(Lead).delete()
    db.commit()
    return {"ok": True}


def _parse_sub_source(source: str, note: str) -> list:
    """从备注中智能提取细分渠道。返回 [(category, value)]"""
    results = []
    n = note or ""

    if source == "抖音":
        # 提取 (XX抖音) 或 (XX抖音私信) 格式
        m = re.findall(r'[（(]([^）)]*?抖音[^）)]*?)[）)]', n)
        if m:
            for sub in m:
                sub_clean = sub.replace("私信", "").replace("号", "").strip()
                if sub_clean:
                    results.append(("抖音", sub_clean + "号"))
        # 提取 "范校抖音私信" "葛老师抖音" 无括号格式
        m2 = re.findall(r'(思格教育抖音|范校抖音|葛老师抖音|安哥抖音)(?:号|私信)?', n)
        for sub in m2:
            results.append(("抖音", sub + "号"))
        if not results:
            results.append(("抖音", "其他抖音来源"))

    elif source == "微信公众号":
        if "匹配工具" in n or "表单" in n:
            results.append(("公众号", "表单/匹配工具"))
        elif "进群" in n or "社群" in n or "加群" in n:
            results.append(("公众号", "进群/加社群"))
        elif "企业微信" in n:
            results.append(("公众号", "企业微信咨询"))
        else:
            results.append(("公众号", "其他公众号"))

    elif source == "微信视频号":
        m = re.findall(r'(范校视频号|思格视频号|葛老师视频号)', n)
        if m:
            results.append(("视频号", m[0]))
        else:
            results.append(("视频号", "其他视频号"))

    return results


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
    month_val: str = Query("", description="YYYY-MM"),
    year_val: int = Query(0),
    mode: str = Query("week"),
    db: SqlSession = Depends(get_db),
):
    today = date.today()
    if mode == "month" and month_val:
        parts = month_val.split("-")
        start = date(int(parts[0]), int(parts[1]), 1)
        if int(parts[1]) == 12:
            end = date(int(parts[0]) + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(int(parts[0]), int(parts[1]) + 1, 1) - timedelta(days=1)
    elif mode == "year" and year_val:
        start = date(year_val, 1, 1)
        end = date(year_val, 12, 31)
    elif week_val:
        start = date.fromisoformat(week_val)
        end = start + timedelta(days=6)
    else:
        start, end = _last_week_range(today)
        start = start - timedelta(days=7)
        end = end - timedelta(days=7)

    rows = db.query(Lead).filter(Lead.date >= start, Lead.date <= end).all()
    total = len(rows)
    valid = sum(1 for r in rows if r.validity == "有效")
    invalid = sum(1 for r in rows if r.validity == "无效")
    pending = sum(1 for r in rows if r.validity == "待定")

    by_source = defaultdict(int)
    by_validity = defaultdict(int)
    by_region = defaultdict(int)
    by_day = defaultdict(int)
    intent_dist = defaultdict(int)
    sub_douyin = defaultdict(int)
    sub_gzh = defaultdict(int)
    sub_shipin = defaultdict(int)
    # 渠道×有效性、地区×有效性 交叉分析 + 意向级别 1/3/5 统计
    src_valid = defaultdict(lambda: {"有效": 0, "无效": 0, "待定": 0, "total": 0, "intent1": 0, "intent3": 0, "intent5": 0})
    reg_valid = defaultdict(lambda: {"有效": 0, "无效": 0, "待定": 0, "total": 0, "intent1": 0, "intent3": 0, "intent5": 0})

    for r in rows:
        by_source[r.source or "其他"] += 1
        by_validity[r.validity or "待定"] += 1
        by_region[r.owner or "未知"] += 1
        intent_dist[r.intent or 0] += 1
        by_day[r.date.isoformat()] += 1

        note = r.note or ""
        v = r.validity or "待定"
        it = r.intent or 0

        # 渠道按备注细分：优先取第一个细分结果（保持与线索总数一致）
        subs = _parse_sub_source(r.source, note)
        chan = subs[0][1] if subs else (r.source or "其他")

        src_valid[chan][v] += 1
        src_valid[chan]["total"] += 1
        if it == 1:
            src_valid[chan]["intent1"] += 1
        elif it == 3:
            src_valid[chan]["intent3"] += 1
        elif it == 5:
            src_valid[chan]["intent5"] += 1

        reg_valid[r.owner or "未知"][v] += 1
        reg_valid[r.owner or "未知"]["total"] += 1
        if it == 1:
            reg_valid[r.owner or "未知"]["intent1"] += 1
        elif it == 3:
            reg_valid[r.owner or "未知"]["intent3"] += 1
        elif it == 5:
            reg_valid[r.owner or "未知"]["intent5"] += 1

        for cat, val in subs:
            if cat == "抖音":
                sub_douyin[val] += 1
            elif cat == "公众号":
                sub_gzh[val] += 1
            elif cat == "视频号":
                sub_shipin[val] += 1

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
        "by_source": [{"name": k, "count": v} for k, v in sorted(by_source.items(), key=lambda x: -x[1])],
        "by_validity": dict(by_validity),
        "by_region": [{"name": k, "count": v} for k, v in sorted(by_region.items(), key=lambda x: -x[1])],
        "by_day": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
        "intent_distribution": [{"level": k, "count": v} for k, v in sorted(intent_dist.items())],
        "sub_douyin": [{"name": k, "count": v} for k, v in sorted(sub_douyin.items(), key=lambda x: -x[1])],
        "sub_gzh": [{"name": k, "count": v} for k, v in sorted(sub_gzh.items(), key=lambda x: -x[1])],
        "sub_shipin": [{"name": k, "count": v} for k, v in sorted(sub_shipin.items(), key=lambda x: -x[1])],
        "by_source_validity": [
            {
                "name": k,
                "valid": v["有效"], "invalid": v["无效"], "pending": v["待定"],
                "total": v["total"],
                "valid_rate": round(v["有效"] / v["total"] * 100, 1) if v["total"] else 0,
                "intent1": v["intent1"], "intent3": v["intent3"], "intent5": v["intent5"],
            }
            for k, v in sorted(src_valid.items(), key=lambda x: -x[1]["total"])
        ],
        "by_region_validity": [
            {
                "name": k,
                "valid": v["有效"], "invalid": v["无效"], "pending": v["待定"],
                "total": v["total"],
                "valid_rate": round(v["有效"] / v["total"] * 100, 1) if v["total"] else 0,
                "intent1": v["intent1"], "intent3": v["intent3"], "intent5": v["intent5"],
            }
            for k, v in sorted(reg_valid.items(), key=lambda x: -x[1]["total"])
        ],
    }


@router.post("/leads/upload")
async def upload_leads(
    file: UploadFile = File(...),
    week_val: str = Query(""),
    month_val: str = Query(""),
    year_val: int = Query(0),
    mode: str = Query("week"),
    db: SqlSession = Depends(get_db),
):
    """上传 Excel，按周/月/年替换：先清空该范围旧数据，再导入新数据。"""
    try:
        import pandas as pd
    except ImportError:
        return {"ok": False, "error": "服务器缺少 pandas"}

    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df = df.where(pd.notna(df), None)
    except Exception as e:
        return {"ok": False, "error": f"Excel解析失败: {str(e)}"}

    # 确定日期范围
    if mode == "month" and month_val:
        parts = month_val.split("-")
        start = date(int(parts[0]), int(parts[1]), 1)
        if int(parts[1]) == 12:
            end = date(int(parts[0]) + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(int(parts[0]), int(parts[1]) + 1, 1) - timedelta(days=1)
    elif mode == "year" and year_val:
        start = date(year_val, 1, 1)
        end = date(year_val, 12, 31)
    elif week_val:
        start = date.fromisoformat(week_val)
        end = start + timedelta(days=6)
    else:
        # 默认本周
        start = date.today()
        end = start + timedelta(days=6)

    deleted = db.query(Lead).filter(Lead.date >= start, Lead.date <= end).delete()
    db.commit()

    imported = 0
    for _, r in df.iterrows():
        try:
            phone = str(r.get("手机号") or "")

            date_val = r.get("日期")
            if hasattr(date_val, "strftime"):
                date_str = date_val.strftime("%Y-%m-%d")
            elif week_val:
                date_str = week_val  # 按周上传，无日期用周一
            else:
                date_str = str(date_val or "")

            lead = Lead(
                name=str(r.get("姓名") or ""),
                gender=str(r.get("性别") or "未知"),
                phone=str(r.get("手机号") or ""),
                year=int(r.get("年份") or 2026),
                month=int(r.get("月份") or 8),
                date=date.fromisoformat(date_str) if date_str else date.today(),
                status=STATUS_MAP.get(str(r.get("客户状态") or "").strip(), "跟进中"),
                source=str(r.get("招生来源") or ""),
                validity=str(r.get("客户有效性") or "待定"),
                intent=int(r.get("意向级别") or 0),
                school=str(r.get("公立学校") or ""),
                grade=str(r.get("年级") or ""),
                contact_count=int(r.get("沟通次数") or 0),
                owner=str(r.get("主责任人") or ""),
                note=str(r.get("备注") or ""),
            )
            db.add(lead)
            imported += 1
        except Exception:
            pass

    db.commit()
    return {"ok": True, "imported": imported, "deleted": deleted, "total": len(df)}
