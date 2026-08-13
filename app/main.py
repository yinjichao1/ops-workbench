"""Ops Workbench — FastAPI entry point."""

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .models import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

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
