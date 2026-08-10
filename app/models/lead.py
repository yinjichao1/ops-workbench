"""Lead model."""

from sqlalchemy import Column, Integer, String, Date, DateTime, func
from .database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), default="")
    gender = Column(String(10), default="")
    phone = Column(String(20), default="")
    year = Column(Integer, default=0)
    month = Column(Integer, default=0)
    date = Column(Date, nullable=False)
    status = Column(String(20), default="", comment="客户状态: 跟进中/未跟进/无需跟进")
    source = Column(String(20), default="", comment="招生来源: 抖音/微信视频号/微信公众号")
    validity = Column(String(10), default="", comment="客户有效性: 有效/无效/待定")
    intent = Column(Integer, default=0, comment="意向级别 0-3")
    school = Column(String(100), default="")
    grade = Column(String(20), default="")
    contact_count = Column(Integer, default=0, comment="沟通次数")
    owner = Column(String(20), default="", comment="主责任人/地区")
    note = Column(String(500), default="")

    created_at = Column(DateTime, server_default=func.now())