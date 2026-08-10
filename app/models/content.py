"""Content-related models: detail, calendar, tasks, topics."""

from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, func,
    CheckConstraint,
)
from .database import Base


class ContentDetail(Base):
    """每条已发布内容的明细表。"""
    __tablename__ = "content_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(
        String(20), nullable=False, index=True,
    )
    publish_date = Column(Date, nullable=False, index=True)
    content_type = Column(
        String(20),
        nullable=False,
        comment="短视频 / 图文 / 长文章 / 笔记",
    )
    title = Column(String(255), nullable=False)
    url = Column(String(500), default="")
    is_promoted = Column(Integer, default=0, comment="是否投流 0/1")
    promote_amount = Column(Float, default=0.0, comment="投流金额 元")

    # --- Performance ---
    impressions = Column(Integer, default=0, comment="曝光/播放量")
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    bookmarks = Column(Integer, default=0, comment="收藏（小红书）")
    completion_rate = Column(Float, default=0.0, comment="完播率（抖音/视频号）")
    reads = Column(Integer, default=0, comment="阅读量（公众号/小红书）")
    conversion_count = Column(Integer, default=0, comment="转化数（公众号）")
    is_viral = Column(Integer, default=0, comment="爆款标记 0/1")

    author = Column(String(50), default="", comment="负责人")
    notes = Column(Text, default="")

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "platform IN ('抖音', '视频号', '公众号', '小红书')",
            name="ck_content_platform",
        ),
        CheckConstraint(
            "content_type IN ('短视频', '图文', '长文章', '笔记')",
            name="ck_content_type",
        ),
    )


class ContentCalendar(Base):
    """内容排期表。"""
    __tablename__ = "content_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    platform = Column(
        String(20), nullable=False,
    )
    content_type = Column(
        String(20), nullable=False,
    )
    status = Column(
        String(20),
        nullable=False,
        default="待策划",
        comment="待策划 / 制作中 / 待审核 / 待发布 / 已发布",
    )
    scheduled_date = Column(Date, nullable=False, index=True)
    published_date = Column(Date, nullable=True)
    assignee = Column(String(50), default="")
    description = Column(Text, default="")
    related_topic_id = Column(Integer, ForeignKey("topic_ideas.id"), nullable=True)
    related_content_id = Column(Integer, ForeignKey("content_detail.id"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('待策划', '制作中', '待审核', '待发布', '已发布')",
            name="ck_calendar_status",
        ),
    )


class Task(Base):
    """团队任务管理表。"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    assignee = Column(String(50), default="")
    priority = Column(
        String(10),
        nullable=False,
        default="中",
    )
    status = Column(
        String(20),
        nullable=False,
        default="待办",
        comment="待办 / 进行中 / 已完成",
    )
    due_date = Column(Date, nullable=True)
    platform = Column(String(20), default="")
    related_calendar_id = Column(
        Integer, ForeignKey("content_calendar.id"), nullable=True,
        comment="关联排期条目，排期完成后自动同步状态",
    )

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "priority IN ('高', '中', '低')",
            name="ck_task_priority",
        ),
        CheckConstraint(
            "status IN ('待办', '进行中', '已完成')",
            name="ck_task_status",
        ),
    )


class TopicIdea(Base):
    """选题库表。"""
    __tablename__ = "topic_ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    source = Column(
        String(50),
        default="灵感",
        comment="热点 / 竞品 / 灵感 / 活动",
    )
    platforms = Column(
        String(100),
        default="",
        comment="适配平台，逗号分隔：抖音,公众号,小红书,视频号",
    )
    priority = Column(
        String(10),
        nullable=False,
        default="中",
    )
    status = Column(
        String(20),
        nullable=False,
        default="待评估",
        comment="待评估 / 已采纳 / 已发布",
    )
    creator = Column(String(50), default="")
    notes = Column(Text, default="")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "priority IN ('高', '中', '低')",
            name="ck_topic_priority",
        ),
        CheckConstraint(
            "status IN ('待评估', '已采纳', '已发布')",
            name="ck_topic_status",
        ),
    )
