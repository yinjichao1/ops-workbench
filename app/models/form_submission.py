"""Form submission model —— 公开表单收集（姓名/手机/学校/专业）。

独立于 leads 表：leads 走「每周 CSV 整段替换」维护，自动收集的表单数据
不进入该替换范围，避免被每周录入覆盖。
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from .database import Base


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), default="", comment="姓名")
    phone = Column(String(20), default="", comment="手机号")
    school = Column(String(100), default="", comment="学校")
    major = Column(String(50), default="", comment="专业")
    page = Column(String(30), default="", comment="来源页面标记，如 timeline28")
    created_at = Column(DateTime, server_default=func.now())
