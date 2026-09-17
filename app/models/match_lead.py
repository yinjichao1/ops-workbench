"""岗位匹配工具留资模型。

独立于 leads（每周 CSV 整段替换）与 form_submissions（落地页门控），
专存 /match/ 工具的考生留资，含学历/意向地区/匹配数等匹配专用字段。
"""
from sqlalchemy import Column, Integer, String, DateTime, func
from .database import Base


class MatchLead(Base):
    __tablename__ = "match_leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), default="", comment="姓名")
    phone = Column(String(20), default="", comment="手机号")
    school = Column(String(100), default="", comment="就读院校")
    major = Column(String(100), default="", comment="所学专业")
    degree_level = Column(Integer, default=0, comment="学历层次 2大专/3本科/4硕士/5博士")
    degree_label = Column(String(20), default="", comment="学历中文名")
    grad_year = Column(String(10), default="", comment="毕业年份")
    province = Column(String(20), default="", comment="意向工作地区")
    group = Column(String(50), default="", comment="招聘集团，如国家能源集团")
    season = Column(String(50), default="", comment="招聘届次，如2027届校园招聘")
    match_total = Column(Integer, default=0, comment="匹配到的岗位数")
    match_exact = Column(Integer, default=0, comment="完全符合数")
    match_family = Column(Integer, default=0, comment="基本符合数")
    match_review = Column(Integer, default=0, comment="需人工确认数")
    source = Column(String(30), default="match-tool", comment="来源标记")
    # ⚠️ 与 collect_routes 的 channel 不是一回事：
    #   channel = 收集入口（form / match / exam）
    #   platform = 投放平台（这条线索是从哪个平台来的），来自入口链接的 ?ch= 参数
    platform = Column(String(20), default="", comment="投放平台渠道代号，如 douyin/shipinhao/gzh/xhs")
    ip = Column(String(45), default="", comment="提交IP，用于风控")
    created_at = Column(DateTime, server_default=func.now())
