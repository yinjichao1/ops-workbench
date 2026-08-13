"""Content API — detail, calendar."""

import csv
import io
import re
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..models import get_db
from ..models.content import ContentDetail, ContentCalendar

router = APIRouter()


# ---------- Content Detail ----------
class ContentIn(BaseModel):
    platform: str
    publish_date: str
    content_type: str
    title: str
    url: str = ""
    is_promoted: int = 0
    promote_amount: float = 0.0
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    bookmarks: int = 0
    completion_rate: float = 0.0
    reads: int = 0
    conversion_count: int = 0
    is_viral: int = 0
    author: str = ""
    notes: str = ""


class ContentUpdateIn(BaseModel):
    title: Optional[str] = None
    platform: Optional[str] = None
    publish_date: Optional[str] = None
    impressions: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    bookmarks: Optional[int] = None
    completion_rate: Optional[float] = None
    reads: Optional[int] = None
    conversion_count: Optional[int] = None
    is_viral: Optional[int] = None
    author: Optional[str] = None
    notes: Optional[str] = None


@router.get("/detail")
def list_content(
    platform: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    content_type: Optional[str] = None,
    is_viral: Optional[int] = None,
    author: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """查询内容明细列表。"""
    q = db.query(ContentDetail)
    if platform:
        q = q.filter(ContentDetail.platform == platform)
    if start_date:
        q = q.filter(ContentDetail.publish_date >= date.fromisoformat(start_date))
    if end_date:
        q = q.filter(ContentDetail.publish_date <= date.fromisoformat(end_date))
    if content_type:
        q = q.filter(ContentDetail.content_type == content_type)
    if is_viral is not None:
        q = q.filter(ContentDetail.is_viral == is_viral)
    if author:
        q = q.filter(ContentDetail.author == author)

    total = q.count()
    rows = q.order_by(ContentDetail.publish_date.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

    return {
        "data": [
            {c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"}
            | {"id": r.id, "publish_date": str(r.publish_date),
               "created_at": str(r.created_at) if r.created_at else None}
            for r in rows
        ],
        "total": total,
        "page": page,
    }


@router.post("/detail")
def create_content(body: ContentIn, db: Session = Depends(get_db)):
    """录入内容明细。"""
    data = body.model_dump()
    if data.get("publish_date"):
        data["publish_date"] = date.fromisoformat(data["publish_date"])
    record = ContentDetail(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "id": record.id}


@router.put("/detail/{content_id}")
def update_content(content_id: int, body: ContentUpdateIn, db: Session = Depends(get_db)):
    """更新内容表现数据。"""
    record = db.query(ContentDetail).filter(ContentDetail.id == content_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "publish_date" and v:
            v = date.fromisoformat(v)
        setattr(record, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/detail/{content_id}")
def delete_content(content_id: int, db: Session = Depends(get_db)):
    record = db.query(ContentDetail).filter(ContentDetail.id == content_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    db.delete(record)
    db.commit()
    return {"ok": True}


# ---------- Content Import (CSV / Excel 智能导入) ----------
FIELD_ALIASES = {
    "title": ["标题", "内容标题", "内容名称", "标题名称", "标题内容", "title"],
    "publish_date": ["日期", "发布日期", "发布时间", "发博时间", "发布时间点", "发布", "publish_date", "时间"],
    "platform": ["平台", "所属平台", "渠道", "平台名称", "platform"],
    "content_type": ["类型", "内容类型", "形式", "体裁", "content_type"],
    "impressions": ["播放量", "播放", "曝光量", "曝光", "阅读量", "阅读", "浏览量", "浏览", "观看量", "播放/阅读", "impressions"],
    "likes": ["点赞", "点赞量", "获赞", "赞", "点赞数", "likes"],
    "comments": ["评论", "评论量", "评论数", "comments"],
    "shares": ["分享", "转发", "分享量", "转发量", "shares"],
    "bookmarks": ["收藏", "收藏量", "收藏数", "笔记收藏", "bookmarks"],
    "completion_rate": ["完播率", "完播", "播放完成率", "completion_rate"],
    "conversion_count": ["转化", "转化数", "转化量", "线索数", "conversion_count"],
    "is_viral": ["爆款", "是否爆款", "is_viral"],
    "author": ["账号", "作者", "账号名称", "负责人", "博主", "发布账号", "author"],
    "notes": ["备注", "说明", "附注", "notes"],
}

PLATFORM_ALIASES = {
    "抖音": ["抖音", "抖音app", "douyin"],
    "视频号": ["视频号", "微信视频号", "视频号助手", "wechatchannel"],
    "公众号": ["公众号", "微信公众号", "微信公众平台", "gzh", "weixin"],
    "小红书": ["小红书", "小红书app", "xhs", "red"],
}

TYPE_ALIASES = {
    "短视频": ["短视频", "视频", "video", "作品"],
    "图文": ["图文", "图集", "图文内容"],
    "长文章": ["长文章", "文章", "推文", "article"],
    "笔记": ["笔记", "note", "种草"],
}

TYPE_FALLBACK = {"抖音": "短视频", "视频号": "短视频", "公众号": "长文章", "小红书": "笔记"}


def _norm(s):
    return re.sub(r"[\s_\-（）()【】\[\]]", "", str(s).lower())


def _build_field_map(headers):
    """将文件列名归一化后映射到标准字段（精确匹配优先，包含匹配兜底）。"""
    alias = {}
    for field, names in FIELD_ALIASES.items():
        for n in names:
            alias[_norm(n)] = field
    mapping = {}
    used = set()
    for h in headers:
        key = _norm(h)
        field = None
        if key in alias and alias[key] not in used:
            field = alias[key]
        else:
            for n, f in alias.items():
                if n and (n in key or key in n) and f not in used:
                    field = f
                    break
        if field:
            mapping[h] = field
            used.add(field)
    return mapping


def _match_alias(value, table, fallback=None):
    v = _norm(value)
    for canon, keys in table.items():
        for k in keys:
            if k in v or v in k:
                return canon
    return fallback


def _parse_date(v):
    """支持字符串日期 / 时间戳 / Excel 序列号 / 含时间字符串。"""
    if v is None:
        return None
    try:
        import pandas as pd
        if isinstance(v, (pd.Timestamp, datetime)):
            return v.date()
        if isinstance(v, (int, float)):
            if v > 20000:  # Excel 序列号
                return (date(1899, 12, 30) + timedelta(days=int(v)))
            return date.fromtimestamp(int(v))
    except Exception:
        pass
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "-"):
        return None
    s = re.sub(r"\.0$", "", s)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日", "%Y年%m月"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    return None


def _parse_int(v):
    try:
        import pandas as pd
        if pd.isna(v):
            return 0
    except Exception:
        pass
    s = re.sub(r"[^\d.\-]", "", str(v))
    try:
        return int(float(s))
    except ValueError:
        return 0


def _row_to_content(row, mapping, platform_fallback=""):
    """把一行记录转换为 ContentDetail；无法识别标题/平台的行返回 None。"""
    def val(field):
        for col, f in mapping.items():
            if f == field:
                return row[col]
        return None

    title = str(val("title") or "").strip()
    if not title or title.lower() in ("nan", "none"):
        return None
    platform = _match_alias(val("platform"), PLATFORM_ALIASES) or (platform_fallback or None)
    if not platform:
        return None
    content_type = _match_alias(val("content_type"), TYPE_ALIASES) or TYPE_FALLBACK.get(platform, "图文")
    pd_ = _parse_date(val("publish_date")) or date.today()
    viral_raw = _norm(val("is_viral"))
    is_viral = 1 if viral_raw in ("1", "是", "true", "yes", "爆款") else 0
    completion_raw = _parse_int(val("completion_rate"))
    completion_rate = float(completion_raw / 100 if completion_raw > 100 else completion_raw)
    return ContentDetail(
        title=title[:200],
        platform=platform,
        content_type=content_type,
        publish_date=pd_,
        author=str(val("author") or "").strip()[:50],
        impressions=_parse_int(val("impressions")),
        likes=_parse_int(val("likes")),
        comments=_parse_int(val("comments")),
        shares=_parse_int(val("shares")),
        bookmarks=_parse_int(val("bookmarks")),
        completion_rate=completion_rate,
        conversion_count=_parse_int(val("conversion_count")),
        is_viral=is_viral,
        notes=str(val("notes") or "").strip()[:500],
    )


@router.post("/import")
async def import_content(
    file: UploadFile = File(...),
    platform: str = Query("", description="文件无平台列时指定：抖音/视频号/公众号/小红书"),
    db: Session = Depends(get_db),
):
    """上传 CSV / XLSX / XLS，智能识别列名后批量写入内容明细。"""
    contents = await file.read()
    filename = file.filename or ""
    try:
        import pandas as pd
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception:
        return {"ok": False, "error": "文件解析失败，请上传 CSV / XLSX / XLS 格式"}
    if df is None or df.empty:
        return {"ok": False, "error": "文件内容为空"}
    fallback = _match_alias(platform, PLATFORM_ALIASES) or ""
    mapping = _build_field_map(list(df.columns))
    if "title" not in mapping.values():
        return {
            "ok": False,
            "error": "未识别到标题列（已识别列：%s），请下载模板对照格式" % "、".join(mapping.values() or ["无"]),
            "mapping": mapping,
        }
    imported = skipped = 0
    errors = []
    for idx, row in df.iterrows():
        try:
            rec = _row_to_content(row, mapping, fallback)
            if rec is None:
                skipped += 1
                continue
            db.add(rec)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append({"row": idx + 2, "error": str(e)[:80]})
    db.commit()
    return {
        "ok": True,
        "imported": imported,
        "skipped": skipped,
        "total": int(len(df)),
        "errors": errors[:20],
    }


@router.get("/import-template")
def import_template():
    """下载内容明细导入模板（UTF-8 BOM 便于 Excel 打开）。"""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["标题", "日期", "平台", "账号", "类型", "播放量", "点赞", "评论", "分享", "收藏", "完播率", "爆款", "备注"])
    w.writerow(["2026国网二批网申流程全解析", "2026-08-06", "抖音", "思格电网", "短视频", "32000", "1240", "86", "45", "", "28.5", "是", "网申讲解"])
    w.writerow(["备考国网需要多长时间", "2026-08-05", "小红书", "小格", "笔记", "5600", "420", "38", "15", "210", "", "", ""])
    csv_bytes = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=content_import_template.csv"},
    )


# ---------- Content Calendar ----------
class CalendarIn(BaseModel):
    title: str
    platform: str
    content_type: str
    status: str = "待策划"
    scheduled_date: str
    assignee: str = ""
    description: str = ""
    related_topic_id: Optional[int] = None


class CalendarUpdateIn(BaseModel):
    title: Optional[str] = None
    platform: Optional[str] = None
    content_type: Optional[str] = None
    status: Optional[str] = None
    scheduled_date: Optional[str] = None
    assignee: Optional[str] = None
    description: Optional[str] = None
    related_topic_id: Optional[int] = None


@router.get("/calendar")
def list_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """查询排期。默认排除「已发布」状态。"""
    q = db.query(ContentCalendar).filter(ContentCalendar.status != "已发布")
    if start_date:
        q = q.filter(ContentCalendar.scheduled_date >= date.fromisoformat(start_date))
    if end_date:
        q = q.filter(ContentCalendar.scheduled_date <= date.fromisoformat(end_date))
    if platform:
        q = q.filter(ContentCalendar.platform == platform)
    if status:
        q = q.filter(ContentCalendar.status == status)
    rows = q.order_by(ContentCalendar.scheduled_date.asc()).all()
    return {
        "data": [
            {
                "id": r.id,
                "title": r.title,
                "platform": r.platform,
                "content_type": r.content_type,
                "status": r.status,
                "scheduled_date": str(r.scheduled_date),
                "assignee": r.assignee,
                "description": r.description,
                "related_topic_id": r.related_topic_id,
            }
            for r in rows
        ]
    }


@router.post("/calendar")
def create_calendar_entry(body: CalendarIn, db: Session = Depends(get_db)):
    """创建排期条目。"""
    data = body.model_dump()
    data["scheduled_date"] = datetime.strptime(data["scheduled_date"], "%Y-%m-%d").date()
    record = ContentCalendar(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "id": record.id}


@router.put("/calendar/{entry_id}")
def update_calendar_entry(entry_id: int, body: CalendarUpdateIn, db: Session = Depends(get_db)):
    """更新排期状态等。"""
    record = db.query(ContentCalendar).filter(ContentCalendar.id == entry_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "scheduled_date" and v:
            v = date.fromisoformat(v)
        setattr(record, k, v)
    db.commit()

    # 如果状态变成"已发布"，检查关联的任务是否自动完成
    if body.status == "已发布" and record.related_content_id is None:
        from .tasks import _auto_complete_task  # noqa: F811
        _auto_complete_task(db, entry_id)

    return {"ok": True}


@router.delete("/calendar/{entry_id}")
def delete_calendar_entry(entry_id: int, db: Session = Depends(get_db)):
    """删除排期条目。"""
    record = db.query(ContentCalendar).filter(ContentCalendar.id == entry_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    db.delete(record)
    db.commit()
    return {"ok": True}
