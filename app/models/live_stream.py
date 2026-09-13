"""Live streaming sessions — 手动录入的直播场次数据（直播数据统计）。"""

from sqlalchemy import Column, Integer, String, Date
from .database import Base


class LiveStream(Base):
    __tablename__ = "live_streams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    live_date = Column(Date, nullable=False, comment="直播日期")
    platform = Column(String(20), nullable=False, comment="平台")
    account = Column(String(50), default="", comment="账号（可选）")
    title = Column(String(200), default="", comment="直播主题")
    duration_min = Column(Integer, default=0, comment="时长（分钟）")
    viewers = Column(Integer, default=0, comment="观看人次")
    peak_online = Column(Integer, default=0, comment="峰值在线")
    engagement = Column(Integer, default=0, comment="互动量（评论+点赞+分享）")
    new_followers = Column(Integer, default=0, comment="新增粉丝")
    leads_count = Column(Integer, default=0, comment="留资线索数")
    note = Column(String(500), default="", comment="备注")
