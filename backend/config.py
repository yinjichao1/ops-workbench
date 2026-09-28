"""
电力央国企简历填写系统 · 后端配置
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 管理口令（学员端不涉及，仅后台使用）
ADMIN_PASSWORD = os.environ.get("RESUME_ADMIN_PASSWORD", "sig27ufjaaw")

# 会话签名密钥（用于后台登录 token）
SECRET_KEY = os.environ.get("RESUME_SECRET_KEY", "sigedianwang-resume-2026-hmac-key")

# 数据库
DB_PATH = BASE_DIR / "data" / "resume.db"

# 存储
STORAGE_DIR = BASE_DIR / "storage"
PHOTO_DIR = STORAGE_DIR / "photos"
EXPORT_DIR = STORAGE_DIR / "exports"
TEMPLATE_PATH = BASE_DIR / "templates" / "简历模板.docx"

# 前端静态文件
FRONTEND_DIR = BASE_DIR / "frontend"

# 提交后通知邮箱（发送到该地址）
NOTIFY_EMAIL = os.environ.get("RESUME_NOTIFY_EMAIL", "yinjichao1005@163.com")

# 全局通知开关（父级系统可关闭）
NOTIFY_ENABLED = os.environ.get("RESUME_NOTIFY_ENABLED", "0") == "1"

for d in (DB_PATH.parent, PHOTO_DIR, EXPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)
