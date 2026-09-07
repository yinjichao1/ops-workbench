"""团队项目中心辅助 API。

把"团队项目"（如 919 模考排位赛）挂在运营工作台上时使用。
工作台(8001)与模考服务(127.0.0.1:8000)同机部署，这里做服务端代理：

  GET /api/wb/proxy/signups  模考管理页 HTML（改写页内内部接口引用）
  GET /api/wb/proxy/data     模考数据 JSON
  GET /api/wb/proxy/export   模考数据 CSV 导出

安全模型：
- ADMIN_KEY 由工作台读取 /opt/sig-exam-backend/.env（或环境变量 SIG919_ADMIN_KEY），
  只存在于服务器端，绝不进入前端模板 / 浏览器 URL / 仓库。
- 所有端点位于 nginx location /（Basic Auth）之后，仅工作台认证账号可访问。
"""

import os
import urllib.parse
import urllib.request

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

router = APIRouter()

SIG_EXAM_ENV = os.environ.get("SIG_EXAM_ENV", "/opt/sig-exam-backend/.env")
SIG_EXAM_BASE = os.environ.get("SIG_EXAM_BASE", "http://127.0.0.1:8000")


def _sig919_admin_key() -> str:
    """优先环境变量；其次读取模考服务 .env 中的 ADMIN_KEY。"""
    key = os.environ.get("SIG919_ADMIN_KEY", "")
    if key:
        return key
    try:
        with open(SIG_EXAM_ENV, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ADMIN_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:  # noqa: BLE001
        pass
    return ""


def _fetch_exam(path: str) -> bytes:
    """请求本机模考服务；key 由本函数注入，外部调用方完全不感知。"""
    key = _sig919_admin_key()
    if not key:
        raise RuntimeError("未读取到模考管理口令（ADMIN_KEY）")
    url = SIG_EXAM_BASE + path
    sep = "&" if "?" in path else "?"
    url += sep + "key=" + urllib.parse.quote(key)
    req = urllib.request.Request(url, headers={"User-Agent": "ops-workbench"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def _err_response(e: Exception, status: int = 502):
    msg = str(e)[:150]
    if isinstance(e, RuntimeError):
        status = 500
    return JSONResponse(status_code=status, content={"ok": False, "error": msg})


@router.get("/wb/proxy/signups")
def proxy_signups():
    """模考管理页 HTML。页内 JS 原样用 '/api/admin/...?key=' 拼内部接口，
    经代理后浏览器不该持有 key，故改写为指向本代理的同源端点。"""
    try:
        body = _fetch_exam("/api/admin/signups")
    except Exception as e:  # noqa: BLE001
        return _err_response(e)
    html = body.decode("utf-8", errors="replace")
    # 以下改写与 /opt/sig-exam-backend/main.py 的 ADMIN_HTML 对应；若后端模板变动需同步
    html = html.replace(
        "var _key = new URLSearchParams(location.search).get('key') || '';",
        "var _key = ''; /* key 由工作台服务端代理注入，浏览器不持有 */",
    )
    html = html.replace(
        "fetch('/api/admin/data?key=' + _key)",
        "fetch('/api/wb/proxy/data')",
    )
    html = html.replace(
        "location.href='/api/admin/export?key='+new URLSearchParams(location.search).get('key')||''",
        "location.href='/api/wb/proxy/export'",
    )
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/wb/proxy/data")
def proxy_data():
    """模考数据 JSON（原样透传）。"""
    try:
        body = _fetch_exam("/api/admin/data")
    except Exception as e:  # noqa: BLE001
        return _err_response(e)
    return Response(content=body, media_type="application/json")


@router.get("/wb/proxy/export")
def proxy_export():
    """模考数据 CSV 导出（带 UTF-8 BOM，Excel 直接打开不乱码）。"""
    try:
        body = _fetch_exam("/api/admin/export")
    except Exception as e:  # noqa: BLE001
        return _err_response(e)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sig919-signups.csv"'},
    )
