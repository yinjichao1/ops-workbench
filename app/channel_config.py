"""渠道分类配置（v2，2026-10-31 与主管确认）。

设计要点：
- 一级渠道 source 为标准枚举，别名在录入/导入时归一（normalize_source）。
- 二级细分渠道 sub_source 为必填白名单，抖音/视频号/公众号不设"其他"；
  备注能识别账号的自动分类（classify_sub_source），识别不了的落"未标注"，
  由运营在 Excel 中补齐后重新上传。
- 公众号官方号唯一，二级按投放位分三类：线索收集工具 / 社群引流 / 表单咨询。
"""

# 一级渠道 → 二级细分白名单（空列表 = 该渠道不设二级）
CHANNEL_TREE = {
    "抖音": ["葛老师抖音号", "范校抖音号", "思格教育抖音号", "电气人抖音号", "未标注"],
    "微信视频号": ["范校视频号", "葛老师视频号", "思格视频号", "未标注"],
    "微信公众号": ["线索收集工具", "社群引流", "表单咨询", "未标注"],
    "小红书": ["题库课程购买", "笔记咨询"],
    "微信私域社群/个人": ["社群", "员工个人微信", "老学员转介绍"],
    "本地生活平台": ["高德地图", "美团/点评"],
    "网申模拟": [],
    "AI搜索/智能问答": [],
    "小程序": [],
    "线下市场活动": [],
    "退学转入": [],
    "其他渠道": [],
}

NO_SUB_SOURCES = {k for k, v in CHANNEL_TREE.items() if not v}

# 来源别名 → 标准一级渠道（按备注内容动态判断的放 normalize_source 里处理）
_SOURCE_ALIAS = {
    "小红书平台": "小红书",
    "线上—活动": "微信公众号",        # 备注全为五一直播课等公众号活动
    "其他新媒体平台": "微信公众号",
    "市场活动-其他": "线下市场活动",
    "市场活动-宣讲会": "线下市场活动",
    "社群转化": "微信私域社群/个人",
    "小程序-直接进入": "小程序",
    "小程序-社群分享·模考": "小程序",
    "小程序-直接进入·模考": "小程序",
}


def normalize_source(source: str, note: str = "") -> str:
    """来源别名归一：按备注内容判断线上—* 类混记来源，其余查静态映射。"""
    s = (source or "").strip()
    n = note or ""
    if s == "线上—新媒体平台":
        if "小红书" in n:
            return "小红书"
        if "抖音" in n:
            return "抖音"
        if "视频号" in n:
            return "微信视频号"
        if "豆包" in n or "AI" in n or "deepseek" in n.lower():
            return "AI搜索/智能问答"
        return "微信公众号"  # 实测备注全为公众号活动（抽奖/模考/进群领资料）
    if s == "线上—短视频平台":
        if "抖音" in n:
            return "抖音"
        if "豆包" in n or "AI" in n or "deepseek" in n.lower():
            return "AI搜索/智能问答"
        if "公众号" in n:
            return "微信公众号"
        return "其他渠道"
    return _SOURCE_ALIAS.get(s, s or "其他渠道")


def classify_sub_source(source: str, note: str) -> str:
    """按备注自动分类二级细分渠道；识别不了返回"未标注"。"""
    s = (source or "").strip()
    n = note or ""

    def _first(*keywords, sub):
        return sub if any(k in n for k in keywords) else None

    if s == "抖音":
        for kw, sub in (
            (("电气人",), "电气人抖音号"),
            (("葛老师", "安哥"), "葛老师抖音号"),
            (("范校", "老范"), "范校抖音号"),
            (("思格教育抖音", "思格抖音", "思格电网抖音", "思格私信", "思格教育私信", "思格电网私信"), "思格教育抖音号"),
        ):
            r = _first(*kw, sub=sub)
            if r:
                return r
        return "未标注"

    if s == "微信视频号":
        for kw, sub in (
            (("范校",), "范校视频号"),
            (("葛老师",), "葛老师视频号"),
            (("思格",), "思格视频号"),
        ):
            r = _first(*kw, sub=sub)
            if r:
                return r
        return "未标注"

    if s == "微信公众号":
        # 优先级：工具留资 → 购买/咨询表单 → 社群/活动引流
        if any(k in n for k in ("匹配工具", "岗位匹配", "专业匹配", "央国企岗位匹配",
                                 "录用信息查询", "录用查询", "查询系统", "网申模拟",
                                 "输入学校名")):
            return "线索收集工具"
        if any(k in n for k in ("购买", "拼团", "刷题版", "考生回忆版", "咨询",
                                 "企业微信", "企微", "表单")):
            return "表单咨询"
        if any(k in n for k in ("进群", "领取", "资料包", "模考", "大赛", "打卡",
                                 "抽奖", "直播", "活动", "公告预约", "分数线",
                                 "预约", "福利", "十周年")):
            return "社群引流"
        return "未标注"

    if s == "小红书":
        if "购买" in n:
            return "题库课程购买"
        if "咨询" in n or n:
            return "笔记咨询"
        return "笔记咨询"

    if s == "微信私域社群/个人":
        if any(k in n for k in ("转介绍", "介绍", "推荐")):
            return "老学员转介绍"
        if any(k in n for k in ("格格微信", "企业微信", "企微", "微信咨询", "微信：", "微信:")):
            return "员工个人微信"
        return "社群"

    if s == "本地生活平台":
        if "美团" in n or "点评" in n:
            return "美团/点评"
        if "高德" in n:
            return "高德地图"
        return "未标注"

    return ""
