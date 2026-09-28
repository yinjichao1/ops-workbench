"""生成界面预览快照 · 把服务端渲染的 HTML + 演示数据合成为静态文件，方便直接打开查看"""
import json
import pathlib
import sys
import urllib.request

B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8903"
OUT = pathlib.Path(__file__).parent.parent / "preview"
OUT.mkdir(exist_ok=True)


def get(path, tok=None):
    h = {"Authorization": "Bearer " + tok} if tok else {}
    return urllib.request.urlopen(urllib.request.Request(B + path, headers=h)).read().decode("utf-8")


def jget(path, tok=None):
    return json.loads(get(path, tok))


tok = jget("/api/admin/login", None) if False else None
import json as _j
import urllib.request as _u
r = _u.Request(B + "/api/admin/login", data=_j.dumps({"password": "sig27ufjaaw"}).encode(),
               headers={"Content-Type": "application/json"})
tok = _j.load(_u.urlopen(r))["token"]

student_html = get("/sume/")
admin_html = get("/sume/admin")

# 找到「张明」的简历 id（不写死）
items = jget("/api/admin/resumes", tok)["items"]
zm = next((x for x in items if x["phone"] == "13800001234"), items[0] if items else None)
zm_id = zm["id"] if zm else 1

zhangming = jget(f"/api/admin/resume/{zm_id}", tok)

bootstrap = f"""
<script>
window.__DEMO__ = true;
window.__DEMO_DATA__ = {json.dumps(zhangming['data'], ensure_ascii=False)};
window.__DEMO_PHONE__ = "13800001234";
window.__DEMO_NAME__  = "张明";
</script>
"""

# 在 </body> 前插入演示引导脚本：直接进入应用
boot_code = """
<script>
(async function(){
  if(!window.__DEMO__) return;
  // 直接进入应用，跳过登录
  document.getElementById('login').style.display='none';
  document.getElementById('app').style.display='block';
  S.phone = window.__DEMO_PHONE__;
  S.name = window.__DEMO_NAME__;
  S.data = window.__DEMO_DATA__ || {};
  S.photos = {};
  S.status = 'submitted';
  S.progress = 92;
  await loadSchema();
  renderAll();
  setStatus('submitted');
  document.getElementById('progPct').textContent = '92%';
  document.getElementById('progFill').style.width = '92%';
  document.getElementById('saveNote').textContent = '✓ 已于 2026-09-28 15:58 提交';
  document.getElementById('saveNote').className = 'save-note ok';
  toast('演示模式：这是学员填完提交后的样子', 'ok');
})();
</script>
"""

student_out = student_html.replace("</body>", bootstrap + boot_code + "</body>")
(OUT / "预览-学员填写页.html").write_text(student_out, encoding="utf-8")

# 管理端：自动登录并直接展示
admin_boot = f"""
<script>
window.__DEMO_TOKEN__ = {json.dumps(tok)};
window.__DEMO_RID__ = {zm_id};
</script>
<script>
(async function(){{
  TOKEN = window.__DEMO_TOKEN__;
  document.getElementById('login').style.display='none';
  document.getElementById('app').style.display='block';
  await enterApp();
  await openDetail(window.__DEMO_RID__);
}})();
</script>
"""
admin_out = admin_html.replace("</body>", admin_boot + "</body>")
(OUT / "预览-管理后台.html").write_text(admin_out, encoding="utf-8")

# 学员端未登录态（登录页）
(OUT / "预览-学员登录页.html").write_text(student_html, encoding="utf-8")

print("生成完成：")
for f in sorted(OUT.glob("*.html")):
    print("  ", f.name, f.stat().st_size, "bytes")
