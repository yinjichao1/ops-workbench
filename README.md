# 思格教育 · 电力央国企简历填写系统

支撑央国企报考服务的付费学员专属简历填写工具。

**方案确认书**：见 `docs/简历系统-方案确认.md`
**部署说明**：见 `部署说明.md`

---

## 业务模型

学员**线下已付费** → 进入本系统**手机号白名单**校验 → 填写简历 → 后台收集 → 导出正式 Word 简历。

**不做在线支付**，登录门槛即为付费墙。

---

## 核心决策（grill-me 5 分支闭合）

| 分支 | 结论 |
|---|---|
| 载体 | 纯 H5 网页，复用 `sigedianwang.cn`，PC 宽屏优先 |
| 登录门槛 | **手机号白名单**，长期有效，一人一份 |
| 后台 | 独立管理页 `/sume/admin` + 管理口令 `sig27ufjaaw` |
| 导出 | **回填原 docx 模板**（24 张表）→ 格式一致的正式简历 |
| 部署 | `sigedianwang.cn/sume/` |

---

## 目录结构

```
resume-system/
├── backend/
│   ├── main.py          FastAPI 入口 · 全部路由
│   ├── db.py            SQLite 数据层（白名单/简历/通知）
│   ├── schema.py        表单字段定义（单一事实来源）
│   ├── docx_export.py   docx 回填引擎
│   ├── notify.py        提交通知（邮件 + 落库）
│   └── config.py        管理口令 / 路径 / 通知配置
├── frontend/
│   ├── index.html       学员端（登录 + 15 模块表单 + 指引抽屉）
│   ├── admin.html       管理端（总览/名单/简历/通知）
│   └── guide.html       指引页
├── templates/简历模板.docx   原 docx 模板（回填基础）
├── storage/
│   ├── photos/          学员上传的证件照/生活照
│   └── exports/         生成的 docx / zip / xlsx
├── data/resume.db       SQLite 数据库
├── 启动.bat             本地一键启动
└── 部署说明.md          服务器部署步骤
```

---

## 本地运行

双击 `启动.bat`，然后访问：
- 学员端 http://127.0.0.1:8901/sume
- 管理端 http://127.0.0.1:8901/sume/admin
- 管理口令 **sig27ufjaaw**

手动启动：
```bash
cd backend
"C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8901
```

---

## 首次使用步骤

1. 打开管理端 `/sume/admin`，用口令登录
2. 到「学员名单」页，添加学员手机号（单个加 或 导入 Excel）
3. 把学员端链接 `sigedianwang.cn/sume` 生成二维码发给学员
4. 学员输手机号进入填写，边填边自动保存
5. 学员点「提交简历」→ 后台「提交通知」出现记录
6. 到「简历列表」查看/导出 Word

---

## 白名单导入格式

| 手机号 | 姓名 | 备注 |
|---|---|---|
| 13800001234 | 张明 | 919购课节 |

首行可为表头（自动跳过），重复号自动去重，格式错的自动跳过。

---

## 导出能力

| 导出 | 说明 |
|---|---|
| 单人 Word | 回填原模板 24 张表，格式一致，含证件照 |
| 批量 Word | 打包 zip，文件名 `姓名_手机号.docx` |
| 简历汇总 Excel | 一人一行，13 个核心字段 |
| 学员名单 Excel | 含填写状态与进度，可用于催缴 |

---

## 技术栈

- 后端：FastAPI + Uvicorn
- 数据库：SQLite（WAL 模式，可平滑迁移 PostgreSQL）
- 文档：python-docx（回填模板）+ openpyxl（Excel 导入导出）
- 鉴权：itsdangerous 签名 token（后台）+ 手机号白名单（学员端）
- 前端：原生 HTML/CSS/JS，零构建步骤

---

## 安全设计

- 管理口令存服务器环境变量，不写前端
- 后台接口全部校验 Bearer Token（12 小时）
- 学员端所有读写都以「手机号在白名单内且未停用」为前提
- 停用（拉黑）后立即失去访问权，适用退费/违规场景
