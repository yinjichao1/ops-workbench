"""Platform daily metrics table — one row per platform per day."""

from datetime import date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, func, CheckConstraint
from .database import Base


class PlatformDailyMetrics(Base):
    __tablename__ = "platform_daily_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    platform = Column(String(20), nullable=False, index=True)
    account = Column(String(50), default="", index=True, comment="账号名，如'主号''小号1'")

    # --- Common metrics across all platforms ---
    followers = Column(Integer, default=0, comment="粉丝数/关注数")
    likes = Column(Integer, default=0, comment="点赞数")
    comments = Column(Integer, default=0, comment="评论数")
    shares = Column(Integer, default=0, comment="分享/转发数")
    new_followers = Column(Integer, default=0, comment="新增粉丝")
    publish_count = Column(Integer, default=0, comment="发布内容数")

    # --- 抖音 / 视频号 ---
    plays = Column(Integer, default=0, comment="播放量（抖音/视频号）")
    completion_rate = Column(Float, default=0.0, comment="完播率 %（抖音/视频号）")
    ad_spend = Column(Float, default=0.0, comment="投流消耗 元（抖音）")

    # --- 公众号 ---
    reads = Column(Integer, default=0, comment="阅读量（公众号）")
    in_views = Column(Integer, default=0, comment="在看数（公众号）")
    conversion_count = Column(Integer, default=0, comment="转化/引流数（公众号）")

    # --- 小红书 ---
    note_reads = Column(Integer, default=0, comment="笔记阅读量（小红书）")
    bookmarks = Column(Integer, default=0, comment="收藏数（小红书）")
    engagement_rate = Column(Float, default=0.0, comment="互动率 %（小红书）")
    is_viral = Column(Integer, default=0, comment="爆款标记 0/1")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "platform IN ('抖音', '视频号', '公众号', '小红书')",
            name="ck_platform_name",
        ),
    )
