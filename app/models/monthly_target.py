"""Monthly KPI targets — user-set goals per platform."""

from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from .database import Base


class MonthlyTarget(Base):
    __tablename__ = "monthly_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    platform = Column(String(20), nullable=False)

    target_new_followers = Column(Integer, default=0, comment="新增粉丝目标")
    target_plays_reads = Column(Integer, default=0, comment="播放/阅读目标")
    target_publish_count = Column(Integer, default=0, comment="发布数量目标")
    target_engagement = Column(Integer, default=0, comment="互动量目标")

    updated_at = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("year", "month", "platform", name="uq_target_month_platform"),
    )