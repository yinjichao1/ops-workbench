"""Ops Workbench — FastAPI entry point."""

import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .models import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

# 轻量迁移：为已存在的表补充新增列（create_all 不会改已有表）
from sqlalchemy import inspect, text  # noqa: E402


def _migrate_columns():
    insp = inspect(engine)
    if "content_calendar" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("content_calendar")}
        if "account" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE content_calendar ADD COLUMN account VARCHAR(50) DEFAULT ''"))
    if "leads" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("leads")}
        if "campus" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE leads ADD COLUMN campus VARCHAR(50) DEFAULT ''"))
    if "match_leads" in insp.get_table_names():
        # 投放渠道（?ch= 参数）。历史记录保持空串，管理页显示"未标注"。
        cols = {c["name"] for c in insp.get_columns("match_leads")}
        if "platform" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE match_leads ADD COLUMN platform VARCHAR(20) DEFAULT ''"))


def _fix_double_counting():
    """修复历史脏数据：旧版录入 bug 曾把公众号/小红书的阅读量同时写入 plays 字段，
    导致看板播放/阅读 = plays + reads + note_reads 翻倍。
    规范化规则：抖音/视频号→plays；公众号→reads；小红书→note_reads。
    修复时优先"搬家"（把值移到正确字段）而不是直接清零，避免丢数据。幂等，可重复执行。"""
    if "platform_daily_metrics" not in inspect(engine).get_table_names():
        return
    with engine.begin() as conn:
        # 小红书：canonical=note_reads。已有 note_reads 时清掉 plays；没有时把 plays 搬过去（NULL 视为空）
        conn.execute(text(
            "UPDATE platform_daily_metrics SET note_reads = plays, plays = 0 "
            "WHERE platform = '小红书' AND plays > 0 AND (note_reads IS NULL OR note_reads = 0)"
        ))
        conn.execute(text(
            "UPDATE platform_daily_metrics SET plays = 0 "
            "WHERE platform = '小红书' AND plays > 0"
        ))
        # 公众号：canonical=reads
        conn.execute(text(
            "UPDATE platform_daily_metrics SET reads = plays, plays = 0 "
            "WHERE platform = '公众号' AND plays > 0 AND (reads IS NULL OR reads = 0)"
        ))
        conn.execute(text(
            "UPDATE platform_daily_metrics SET plays = 0 "
            "WHERE platform = '公众号' AND plays > 0"
        ))
        # 抖音/视频号：canonical=plays，清掉误写的 reads/note_reads（仅当 plays 有值时，避免丢数据）
        conn.execute(text(
            "UPDATE platform_daily_metrics SET reads = 0, note_reads = 0 "
            "WHERE platform IN ('抖音', '视频号') AND plays > 0 AND (reads > 0 OR note_reads > 0)"
        ))


_migrate_columns()
_fix_double_counting()

app = FastAPI(title="新媒体运营工作台", version="0.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler — no stack trace leaks
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)[:200]})


# 字段中文名（用于 422 提示，让用户看得懂到底哪一栏填错了）。
# 通用名保持中性，避免不同模块同名不同义（如 tasks.title 与 live.title）。
FIELD_LABELS = {
    "live_date": "直播日期", "platform": "平台", "account": "账号",
    "duration_min": "时长（分钟）", "viewers": "观看人次", "peak_online": "峰值在线",
    "engagement": "互动量", "new_followers": "新增粉丝", "leads_count": "留资线索",
    "impressions": "曝光量", "likes": "点赞", "comments": "评论",
    "shares": "分享", "bookmarks": "收藏", "completion_rate": "完播率", "reads": "阅读量",
    "plays": "播放量", "note_reads": "笔记阅读量", "followers": "粉丝数",
    "publish_count": "发布数", "ad_spend": "投放费用",
    "conversion_count": "转化数", "is_viral": "是否爆款", "is_promoted": "是否投流",
    "promote_amount": "投流金额", "target_new_followers": "目标新增粉丝",
    "target_plays_reads": "目标播放/阅读", "target_publish_count": "目标发布数",
    "target_engagement": "目标互动量", "amount": "金额", "year": "年份", "month": "月份",
    "date": "日期", "week": "周次", "start_date": "开始日期", "end_date": "结束日期",
    "phone": "手机号", "school": "学校", "grade": "年级",
    "channel": "渠道", "source": "来源", "report_type": "报表类型", "status": "状态",
    # 中性兜底
    "title": "标题", "name": "名称", "note": "备注", "desc": "说明", "content": "内容",
    "url": "链接", "file": "文件", "id": "编号", "ids": "编号",
}

# 模块专属名称（按路径前缀命中，优先级高于通用名）
SCOPED_LABELS = {
    "/api/live": {"title": "直播主题", "note": "备注", "account": "账号"},
    "/api/tasks": {"title": "任务标题", "desc": "任务说明", "due_date": "截止日期"},
    "/api/topics": {"title": "选题标题", "note": "备注"},
    "/api/content": {"title": "内容标题"},
    "/api/leads": {"amount": "成交金额", "intent": "意向等级"},
}

_ERR_CN = {
    "missing": "未填写",
    "int_from_float": "需要整数（不要填小数）",
    "int_parsing": "需要数字",
    "float_parsing": "需要数字",
    "string_type": "需要文本",
    "date_from_datetime_parsing": "日期格式不对",
    "date_parsing": "日期格式不对",
    "datetime_parsing": "时间格式不对",
    "list_type": "需要是列表",
    "dict_type": "格式不对",
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """把 FastAPI 的英文校验错误转成一句看得懂的中文，并让 detail 保持为字符串。"""
    path = request.url.path
    scope = next((v for k, v in SCOPED_LABELS.items() if path.startswith(k)), {})

    msgs = []
    for err in exc.errors():
        etype = err.get("type", "")
        if etype == "json_invalid":
            msgs.append("提交的数据格式不对，请刷新页面后重试")
            continue
        loc = [str(x) for x in (err.get("loc") or []) if x not in ("body", "query", "path")]
        field = ".".join(loc) or "提交内容"
        # 自定义校验器（如 live 的数字校验）已经给了中文原文，直接用
        if etype == "value_error":
            raw = (err.get("msg") or "").replace("Value error, ", "").strip()
            msgs.append(raw or f"{field} 填写有误")
            continue
        key = field.split(".")[-1]
        label = scope.get(key) or FIELD_LABELS.get(key) or field
        if etype == "missing":
            msgs.append(f"「{label}」未填写")
            continue
        reason = _ERR_CN.get(etype)
        if not reason:
            if etype.startswith("int_") or etype.startswith("float_"):
                reason = "需要填写数字（可填小数）"
            elif etype.startswith("string_too"):
                reason = "长度不符合要求"
            else:
                reason = "填写有误"
        msgs.append(f"「{label}」{reason}")
    detail = "；".join(dict.fromkeys(msgs)) or "提交内容格式有误"
    return JSONResponse(status_code=422, content={"detail": detail})

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Import and register routers
from .routes import dashboard, data, content, tasks, topics, reports, targets, export_data, leads, batch, forms, projects, live, match_routes, collect_routes  # noqa: E402

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["看板"])
app.include_router(data.router, prefix="/api/data", tags=["数据录入"])
app.include_router(content.router, prefix="/api/content", tags=["内容"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务"])
app.include_router(topics.router, prefix="/api/topics", tags=["选题"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表"])
app.include_router(targets.router, prefix="/api", tags=["目标"])
app.include_router(export_data.router, prefix="/api", tags=["导出"])
app.include_router(leads.router, prefix="/api", tags=["线索"])
app.include_router(batch.router, prefix="/api", tags=["批量导入"])
app.include_router(forms.router, prefix="/api", tags=["表单收集"])
app.include_router(projects.router, prefix="/api", tags=["团队项目"])
app.include_router(live.router, prefix="/api", tags=["直播数据"])
app.include_router(collect_routes.router, prefix="/api", tags=["Collect"])
app.include_router(match_routes.router, prefix="/api", tags=["Match tool"])


@app.get("/")
async def index():
    """Serve main SPA page. HTML 永不缓存，静态资源由 ?v= 版本号控制缓存。"""
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    return FileResponse(
        os.path.join(templates_dir, "index.html"),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/forms")
async def forms_admin():
    """公开表单收集管理页（位于工作台 Basic Auth 之后）。"""
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    return FileResponse(
        os.path.join(templates_dir, "forms.html"),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/team-projects")
async def team_projects():
    """团队项目模块页：集中挂接面向学员/员工的线上项目入口与数据管理（Basic Auth 之后）。"""
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    return FileResponse(
        os.path.join(templates_dir, "team_projects.html"),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
