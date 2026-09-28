"""
表单字段定义 · 单一事实来源
前端渲染表单、后端计算填写进度、docx 回填都基于此定义。
"""

MODULES = [
    {
        "key": "basic",
        "title": "1.1 基本信息",
        "required": True,
        "type": "group",
        "fields": [
            {"key": "name", "label": "姓名", "type": "text", "required": True, "tip": "必须与身份证一致"},
            {"key": "gender", "label": "性别", "type": "radio", "options": ["男", "女"]},
            {"key": "birth", "label": "出生年月", "type": "month"},
            {"key": "ethnic", "label": "民族", "type": "text", "tip": "如：汉族"},
            {"key": "political", "label": "政治面貌", "type": "select",
             "options": ["群众", "共青团员", "中共预备党员", "中共党员"]},
            {"key": "join_party", "label": "入党时间", "type": "month", "tip": "党员填写，如 2024.06"},
            {"key": "native_place", "label": "籍贯", "type": "text", "tip": "如：山东青岛"},
            {"key": "phone", "label": "手机号", "type": "text", "readonly": True, "tip": "登录手机号，不可修改"},
            {"key": "email", "label": "邮箱", "type": "text"},
            {"key": "id_card", "label": "身份证号", "type": "text", "required": True, "tip": "国网提交后不可改"},
            {"key": "hukou", "label": "户口性质", "type": "radio", "options": ["农业", "非农业"]},
            {"key": "residence", "label": "现居住地", "type": "text"},
            {"key": "overseas", "label": "是否留学生", "type": "radio", "options": ["否", "是"]},
            {"key": "address", "label": "通信地址", "type": "text"},
            {"key": "marriage", "label": "婚姻状况", "type": "radio", "options": ["未婚", "已婚"]},
            {"key": "courses", "label": "主修课程（3-5门）", "type": "textarea", "rows": 2, "full": True},
            {"key": "research", "label": "研究方向/导师（研究生填）", "type": "text", "full": True},
        ],
        "uploads": [
            {"key": "id_photo", "label": "证件照", "tip": "蓝底正装一寸照（国网/南网/华能等均要求）"},
            {"key": "life_photo", "label": "生活照", "tip": "清晰自然生活照（国家电投要求最多6张，每张≤10MB）"},
        ],
    },
    {
        "key": "education",
        "title": "1.2 教育背景",
        "subtitle": "从高中开始，学历从高到低",
        "type": "table",
        "rows": [
            {"key": "stage", "label": "最高学历", "fixed": "最高学历", "tip": "如：硕士 / 本科"},
            {"key": "stage", "label": "本科/大专", "fixed": "本科/大专"},
            {"key": "stage", "label": "高中", "fixed": "高中"},
        ],
        "columns": [
            {"key": "school", "label": "学校全称", "type": "text"},
            {"key": "major", "label": "专业", "type": "text"},
            {"key": "period", "label": "起止时间", "type": "text", "tip": "如 2022.09-2026.06"},
            {"key": "fulltime", "label": "学习形式", "type": "checkbox", "checkbox_label": "全日制"},
            {"key": "student_no", "label": "学号/学籍状态", "type": "text"},
            {"key": "gpa", "label": "GPA", "type": "text", "tip": "低于3.0可不填"},
            {"key": "rank", "label": "排名", "type": "text", "tip": "格式 15/120"},
        ],
        "tip": "华能/华电从高中开始填；排名格式「15/120」；GPA<3.0 可不填",
    },
    {
        "key": "internships",
        "title": "1.3 实习 / 工作经历",
        "type": "repeater",
        "min": 0, "max": 6,
        "tip": "写「做了什么 + 结果」，用量化数据；不要只写「负责巡检」",
        "fields": [
            {"key": "company", "label": "单位全称", "type": "text"},
            {"key": "position", "label": "部门/岗位", "type": "text"},
            {"key": "period", "label": "起止时间", "type": "text"},
            {"key": "location", "label": "工作地点", "type": "text"},
            {"key": "duties", "label": "主要工作", "type": "textarea", "rows": 3, "placeholder": "1.\n2.\n3."},
            {"key": "achievements", "label": "工作成果", "type": "textarea", "rows": 2, "placeholder": "量化数据：如完成XX、提升XX%"},
        ],
    },
    {
        "key": "projects",
        "title": "1.4 项目经历",
        "type": "repeater",
        "min": 0, "max": 6,
        "tip": "没真实项目就写课程设计/竞赛/大创；重点写你做了什么",
        "fields": [
            {"key": "name", "label": "项目名称", "type": "text"},
            {"key": "role", "label": "担任角色", "type": "text"},
            {"key": "period", "label": "起止时间", "type": "text"},
            {"key": "scale", "label": "项目规模", "type": "text"},
            {"key": "desc", "label": "项目描述", "type": "textarea", "rows": 3, "placeholder": "项目背景 + 你负责什么"},
            {"key": "result", "label": "项目成果", "type": "textarea", "rows": 2, "placeholder": "量化成果"},
        ],
    },
    {
        "key": "student_leaders",
        "title": "1.5 学生干部经历",
        "type": "repeater", "min": 0, "max": 5,
        "fields": [
            {"key": "title", "label": "职务", "type": "text"},
            {"key": "org", "label": "单位/社团", "type": "text"},
            {"key": "period", "label": "起止时间", "type": "text"},
            {"key": "duty", "label": "主要工作/成果", "type": "text"},
        ],
    },
    {
        "key": "practices",
        "title": "1.6 社会实践经历",
        "type": "repeater", "min": 0, "max": 5,
        "fields": [
            {"key": "name", "label": "实践名称", "type": "text"},
            {"key": "org", "label": "实践单位", "type": "text"},
            {"key": "period", "label": "起止时间", "type": "text"},
            {"key": "content", "label": "主要内容/成果", "type": "text"},
        ],
    },
    {
        "key": "languages",
        "title": "1.7 外语水平",
        "subtitle": "国网/南网/大唐单独模块",
        "type": "repeater", "min": 0, "max": 5,
        "tip": "外语和计算机是两个独立模块，国网/南网分开填；成绩写具体分数",
        "fields": [
            {"key": "exam", "label": "考试名称", "type": "text", "placeholder": "CET-4 / CET-6"},
            {"key": "score", "label": "成绩/等级", "type": "text"},
            {"key": "issuer", "label": "颁发机构", "type": "text", "placeholder": "教育部考试中心"},
            {"key": "date", "label": "考试时间", "type": "text"},
            {"key": "remark", "label": "备注", "type": "text", "placeholder": "没有填「无」"},
        ],
    },
    {
        "key": "computers",
        "title": "1.8 计算机水平",
        "subtitle": "国网/南网/大唐单独模块",
        "type": "repeater", "min": 0, "max": 5,
        "fields": [
            {"key": "exam", "label": "考试名称", "type": "text", "placeholder": "计算机等级（二级/三级）"},
            {"key": "score", "label": "成绩/等级", "type": "text"},
            {"key": "issuer", "label": "颁发机构", "type": "text", "placeholder": "教育部考试中心"},
            {"key": "date", "label": "考试时间", "type": "text"},
            {"key": "remark", "label": "备注", "type": "text", "placeholder": "没有填「无」"},
        ],
    },
    {
        "key": "certificates",
        "title": "1.9 资格证书 / 职业资格",
        "type": "repeater", "min": 0, "max": 6,
        "tip": "专业证书≠荣誉证书！电工证填这里，奖学金填下一项",
        "fields": [
            {"key": "name", "label": "证书名称", "type": "text"},
            {"key": "level", "label": "等级", "type": "text"},
            {"key": "issuer", "label": "颁发机构", "type": "text"},
            {"key": "no", "label": "证书编号", "type": "text"},
            {"key": "date", "label": "获得时间", "type": "text"},
            {"key": "remark", "label": "备注", "type": "text", "placeholder": "没有填「无」"},
        ],
    },
    {
        "key": "awards",
        "title": "1.10 获奖情况 / 荣誉奖励",
        "type": "repeater", "min": 0, "max": 6,
        "tip": "南网最多填3项倒序；写清颁奖单位和等级",
        "fields": [
            {"key": "name", "label": "奖项名称", "type": "text"},
            {"key": "issuer", "label": "颁奖单位", "type": "text"},
            {"key": "level", "label": "等级/名次", "type": "text"},
            {"key": "date", "label": "获奖时间", "type": "text"},
            {"key": "remark", "label": "备注", "type": "text"},
        ],
    },
    {
        "key": "academics",
        "title": "1.11 学术成果：论文 / 专利 / 科研项目",
        "type": "repeater", "min": 0, "max": 5,
        "tip": "没有论文专利填「无」",
        "fields": [
            {"key": "type", "label": "类型", "type": "select", "options": ["论文", "专利", "科研项目", "其他"]},
            {"key": "name", "label": "名称", "type": "text"},
            {"key": "journal", "label": "发表/授权刊物", "type": "text"},
            {"key": "date", "label": "时间", "type": "text"},
            {"key": "rank", "label": "排名/角色", "type": "text", "placeholder": "如 第2作者"},
        ],
    },
    {
        "key": "teachings",
        "title": "1.11b 教学经历",
        "subtitle": "华电第2模块；无则填无",
        "type": "repeater", "min": 0, "max": 5,
        "fields": [
            {"key": "course", "label": "课程名称", "type": "text"},
            {"key": "audience", "label": "授课对象", "type": "text"},
            {"key": "period", "label": "起止时间", "type": "text"},
            {"key": "hours", "label": "学时/任务", "type": "text"},
        ],
    },
    {
        "key": "hobbies",
        "title": "1.12 爱好特长 / 个人技能兴趣",
        "type": "single_textarea",
        "placeholder": "如：运动、写作、驾驶（C1）、乐器等；没有填「无」",
        "tip": "爱好特长国家能源/华能必填",
    },
    {
        "key": "family",
        "title": "1.13 家庭背景",
        "type": "family",
        "rows": [
            {"key": "father", "label": "父亲"},
            {"key": "mother", "label": "母亲"},
            {"key": "spouse", "label": "配偶"},
        ],
        "columns": [
            {"key": "name", "label": "姓名"},
            {"key": "company", "label": "工作单位"},
            {"key": "position", "label": "职务"},
            {"key": "political", "label": "政治面貌"},
        ],
        "tip": "华能填「四类关系」；国家电投填亲属任职；没有填「无」",
    },
    {
        "key": "intention",
        "title": "1.14 求职意向与网申补充",
        "type": "group",
        "tip": "接受基层增加录取机会；挂科/处分如实填不要隐瞒",
        "fields": [
            {"key": "target", "label": "应聘单位/岗位", "type": "text", "full": True},
            {"key": "location", "label": "期望工作地点", "type": "text"},
            {"key": "exam_city", "label": "首选考试城市", "type": "text"},
            {"key": "adjust", "label": "是否服从调剂", "type": "radio", "options": ["服从", "不服从"]},
            {"key": "grassroots", "label": "是否接受基层/偏远地区", "type": "radio", "options": ["接受", "看单位", "不接受"]},
            {"key": "postgrad", "label": "是否考研/考博", "type": "radio", "options": ["直接就业", "已考研", "已保研"]},
            {"key": "abroad", "label": "近期是否出国留学", "type": "radio", "options": ["否", "是"]},
            {"key": "other", "label": "其他情况说明", "type": "textarea", "rows": 2, "full": True, "placeholder": "无填「无」"},
        ],
    },
    {
        "key": "self_eval",
        "title": "1.15 自我评价",
        "type": "single_textarea",
        "max_len": 200,
        "placeholder": "三段式：①专业能力 ②性格特质 ③职业意愿",
        "tip": "不要写「性格开朗积极向上」空话；技术岗突出严谨",
    },
]


def flatten_field_keys():
    """返回所有可计数的字段 key 路径，用于计算填写进度"""
    keys = []

    def walk_group(prefix, fields):
        for f in fields:
            keys.append(f"{prefix}.{f['key']}")

    for m in MODULES:
        k = m["key"]
        t = m["type"]
        if t == "group":
            walk_group(k, m["fields"])
            for u in m.get("uploads", []):
                keys.append(f"{k}.{u['key']}")
        elif t == "table":
            for i, _ in enumerate(m["rows"]):
                for c in m["columns"]:
                    keys.append(f"{k}.rows.{i}.{c['key']}")
        elif t == "repeater":
            keys.append(f"{k}.items")
        elif t == "single_textarea":
            keys.append(f"{k}.value")
        elif t == "family":
            for i, _ in enumerate(m["rows"]):
                for c in m["columns"]:
                    keys.append(f"{k}.rows.{i}.{c['key']}")
            keys.append(f"{k}.has_relative")
    return keys


CORE_KEYS = [
    "basic.name", "basic.phone", "basic.id_card", "basic.email",
    "basic.gender", "basic.political", "basic.ethnic", "basic.birth",
    "education.rows.0.school", "education.rows.0.major", "education.rows.0.period",
    "education.rows.0.gpa",
    "basic.courses", "intention.target", "intention.exam_city",
    "intention.adjust", "intention.grassroots", "self_eval.value",
    "internships.items", "projects.items",
]


def _get(data, path):
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def calc_progress(data: dict) -> int:
    """核心字段完成度 0-100"""
    if not isinstance(data, dict):
        return 0
    hit = 0
    for k in CORE_KEYS:
        v = _get(data, k)
        if isinstance(v, list) and len(v) > 0:
            hit += 1
        elif isinstance(v, str) and v.strip():
            hit += 1
        elif isinstance(v, (int, float)) and v:
            hit += 1
    return int(round(hit / len(CORE_KEYS) * 100))
