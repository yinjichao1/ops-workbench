"""Ops Workbench — FastAPI entry point."""

import os
from fastapi import FastAPI, Request
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

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Import and register routers
from .routes import dashboard, data, content, tasks, topics, reports, targets, export_data, leads, batch  # noqa: E402

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
