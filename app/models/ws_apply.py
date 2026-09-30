"""网申模拟系统数据模型。

与 leads / match_leads / form_submissions 完全隔离：
- ws_archives       每次提交一份完整档案（JSON 快照 + 摘要字段）
- ws_archive_items  多行明细子表（教育经历/家庭成员等逐行落库，便于统计）
线索摘要同步写 leads 表（source="网申模拟"），由路由层负责。
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from .database import Base


class WsArchive(Base):
    __tablename__ = "ws_archives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # ── 摘要字段（从档案提取，便于列表/搜索，免解析 JSON）──
    name = Column(String(50), default="", comment="姓名")
    phone = Column(String(20), default="", comment="手机号")
    email = Column(String(100), default="", comment="邮箱")
    school = Column(String(100), default="", comment="最高学历院校")
    major = Column(String(100), default="", comment="最高学历专业")
    level = Column(String(20), default="", comment="最高学历层次，如 本科/硕士")
    grad_date = Column(String(20), default="", comment="毕业时间（原样字符串）")
    # ── 体检报告结果快照 ──
    score = Column(Integer, default=0, comment="体检评分 0-100")
    hard_count = Column(Integer, default=0, comment="硬伤数")
    risk_count = Column(Integer, default=0, comment="风险数")
    tip_count = Column(Integer, default=0, comment="提示数")
    complete_pct = Column(Integer, default=0, comment="完整度 %")
    # ── 渠道与风控 ──
    source = Column(String(30), default="ws-tool", comment="来源标记")
    platform = Column(String(20), default="", comment="投放渠道代号，来自 ?ch=")
    ip = Column(String(45), default="", comment="提交IP，用于风控")
    # ── 完整档案（附件 base64 已剥离，证件照保留）──
    archive_json = Column(Text, default="", comment="完整档案 JSON 快照")

    created_at = Column(DateTime, server_default=func.now())


class WsArchiveItem(Base):
    """多行明细子表：一行 = 档案里某个多行模块的一行记录。

    section 取值：education/family/language/computer/certificate/
                 practice/paper/research/award/attachment
    data_json 为该行字段的 JSON（键与前端 EMPTY_DATA 对应数组的元素一致）。
    """
    __tablename__ = "ws_archive_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    archive_id = Column(Integer, nullable=False, index=True, comment="所属档案 id")
    section = Column(String(20), nullable=False, comment="模块标识")
    sort = Column(Integer, default=0, comment="行序号（从 0 开始）")
    data_json = Column(Text, default="", comment="该行字段 JSON")

    created_at = Column(DateTime, server_default=func.now())
