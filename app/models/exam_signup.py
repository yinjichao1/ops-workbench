"""919 模考报名表（exam_signups）—— 与模考服务(sig-exam-backend)共库，此处只读/删除用于统一线索视图。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from .database import Base


class ExamSignup(Base):
    __tablename__ = "exam_signups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    school = Column(String(100), nullable=False, default="")
    grade = Column(String(20), nullable=False, default="")
    score = Column(Float, nullable=False, default=0)
    duration = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
