"""Ops Workbench — FastAPI entry point."""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .models import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="新媒体运营工作台", version="0.1.0")

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Import and register routers
from .routes import dashboard, data, content, tasks, topics, reports  # noqa: E402

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["看板"])
app.include_router(data.router, prefix="/api/data", tags=["数据录入"])
app.include_router(content.router, prefix="/api/content", tags=["内容"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务"])
app.include_router(topics.router, prefix="/api/topics", tags=["选题"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表"])


@app.get("/")
async def index():
    """Serve main SPA page."""
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    return FileResponse(os.path.join(templates_dir, "index.html"))
