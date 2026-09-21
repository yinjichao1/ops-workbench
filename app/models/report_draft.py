"""Report drafts — 周报/月报的手工编辑稿。

设计：**每个周期只存一份**。报表由系统按数据自动生成，但主管会手工修改内容
（补复盘结论、改措辞、删掉空章节），所以需要把改后的稿子留下来；下次再选到
同一个周期时自动载入已保存的内容，而不是重新生成把修改冲掉。

- report_type: weekly / monthly
- period_start: 周期起点（周报=所在周的周一，月报=该月 1 号），与 report_type 组成唯一键
- content_html: 用户编辑后的正文 HTML（再次打开时直接渲染，所见即所得）
- content_md:   对应的 Markdown 版本（下载 / 复制用）
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .database import Base


class ReportDraft(Base):
    __tablename__ = "report_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(10), nullable=False, comment="weekly / monthly")
    period_start = Column(Date, nullable=False, comment="周期起点：周报=周一，月报=该月 1 号")
    title = Column(String(200), default="", comment="报表标题（列表展示用）")
    content_html = Column(Text, default="", comment="编辑后的正文 HTML")
    content_md = Column(Text, default="", comment="对应的 Markdown（下载/复制用）")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="最后保存时间"
    )

    __table_args__ = (
        UniqueConstraint("report_type", "period_start", name="uq_report_draft_period"),
    )
