"""Task management API."""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..models import get_db
from ..models.content import Task

router = APIRouter()


class TaskIn(BaseModel):
    title: str
    description: str = ""
    assignee: str = ""
    priority: str = "中"
    status: str = "待办"
    due_date: Optional[str] = None
    platform: str = ""
    related_calendar_id: Optional[int] = None


class TaskUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None


def _auto_complete_task(db: Session, calendar_id: int):
    """排期状态变为'已发布'时，自动完成关联任务。"""
    related_tasks = (
        db.query(Task)
        .filter(Task.related_calendar_id == calendar_id, Task.status != "已完成")
        .all()
    )
    for t in related_tasks:
        t.status = "已完成"
    if related_tasks:
        db.commit()


@router.get("")
def list_tasks(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    platform: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """查询任务列表。"""
    q = db.query(Task)
    if status:
        q = q.filter(Task.status == status)
    if assignee:
        q = q.filter(Task.assignee == assignee)
    if platform:
        q = q.filter(Task.platform == platform)
    if priority:
        q = q.filter(Task.priority == priority)

    rows = q.order_by(Task.created_at.desc()).all()
    return {
        "data": [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "assignee": r.assignee,
                "priority": r.priority,
                "status": r.status,
                "due_date": str(r.due_date) if r.due_date else None,
                "platform": r.platform,
                "related_calendar_id": r.related_calendar_id,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]
    }


@router.post("")
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    """创建任务。"""
    data = body.model_dump()
    if data.get("due_date"):
        data["due_date"] = date.fromisoformat(data["due_date"])
    record = Task(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "id": record.id}


@router.put("/{task_id}")
def update_task(task_id: int, body: TaskUpdateIn, db: Session = Depends(get_db)):
    """更新任务状态。"""
    record = db.query(Task).filter(Task.id == task_id).first()
    if not record:
        return {"ok": False, "error": "not found"}
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "due_date" and v:
            v = date.fromisoformat(v)
        setattr(record, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务。"""
    result = db.query(Task).filter(Task.id == task_id).delete()
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.commit()
    return {"ok": True}
