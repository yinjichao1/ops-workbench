"""
提交通知模块
学员提交简历后，生成通知记录；支持通过 SMTP 发送邮件给主管。

设计原则：通知失败绝不影响学员提交。先落库，再尝试发送。
"""
import json
import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import db
from config import NOTIFY_EMAIL, NOTIFY_ENABLED

# SMTP 配置（如未配置，则只落库不发送）
SMTP_HOST = ""
SMTP_PORT = 465
SMTP_USER = ""
SMTP_PASS = ""


def build_payload(phone: str, name: str, data: dict, resume_id: int) -> dict:
    basic = data.get("basic") or {}
    edu_rows = (data.get("education") or {}).get("rows") or []
    edu = edu_rows[0] if edu_rows else {}
    intent = data.get("intention") or {}
    return {
        "resume_id": resume_id,
        "phone": phone,
        "name": name or basic.get("name") or "（未填姓名）",
        "gender": basic.get("gender", ""),
        "political": basic.get("political", ""),
        "school": edu.get("school", ""),
        "major": edu.get("major", ""),
        "degree": edu.get("stage") or "最高学历",
        "gpa": edu.get("gpa", ""),
        "rank": edu.get("rank", ""),
        "target": intent.get("target", ""),
        "exam_city": intent.get("exam_city", ""),
        "email": basic.get("email", ""),
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def render_text(p: dict) -> str:
    lines = [
        "【思格教育 · 简历提交通知】",
        "",
        f"学员姓名：{p['name']}",
        f"手机号：{p['phone']}",
        f"性别：{p['gender'] or '—'}",
        f"政治面貌：{p['political'] or '—'}",
        f"学校专业：{p['school'] or '—'} · {p['major'] or '—'}",
        f"GPA/排名：{p['gpa'] or '—'} / {p['rank'] or '—'}",
        f"应聘意向：{p['target'] or '—'}",
        f"首选考试城市：{p['exam_city'] or '—'}",
        f"学员邮箱：{p['email'] or '—'}",
        f"提交时间：{p['submitted_at']}",
        "",
        f"请登录后台查看完整简历：/sume/admin",
    ]
    return "\n".join(lines)


def render_html(p: dict) -> str:
    return f"""<div style="font-family:-apple-system,'Microsoft YaHei',sans-serif;max-width:560px">
  <div style="background:#0a69cd;color:#fff;padding:14px 18px;border-radius:8px 8px 0 0;font-size:16px;font-weight:600">
    思格教育 · 简历提交通知
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:14px;border:1px solid #e5e9f0;border-top:none;border-radius:0 0 8px 8px;overflow:hidden">
    <tr><td style="padding:10px 16px;background:#f7f9fc;width:110px;color:#64748b">学员姓名</td><td style="padding:10px 16px;font-weight:600;color:#1e293b">{p['name']}</td></tr>
    <tr><td style="padding:10px 16px;background:#f7f9fc;color:#64748b">手机号</td><td style="padding:10px 16px;color:#1e293b">{p['phone']}</td></tr>
    <tr><td style="padding:10px 16px;background:#f7f9fc;color:#64748b">性别 / 政治面貌</td><td style="padding:10px 16px;color:#1e293b">{p['gender'] or '—'} / {p['political'] or '—'}</td></tr>
    <tr><td style="padding:10px 16px;background:#f7f9fc;color:#64748b">学校 · 专业</td><td style="padding:10px 16px;color:#1e293b">{p['school'] or '—'} · {p['major'] or '—'}</td></tr>
    <tr><td style="padding:10px 16px;background:#f7f9fc;color:#64748b">GPA / 排名</td><td style="padding:10px 16px;color:#1e293b">{p['gpa'] or '—'} / {p['rank'] or '—'}</td></tr>
    <tr><td style="padding:10px 16px;background:#f7f9fc;color:#64748b">应聘意向</td><td style="padding:10px 16px;color:#1e293b">{p['target'] or '—'}</td></tr>
    <tr><td style="padding:10px 16px;background:#f7f9fc;color:#64748b">首选考试城市</td><td style="padding:10px 16px;color:#1e293b">{p['exam_city'] or '—'}</td></tr>
    <tr><td style="padding:10px 16px;background:#f7f9fc;color:#64748b">提交时间</td><td style="padding:10px 16px;color:#1e293b">{p['submitted_at']}</td></tr>
  </table>
  <p style="color:#94a3b8;font-size:12px;margin-top:14px">请登录简历管理后台查看完整简历并导出 Word。</p>
</div>"""


def notify_submission(phone: str, name: str, data: dict, resume_id: int):
    """记录通知 + 尝试发送邮件（失败不影响主流程）"""
    payload = build_payload(phone, name, data, resume_id)
    sent, error = 0, ""

    if NOTIFY_ENABLED and SMTP_HOST and SMTP_USER:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(f"【简历提交】{payload['name']} · {payload['school'] or '未知学校'}", "utf-8")
            msg["From"] = SMTP_USER
            msg["To"] = NOTIFY_EMAIL
            msg.attach(MIMEText(render_text(payload), "plain", "utf-8"))
            msg.attach(MIMEText(render_html(payload), "html", "utf-8"))
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_USER, [NOTIFY_EMAIL], msg.as_string())
            sent = 1
        except Exception as e:
            error = str(e)[:400]
    else:
        error = "邮件通道未配置（已记录待处理）"

    db.notify_log_add(resume_id, phone, payload["name"], payload, sent, error)
    return {"sent": bool(sent), "payload": payload, "error": error}
