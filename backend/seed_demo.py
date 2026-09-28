"""演示数据注入脚本 · 用于预览界面效果（可重复运行，会跳过已存在的手机号）"""
import json
import urllib.request
import sys

B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8903"
PWD = "sig27ufjaaw"


def req(path, data=None, tok=None):
    h = {"Content-Type": "application/json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    r = urllib.request.Request(B + path, data=json.dumps(data).encode() if data else None,
                               headers=h)
    try:
        return json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        return {"_err": e.read().decode()[:160]}


tok = req("/api/admin/login", {"password": PWD})["token"]

for p, n, m in [
    ("13800001234", "张明", "919购课节 · 吉林校区"),
    ("13900002222", "李华", "辽宁校区"),
    ("13700003333", "王强", "黑龙江校区"),
    ("13600004444", "赵敏", "吉林校区"),
    ("13500005555", "孙磊", "内蒙古校区"),
]:
    req("/api/admin/whitelist/add", {"phone": p, "name": n, "remark": m}, tok)

zhangming = {
    "basic": {"name": "张明", "gender": "男", "birth": "2003-05", "ethnic": "汉族",
              "political": "中共党员", "join_party": "2024-06", "native_place": "山东青岛",
              "phone": "13800001234", "email": "zhangming@qq.com",
              "id_card": "370200200305011234", "hukou": "非农业", "residence": "吉林长春",
              "overseas": "否", "address": "吉林省长春市朝阳区XX路XX号", "marriage": "未婚",
              "courses": "电力系统分析、继电保护原理、高电压技术"},
    "education": {"rows": [
        {"school": "东北电力大学", "major": "电气工程及其自动化", "period": "2022.09-2026.06",
         "fulltime": True, "student_no": "2022010101", "gpa": "3.7", "rank": "15/120"},
        {"school": "", "major": "", "period": "", "fulltime": True},
        {"school": "长春市第一中学", "major": "理科", "period": "2019.09-2022.06", "fulltime": True}]},
    "internships": [
        {"company": "国网长春供电公司", "position": "变电检修实习生", "period": "2025.07-2025.09",
         "location": "吉林长春",
         "duties": "1. 跟随师傅完成110kV变电站年度检修，参与8个间隔巡检\n2. 协助整理检修记录30余份，发现2处设备隐患并上报\n3. 学习倒闸操作票填写，参与5次模拟开票",
         "achievements": "参与8个间隔巡检；整理检修记录30余份；发现并上报设备隐患2处"},
        {"company": "长春XX电气设备有限公司", "position": "电气设计助理",
         "period": "2024.07-2024.08", "location": "吉林长春",
         "duties": "协助完成低压配电柜图纸绘制与元件选型", "achievements": "独立完成5套配电柜图纸"}],
    "projects": [
        {"name": "110kV变电站主接线设计", "role": "组长", "period": "2024.09-2024.12",
         "scale": "4人团队", "desc": "完成110kV变电站主接线设计，计算短路电流并完成设备选型",
         "result": "用AutoCAD绘制电气主接线图，答辩获优秀设计"},
        {"name": "大学生创新创业训练项目", "role": "核心成员", "period": "2023.10-2024.06",
         "scale": "校级立项", "desc": "基于单片机的配电网故障监测装置开发",
         "result": "装置原型完成，参与校级结题答辩"}],
    "student_leaders": [{"title": "学习委员", "org": "电气2201班", "period": "2022.09-2024.06",
                         "duty": "负责班级学风建设，组织复习小组，班级平均分提升5分"}],
    "practices": [{"name": "三下乡社会实践", "org": "校团委", "period": "2024.07",
                   "content": "赴乡镇开展用电安全宣传，走访农户60余户"}],
    "languages": [
        {"exam": "CET-6", "score": "480分", "issuer": "教育部考试中心", "date": "2024.12", "remark": ""},
        {"exam": "CET-4", "score": "562分", "issuer": "教育部考试中心", "date": "2023.06", "remark": ""}],
    "computers": [{"exam": "计算机等级二级C语言", "score": "合格",
                   "issuer": "教育部考试中心", "date": "2024.03", "remark": ""}],
    "certificates": [
        {"name": "高压电工作业证", "level": "高压", "issuer": "应急管理局",
         "no": "T3702****1234", "date": "2025.03", "remark": ""},
        {"name": "低压电工作业证", "level": "低压", "issuer": "应急管理局",
         "no": "T3702****5678", "date": "2024.11", "remark": ""}],
    "awards": [
        {"name": "国家励志奖学金", "issuer": "教育部", "level": "国家级", "date": "2024.11", "remark": ""},
        {"name": "校级三好学生", "issuer": "东北电力大学", "level": "校级", "date": "2024.05", "remark": ""},
        {"name": "全国大学生数学建模竞赛", "issuer": "中国工业与应用数学学会",
         "level": "省二等奖", "date": "2024.09", "remark": ""}],
    "academics": [{"type": "论文", "name": "XX变电站接地网优化设计", "journal": "电气技术",
                   "date": "2025.06", "rank": "第2作者"}],
    "teachings": [],
    "hobbies": "篮球（校队主力）、长跑、驾驶（C1）、摄影",
    "family": {"rows": [
        {"name": "张某某", "company": "XX机械制造有限公司", "position": "工程师", "political": "群众"},
        {"name": "李某某", "company": "XX市第一医院", "position": "护士长", "political": "中共党员"}, {}],
        "has_relative": "无", "relative_detail": ""},
    "intention": {"target": "国网吉林省电力有限公司 · 变电检修岗", "location": "吉林省长春市",
                  "exam_city": "长春", "adjust": "服从", "grassroots": "接受",
                  "postgrad": "直接就业", "abroad": "否", "other": "无"},
    "self_eval": "电气工程及其自动化专业，专业排名前15%，在国网长春供电公司完成变电检修实习，"
                 "熟悉110kV变电站巡检流程与倒闸操作规范；性格严谨细致、责任心强，"
                 "能适应倒班与基层工作节奏；愿从基层一线做起，长期扎根电力行业。",
}

lihua = {
    "basic": {"name": "李华", "gender": "女", "birth": "2003-11", "ethnic": "汉族",
              "political": "共青团员", "native_place": "辽宁沈阳", "phone": "13900002222",
              "email": "lihua@qq.com", "hukou": "非农业", "marriage": "未婚",
              "courses": "电机学、电力电子技术"},
    "education": {"rows": [
        {"school": "沈阳工程学院", "major": "电力系统及其自动化", "period": "2022.09-2026.06",
         "fulltime": True, "gpa": "3.5", "rank": "28/150"}]},
    "intention": {"target": "国网辽宁省电力有限公司 · 调度运行岗", "exam_city": "沈阳",
                  "adjust": "服从", "grassroots": "接受"},
    "self_eval": "电力系统及其自动化专业，具备扎实的电力系统理论基础。",
}

wangqiang = {
    "basic": {"name": "王强", "gender": "男", "phone": "13700003333", "ethnic": "汉族"},
    "education": {"rows": [{"school": "哈尔滨工业大学", "major": "电气工程", "period": "2022.09-2026.06"}]},
}

print("白名单:", req("/api/admin/whitelist/add", {"phone": "13800001234", "name": "张明"}, tok))
print("张明:", req("/api/save", {"phone": "13800001234", "data": zhangming, "photos": {}, "status": "submitted"}))
print("李华:", req("/api/save", {"phone": "13900002222", "data": lihua, "photos": {}, "status": "submitted"}))
print("王强:", req("/api/save", {"phone": "13700003333", "data": wangqiang, "photos": {}, "status": "draft"}))
print("统计:", req("/api/admin/stats", None, tok))
print("导出测试:", req("/api/admin/resume/1", None, tok).get("phone", "?"))
