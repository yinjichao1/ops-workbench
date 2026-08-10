// ========== EXPORT ==========
function openExportDialog() {
  const mid = "export-" + Date.now();
  const thisWeek = getLastWeek();
  const now = new Date();
  const thisMonth = `${now.getFullYear()}-${String(now.getMonth()).padStart(2,'0')}`;
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:400px">
    <h2>导出数据</h2>
    <div class="form-group"><label>导出维度</label>
      <select id="exp-mode" onchange="document.getElementById('exp-week-grp').style.display=this.value==='week'?'':'none';document.getElementById('exp-month-grp').style.display=this.value==='month'?'':'none'">
        <option value="week">按周</option>
        <option value="month">按月</option>
      </select>
    </div>
    <div class="form-group" id="exp-week-grp"><label>周次</label><input type="week" id="exp-week" value="${thisWeek}"></div>
    <div class="form-group" id="exp-month-grp" style="display:none"><label>月份</label><input type="month" id="exp-month" value="${thisMonth}"></div>
    <div class="form-group"><label>平台（留空=全部）</label>
      <select id="exp-plat"><option value="">全部平台</option>${["抖音","视频号","公众号","小红书"].map(p=>`<option>${p}</option>`).join("")}</select>
    </div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="doExport('${mid}')">下载 CSV</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

function doExport(modalId) {
  const mode = $qs("#exp-mode").value;
  const platform = $qs("#exp-plat").value;
  let url = API + `/export?mode=${mode}&platform=${encodeURIComponent(platform)}`;
  if (mode === "week") url += `&week_val=${$qs("#exp-week").value}`;
  else url += `&month_val=${$qs("#exp-month").value}`;
  closeModal(modalId);
  window.open(url, "_blank");
  toast("CSV 文件开始下载", "success");
}

// ========== DASHBOARD SUB-NAV ==========
function switchDashtab(el, tab) {
  document.querySelectorAll(".sub-nav-item").forEach(t => t.classList.remove("active"));
  if (el) el.classList.add("active");
  document.querySelectorAll(".dashtab").forEach(d => d.style.display = "none");
  const target = document.getElementById("dashtab-" + tab);
  if (target) target.style.display = "";
  document.querySelectorAll(".sidebar-sub-item").forEach(s => {
    s.classList.toggle("active", s.dataset.tab === tab);
  });
  // 切换 tab 时按需加载数据
  if (tab === "trend") loadDashboardDetail(null, "抖音");
  if (tab === "hot") loadHotContent();
  if (tab === "leads") loadLeads();
}

function switchDashtabFromSidebar(tab) {
  switchDashtab(null, tab);
}

function toggleSubmenu(el) {
  const sidebarItem = el.closest(".sidebar-item");
  const submenuId = sidebarItem?.dataset.page;
  if (!submenuId) return;
  const submenu = document.querySelector(`[data-submenu="${submenuId}"]`);
  if (submenu) submenu.classList.toggle("open");
  el.textContent = submenu?.classList.contains("open") ? "▾" : "▸";
}

function switchTrendTab(platform) {
  document.querySelectorAll("#dashtab-trend .detail-tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  loadDashboardDetail(null, platform);
}
/* P1: skeleton loading, form validation, error handling, delete confirm */
/* P2: platform color usage in data, distinct card treatments */
/* P3: guided empty states, tooltips */
/* ALL TEXT IN CHINESE */

const API = "/api";
const PLATFORMS = ["抖音", "视频号", "公众号", "小红书"];
const ACCOUNTS = {
  "抖音": ["思格电网", "安哥", "范校", "东北电气人都认"],
  "视频号": ["思格电网", "范校"],
  "公众号": ["思格电网"],
  "小红书": ["小格", "学姐"],
};

// ---------- Sidebar Navigation ----------
document.querySelectorAll(".sidebar-item[data-page]").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".sidebar-item[data-page]").forEach(i => i.classList.remove("active"));
    item.classList.add("active");
    const page = item.dataset.page;
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById("page-" + page).classList.add("active");

    const titles = {
      dashboard: "数据看板", calendar: "内容排期",
      content: "内容明细", tasks: "任务管理",
      topics: "选题库", reports: "报表生成"
    };
    document.getElementById("page-title").textContent = titles[page] || page;

    switch(page) {
      case "dashboard": loadDashboard(); break;
      case "content": loadContent(); break;
      case "calendar": loadCalendar(); break;
      case "tasks": loadTasks(); break;
      case "topics": loadTopics(); break;
      case "reports": loadReports(); break;
    }
  });
});

// ---------- Utilities ----------
function $qs(sel) { return document.querySelector(sel); }
function $qa(sel) { return document.querySelectorAll(sel); }
function fmt(n) {
  if (typeof n !== 'number') n = parseInt(n) || 0;
  return n >= 10000 ? (n / 10000).toFixed(1) + "万" : n.toLocaleString();
}
function toast(msg, type) {
  const t = document.createElement("div");
  t.className = "toast" + (type ? " " + type : "");
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}

// ---------- Form Validation (P1) ----------
function validateForm(modalId, requiredFields) {
  let valid = true;
  requiredFields.forEach(fid => {
    const el = document.getElementById(fid);
    const group = el ? el.closest(".form-group") : null;
    if (!el || !el.value.trim()) {
      if (group) group.classList.add("has-error");
      if (group) { const em = group.querySelector(".error-msg"); if (em) em.style.display = "block"; }
      valid = false;
    } else {
      if (group) group.classList.remove("has-error");
      if (group) { const em = group.querySelector(".error-msg"); if (em) em.style.display = "none"; }
    }
  });
  return valid;
}

function clearValidation(modalId) {
  document.querySelectorAll("#" + modalId + " .form-group").forEach(g => {
    g.classList.remove("has-error");
    const em = g.querySelector(".error-msg");
    if (em) em.style.display = "none";
  });
}

// ---------- Week helper ----------
function getCurrentWeek() {
  const now = new Date();
  const monday = new Date(now);
  monday.setDate(now.getDate() - (now.getDay() || 7) + 1);
  const y = monday.getFullYear();
  const mm = String(monday.getMonth() + 1).padStart(2, '0');
  const dd = String(monday.getDate()).padStart(2, '0');
  return `${y}-${mm}-${dd}`;
}

function getLastWeek() {
  const now = new Date();
  const lastMonday = new Date(now);
  lastMonday.setDate(now.getDate() - (now.getDay() || 7) - 6);
  const y = lastMonday.getFullYear();
  const mm = String(lastMonday.getMonth() + 1).padStart(2, '0');
  const dd = String(lastMonday.getDate()).padStart(2, '0');
  return `${y}-${mm}-${dd}`;
}

function updateAccountSelect(platId, acctId) {
  const plat = document.getElementById(platId);
  const acct = document.getElementById(acctId);
  if (!plat || !acct) return;
  const accounts = ACCOUNTS[plat.value] || ["主号"];
  acct.innerHTML = accounts.map((a) => "<option>" + a + "</option>").join("");
}

// ---------- Confirmation Dialog (P1) ----------
function confirmDialog(title, message, onConfirm) {
  const id = "confirm-dialog-" + Date.now();
  const html = `<div class="modal-overlay show" id="${id}">
    <div class="modal" style="max-width:400px">
      <h2>${title}</h2>
      <div class="confirm-body">
        <div class="confirm-icon">&#9888;</div>
        <p>${message}</p>
      </div>
      <div class="form-actions">
        <button class="btn btn-outline btn-sm" onclick="closeModal('${id}')">取消</button>
        <button class="btn btn-danger btn-sm" id="${id}-confirm">确认删除</button>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML("beforeend", html);
  document.getElementById(id + "-confirm").addEventListener("click", () => {
    closeModal(id);
    if (onConfirm) onConfirm();
  });
}

// ---------- Skeleton Loaders (P1) ----------
function showSkeleton(containerId, type) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (type === "cards-4") {
    el.innerHTML = Array(4).fill(0).map(() => '<div class="skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-stat"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text short"></div></div>').join("");
  } else if (type === "kpi-3") {
    el.innerHTML = Array(3).fill(0).map(() => '<div class="skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text short"></div></div>').join("");
  } else if (type === "table") {
    el.innerHTML = Array(5).fill(0).map(() => '<tr><td><div class="skeleton skeleton-text" style="height:12px"></div></td><td><div class="skeleton skeleton-text" style="height:12px;width:60%"></div></td><td><div class="skeleton skeleton-text" style="height:12px;width:40%"></div></td><td><div class="skeleton skeleton-text" style="height:12px;width:70%"></div></td><td><div class="skeleton skeleton-text" style="height:12px;width:30%"></div></td></tr>').join("");
  }
}

// ========== DASHBOARD ==========
async function loadDashboard(startWeek, endWeek) {
  // 默认显示上周数据
  if (!startWeek) {
    const lw = new Date();
    lw.setDate(lw.getDate() - (lw.getDay() || 7) - 6);
    const y = lw.getFullYear();
    const m = String(lw.getMonth() + 1).padStart(2, '0');
    const d = String(lw.getDate()).padStart(2, '0');
    startWeek = endWeek = `${y}-${m}-${d}`;
  }
  showSkeleton("overview-grid", "cards-4");
  showSkeleton("kpi-grid-container", "kpi-3");
  let url = API + "/dashboard/overview";
  if (startWeek && endWeek) url += `?start_week=${startWeek}&end_week=${endWeek}`;

  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error("数据加载失败");
    const resp = await r.json();
    const data = resp.data;
    if (!data || !data.length) {
      showEmptyOverview();
      return;
    }
    renderOverviewCards(data);
    // Populate filters
    if (resp.available_weeks && resp.available_weeks.length) {
      populateFilters(resp.available_weeks);
    }
    loadDashboardDetail(data);
    loadDashboardKPI();
  } catch(e) {
    toast("数据加载失败，请检查网络连接后刷新页面", "error");
    console.error(e);
  }
}

function showEmptyOverview() {
  const grid = $qs("#overview-grid");
  grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
    <div class="empty-icon">&#128202;</div>
    <h3>暂无数据</h3>
    <p>尚未录入任何平台运营数据，看板无法生成。</p>
    <button class="btn btn-primary btn-sm empty-cta" onclick="openMetricForm()">录入第一条数据</button>
  </div>`;
}

function renderOverviewCards(data) {
  const grid = $qs("#overview-grid");
  const platClasses = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };

  grid.innerHTML = data.map(d => {
    const cls = platClasses[d.platform] || "";
    const fwow = d.followers_wow || 0;
    const isDouyin = d.platform === "抖音";
    const isShipin = d.platform === "视频号";
    const isGzh = d.platform === "公众号";
    const isXhs = d.platform === "小红书";
    return `
    <div class="stat-card ${cls}" onclick="openPlatformDetail('${d.platform}')">
      <div class="stat-label">${d.platform}</div>
      <div class="stat-row-split">
        <div class="stat-split-item">
          <div class="stat-split-label">${isDouyin || isShipin ? '播放量' : '阅读量'}</div>
          <div class="stat-split-val">${fmt(d.plays_reads)}</div>
        </div>
        <div class="stat-split-item">
          <div class="stat-split-label">粉丝</div>
          <div class="stat-split-val">${fmt(d.followers)}</div>
        </div>
      </div>
      <div class="stat-detail">
        <div class="stat-detail-row"><span class="sdl">点赞</span><span class="sdv">${fmt(d.likes||0)}</span></div>
        <div class="stat-detail-row"><span class="sdl">评论</span><span class="sdv">${fmt(d.comments||0)}</span></div>
        ${isShipin ? `<div class="stat-detail-row"><span class="sdl">爱心</span><span class="sdv">${fmt(d.hearts||0)}</span></div>` : ''}
        <div class="stat-detail-row"><span class="sdl">分享</span><span class="sdv">${fmt(d.shares||0)}</span></div>
        ${isXhs || isDouyin || isGzh ? `<div class="stat-detail-row"><span class="sdl">收藏</span><span class="sdv">${fmt(d.bookmarks||0)}</span></div>` : ''}
        ${isDouyin ? `<div class="stat-detail-row"><span class="sdl">主页访问</span><span class="sdv">${fmt(d.in_views||0)}</span></div>` : ''}
        ${isDouyin || isShipin ? `<div class="stat-detail-row"><span class="sdl">完播率</span><span class="sdv">${(d.completion_rate||0).toFixed(1)}%</span></div>` : ''}
        <div class="stat-detail-row"><span class="sdl">互动量</span><span class="sdv">${fmt(d.engagement)}</span></div>
        <div class="stat-detail-row"><span class="sdl">发布</span><span class="sdv">${d.publish_count} 条</span></div>
        <div class="stat-detail-row stat-detail-attract"><span class="sdl">🎯 吸粉量</span><span class="sdv ${fwow >= 0 ? 'up' : 'down'}">${fwow >= 0 ? '↑' : '↓'}${Math.abs(fwow)}% · ${fmt(d.new_followers||0)}</span></div>
      </div>
    </div>`;
  }).join("");

  // 本周数据总览对比表
  const tbody = document.getElementById("overview-table-body");
  if (tbody) {
    const pMap = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
    tbody.innerHTML = data.map(d => {
      const c = pMap[d.platform] || "";
      const fw = d.followers_wow || 0;
      const pw = d.plays_reads_wow || 0;
      const ew = d.engagement_wow || 0;
      const trend = (fw >= 0 && pw >= 0 && ew >= 0) ? "↑ 全面上涨" : (fw < 0 && pw < 0) ? "↓ 多项下滑" : "→ 有涨有跌";
      const tc = (fw >= 0 && pw >= 0 && ew >= 0) ? "var(--up)" : (fw < 0 && pw < 0) ? "var(--down)" : "var(--warning)";
      return `<tr>
        <td><span class="platform-badge ${c}">${d.platform}</span></td>
        <td>${fmt(d.followers)}</td>
        <td style="color:${fw>=0?'var(--up)':'var(--down)'};font-weight:600">${fw>=0?'+':''}${fw}%</td>
        <td>${fmt(d.plays_reads)}</td>
        <td>${fmt(d.engagement)}</td>
        <td>${d.publish_count}</td>
        <td style="color:${tc};font-weight:600">${trend}</td>
      </tr>`;
    }).join("");
  }
}

function switchPlatformDetail(platform) {
  document.querySelectorAll(".detail-tab").forEach(t => t.classList.remove("active"));
  const tab = document.querySelector(`.detail-tab[data-platform="${platform}"]`);
  if (tab) tab.classList.add("active");
  loadDashboardDetail([], platform);
}

// ========== Platform Detail Page ==========
function openPlatformDetail(platform) {
  window._pdPlatform = platform;
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".sidebar-item[data-page]").forEach(i => i.classList.remove("active"));
  // Highlight dashboard sidebar item since this is accessed from dashboard
  const dashItem = document.querySelector('.sidebar-item[data-page="dashboard"]');
  if (dashItem) dashItem.classList.add("active");
  document.getElementById("page-platform-detail").classList.add("active");
  document.getElementById("page-title").textContent = "平台明细";
  loadPlatformDetail(platform);
}

function goToDashboard() {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".sidebar-item[data-page]").forEach(i => i.classList.remove("active"));
  const dashItem = document.querySelector('.sidebar-item[data-page="dashboard"]');
  if (dashItem) dashItem.classList.add("active");
  document.getElementById("page-dashboard").classList.add("active");
  document.getElementById("page-title").textContent = "数据看板";
  loadDashboard();
}

async function loadPlatformDetail(platform) {
  document.getElementById("pd-platform-name").textContent = platform;
  document.getElementById("pd-title").textContent = `${platform} · 数据明细`;

  // Skeleton
  document.getElementById("pd-aggregate").innerHTML = Array(4).fill(0).map(() => '<div class="skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-stat"></div><div class="skeleton skeleton-text"></div></div>').join("");
  document.getElementById("pd-accounts").innerHTML = "";

  try {
    const r = await fetch(API + `/dashboard/platform-detail?platform=${encodeURIComponent(platform)}`);
    if (!r.ok) throw new Error("平台明细加载失败");
    const data = await r.json();
    renderPlatformDetail(data, platform);
  } catch(e) {
    console.error(e);
    toast("平台明细加载失败", "error");
  }
}

function renderPlatformDetail(data, platform) {
  const platClasses = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
  const cls = platClasses[platform] || "";
  const agg = data.aggregate;

  document.getElementById("pd-week-label").textContent = `本周汇总 · ${data.accounts_data.length} 个账号`;

  // 平台聚合
  document.getElementById("pd-aggregate").innerHTML = `
    <div class="stat-card ${cls}">
      <div class="stat-label">${platform === "抖音" || platform === "视频号" ? "播放量" : "阅读量"}</div>
      <div class="stat-value">${fmt(agg.plays_reads)}</div>
      <div class="stat-change ${agg.plays_reads_pct >= 0 ? 'up' : 'down'}">${agg.plays_reads_pct >= 0 ? '↑' : '↓'}${Math.abs(agg.plays_reads_pct)}%</div>
    </div>
    <div class="stat-card ${cls}">
      <div class="stat-label">粉丝总数</div>
      <div class="stat-value">${fmt(agg.followers)}</div>
      <div class="stat-change ${agg.new_followers_pct >= 0 ? 'up' : 'down'}">${agg.new_followers_pct >= 0 ? '↑' : '↓'}${Math.abs(agg.new_followers_pct)}% 新增 ${fmt(agg.new_followers)}</div>
    </div>
    <div class="stat-card ${cls}">
      <div class="stat-label">互动量</div>
      <div class="stat-value">${fmt(agg.engagement)}</div>
      <div class="stat-change ${agg.engagement_pct >= 0 ? 'up' : 'down'}">${agg.engagement_pct >= 0 ? '↑' : '↓'}${Math.abs(agg.engagement_pct)}%</div>
    </div>
    <div class="stat-card ${cls}">
      <div class="stat-label">发布内容</div>
      <div class="stat-value">${agg.publish_count}</div>
      <div class="stat-change up">共 ${data.accounts_data.length} 个账号</div>
    </div>
  `;

  // 账号子卡
  const acctsDiv = document.getElementById("pd-accounts");
  if (!data.accounts_data.length) {
    acctsDiv.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><p>该平台暂无账号数据</p></div>';
    return;
  }
  acctsDiv.innerHTML = data.accounts_data.map(a => {
    const acctCol = (a.new_followers_pct >= 0 ? 'up' : 'down');
    return `
    <div class="account-card" onclick="editAccountData('${platform}','${a.account}')">
      <div class="account-header">
        <span class="account-name">${a.account}</span>
        ${a.has_data ? '<span class="account-status">已录入</span>' : '<span class="account-status pending">未录入</span>'}
      </div>
            <div class="account-metric-row-split">
        <div class="account-split-item">
          <span class="asl">${platform === "抖音" || platform === "视频号" ? "播放量" : "阅读量"}</span>
          <span class="asv">${fmt(a.plays_reads)}</span>
        </div>
        <div class="account-split-item">
          <span class="asl">粉丝</span>
          <span class="asv">${fmt(a.followers)}</span>
        </div>
      </div>
      <div class="account-metric-row">
        <span class="aml">点赞</span>
        <span class="amv">${fmt(a.likes||0)}</span>
      </div>
      <div class="account-metric-row">
        <span class="aml">评论</span>
        <span class="amv">${fmt(a.comments||0)}</span>
      </div>
      ${platform === "视频号" ? `
      <div class="account-metric-row">
        <span class="aml">爱心</span>
        <span class="amv">${fmt(a.hearts||0)}</span>
      </div>` : ''}
      <div class="account-metric-row">
        <span class="aml">分享</span>
        <span class="amv">${fmt(a.shares||0)}</span>
      </div>
      ${platform === "小红书" || platform === "抖音" || platform === "公众号" ? `
      <div class="account-metric-row">
        <span class="aml">收藏</span>
        <span class="amv">${fmt(a.bookmarks||0)}</span>
      </div>` : ''}
      ${platform === "抖音" ? `
      <div class="account-metric-row">
        <span class="aml">主页访问</span>
        <span class="amv">${fmt(a.in_views||0)}</span>
      </div>` : ''}
      ${platform === "抖音" || platform === "视频号" ? `
      <div class="account-metric-row">
        <span class="aml">完播率</span>
        <span class="amv">${a.completion_rate||0}%</span>
      </div>` : ''}
      <div class="account-metric-row">
        <span class="aml">发布</span>
        <span class="amv">${a.publish_count} 条</span>
      </div>
      <div class="account-metric-row account-metric-attract">
        <span class="aml">🎯 吸粉量</span>
        <span class="amv ${a.new_followers_pct >= 0 ? 'up' : 'down'}">${a.new_followers_pct >= 0 ? '↑' : '↓'}${Math.abs(a.new_followers_pct||0)}% · ${fmt(a.new_followers)}</span>
      </div>
      <div class="account-card-footer">点击录入或更新本周数据 →</div>
    </div>`;
  }).join("");
}

function editAccountData(platform, account) {
  // 打开录入表单并预填选定的平台和账号
  openMetricForm();
  setTimeout(() => {
    document.getElementById("mf-plat").value = platform;
    updateAccountSelect("mf-plat", "mf-acct");
    const acctSel = document.getElementById("mf-acct");
    if (acctSel) acctSel.value = account;
  }, 100);
}

async function loadDashboardDetail(allData, platform, account) {
  platform = platform || "抖音";
  account = account || "";
  // Show skeleton
  $qs("#trend-bars").innerHTML = Array(7).fill(0).map(() => '<div class="skeleton" style="flex:1;height:120px;border-radius:3px 3px 0 0"></div>').join("");

  // Update account tabs
  const accts = ACCOUNTS[platform] || ["主号"];
  const acctTabs = document.getElementById("account-tabs");
  if (acctTabs && accts.length > 1) {
    acctTabs.style.display = "flex";
    acctTabs.innerHTML = '<button class="btn btn-outline btn-sm account-tab' + (account === "" ? " active" : "") + '" data-account="" onclick="loadDashboardDetail(null,\'' + platform + '\',\'\')">全部</button>' +
      accts.map(a => '<button class="btn btn-outline btn-sm account-tab' + (account === a ? " active" : "") + '" data-account="' + a + '" onclick="loadDashboardDetail(null,\'' + platform + '\',\'' + a + '\')">' + a + '</button>').join("");
  } else if (acctTabs) {
    acctTabs.style.display = "none";
  }

  try {
    const r = await fetch(API + `/dashboard/trend?platform=${encodeURIComponent(platform)}&account=${encodeURIComponent(account)}&days=28`);
    if (!r.ok) throw new Error("趋势数据加载失败");
    const { trend } = await r.json();
    const bars = $qs("#trend-bars");
    if (trend && trend.length) {
      const maxVal = Math.max(...trend.map(t => t.plays_reads || t.plays || t.reads || t.note_reads || 0), 1);
      bars.innerHTML = trend.map(t => {
        const val = t.plays_reads || t.plays || t.reads || t.note_reads || 0;
        const h = Math.max(4, (val / maxVal) * 120);
        return `
          <div data-tooltip="${t.week_cn || t.week || t.date}: ${fmt(val)}" style="flex:1;background:var(--accent);border-radius:3px 3px 0 0;min-height:4px;height:${h}px;opacity:${0.3 + (h/120)*0.7};transition:height 0.3s"></div>`;
      }).join("");
    } else {
      bars.innerHTML = '<div class="empty-state" style="flex:1"><p>该平台暂无趋势数据</p></div>';
    }
  } catch(e) { /* no data - silent */ }

  // Data table
  showSkeleton("trend-table-body", "table");
  try {
    const dr = await fetch(API + `/data/metrics?platform=${platform}&limit=12`);
    if (dr.ok) {
      const { data: rows } = await dr.json();
      const tbody = $qs("#trend-table tbody");
      if (rows && rows.length) {
        tbody.innerHTML = rows.map(r => `
          <tr>
            <td>${r.week_cn || r.week || r.date}</td>
            <td>${fmt(r.plays || r.reads || r.note_reads || 0)}</td>
            <td>${fmt(r.new_followers || 0)}</td>
            <td>${fmt((r.likes||0)+(r.comments||0)+(r.shares||0)+(r.bookmarks||0))}</td>
            <td>${r.publish_count || 0}</td>
            <td>${r.completion_rate || 0}%</td>
          </tr>
        `).join("");
      } else {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><p>该平台暂无数据</p></td></tr>';
      }
    }
  } catch(e) {}
}

// Top 5 — 在「本周热门」tab 里跨所有平台
async function loadHotContent() {
  const top5Div = $qs("#top5-container");
  if (!top5Div) return;
  try {
    const ov = await fetch(API + "/dashboard/overview");
    const { data } = await ov.json();
    const items = [];
    data.forEach(d => {
      (d.top5 || []).forEach(c => items.push({ ...c, platform: d.platform }));
    });
    if (!items.length) {
      top5Div.innerHTML = '<div class="empty-state"><h3>暂无热门内容</h3><p>发布内容并录入数据后，排名会自动出现</p></div>';
      return;
    }
    items.sort((a, b) => (b.likes || 0) - (a.likes || 0));
    top5Div.innerHTML = items.slice(0, 10).map((c, i) => {
      const rankCls = i === 0 ? 'r1' : i === 1 ? 'r2' : i === 2 ? 'r3' : 'rn';
      return `
      <div class="top-item">
        <div class="top-rank ${rankCls}">${i + 1}</div>
        <div class="top-info">
          <div class="tt">${c.title || '未命名'}</div>
          <div class="tm">${c.platform}</div>
        </div>
        <div class="top-stat-r">${fmt(c.likes)}</div>
      </div>`;
    }).join("");
  } catch(e) {}
}

async function loadDashboardKPI() {
  try {
    const r = await fetch(API + "/dashboard/kpi");
    if (!r.ok) throw new Error("KPI 数据加载失败: " + r.status);
    const resp = await r.json();
    const data = resp.data;
    if (!data || !data.length) return;
    const grid = $qs("#kpi-grid-container");
    if (!grid) return; // tab not rendered yet
    grid.innerHTML = data.map(d => {
      const f = d.followers_kpi || {actual:0, target:1, pct:0};
      const p = d.plays_kpi || {actual:0, target:1, pct:0};
      const pu = d.publish_kpi || {actual:0, target:1, pct:0};
      const e = d.engagement_kpi || {actual:0, target:1, pct:0};
      return `
      <div class="kpi-card">
        <div class="kpi-title">${d.platform}${d.has_target ? '' : ' <span class="kpi-no-target">未设目标</span>'}</div>
        <div class="kpi-bar">
          <div class="kpi-bar-label"><span>新增粉丝</span><span>${fmt(f.actual)} / ${fmt(f.target)}</span></div>
          <div class="kpi-track"><div class="kpi-fill accent" style="width:${Math.min(f.pct, 100)}%"></div></div>
        </div>
        <div class="kpi-bar">
          <div class="kpi-bar-label"><span>播放 / 阅读</span><span>${fmt(p.actual)} / ${fmt(p.target)}</span></div>
          <div class="kpi-track"><div class="kpi-fill blue" style="width:${Math.min(p.pct, 100)}%"></div></div>
        </div>
        <div class="kpi-bar">
          <div class="kpi-bar-label"><span>发布数量</span><span>${pu.actual} / ${pu.target}</span></div>
          <div class="kpi-track"><div class="kpi-fill gold" style="width:${Math.min(pu.pct, 100)}%"></div></div>
        </div>
        <div class="kpi-bar">
          <div class="kpi-bar-label"><span>互动量</span><span>${fmt(e.actual)} / ${fmt(e.target)}</span></div>
          <div class="kpi-track"><div class="kpi-fill green" style="width:${Math.min(e.pct, 100)}%"></div></div>
        </div>
      </div>
    `}).join("");
  } catch(e) {
    toast("KPI 加载失败: " + (e.message || e), "error");
  }
}

async function openTargetSettings() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  // Load existing targets
  let existing = {};
  try {
    const r = await fetch(API + `/targets?year=${year}&month=${month}`);
    if (r.ok) {
      const { data } = await r.json();
      data.forEach(t => existing[t.platform] = t);
    }
  } catch(e) {}

  const PLATFORMS = ["抖音", "视频号", "公众号", "小红书"];
  const mid = "target-" + Date.now();
  const rows = PLATFORMS.map(p => {
    const e = existing[p] || {};
    return `<div class="target-row">
      <div class="target-platform">${p}</div>
      <div class="target-fields">
        <div class="target-field"><label>新增粉丝</label><input type="number" id="tg-${p}-nf" value="${e.target_new_followers||0}"></div>
        <div class="target-field"><label>播放/阅读</label><input type="number" id="tg-${p}-pr" value="${e.target_plays_reads||0}"></div>
        <div class="target-field"><label>发布数量</label><input type="number" id="tg-${p}-pub" value="${e.target_publish_count||0}"></div>
        <div class="target-field"><label>互动量</label><input type="number" id="tg-${p}-eng" value="${e.target_engagement||0}"></div>
      </div>
    </div>`;
  }).join("");

  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:680px"><h2>${year}年${month}月 KPI 目标</h2>
    <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px">未填写的指标会回落到上月数据</div>
    ${rows}
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveTargets(${year},${month},'${mid}')">保存目标</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveTargets(year, month, modalId) {
  const PLATFORMS = ["抖音", "视频号", "公众号", "小红书"];
  const records = PLATFORMS.map(p => ({
    year, month, platform: p,
    target_new_followers: +($qs(`#tg-${p}-nf`).value) || 0,
    target_plays_reads: +($qs(`#tg-${p}-pr`).value) || 0,
    target_publish_count: +($qs(`#tg-${p}-pub`).value) || 0,
    target_engagement: +($qs(`#tg-${p}-eng`).value) || 0,
  }));
  try {
    const r = await fetch(API + "/targets/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(records),
    });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId);
    toast("目标已保存", "success");
    loadDashboard();
  } catch(e) { toast("目标保存失败", "error"); }
}

// Detail tab switching
document.querySelectorAll(".detail-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".detail-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    loadDashboardDetail([], tab.dataset.platform);
  });
});

// ========== CONTENT ==========
async function loadContent() {
  showSkeleton("content-table-body", "table");
  try {
    const r = await fetch(API + "/content/detail?page_size=50");
    if (!r.ok) throw new Error("加载失败");
    const { data } = await r.json();
    const tbody = $qs("#content-table tbody");
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="7">
        <div class="empty-state">
          <div class="empty-icon">&#128196;</div>
          <h3>暂无内容数据</h3>
          <p>录入已发布内容的播放量、点赞等数据，开始追踪表现</p>
          <button class="btn btn-primary btn-sm empty-cta" onclick="openContentForm()">录入第一条内容</button>
        </div>
      </td></tr>`;
      return;
    }
    const platMap = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
    tbody.innerHTML = data.map(d => `
      <tr>
        <td>${d.publish_date}</td>
        <td><span class="platform-badge ${platMap[d.platform]||''}">${d.platform}</span></td>
        <td>${d.content_type}</td>
        <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${d.title}</td>
        <td>${d.is_viral ? '🔥 爆款' : '常规'}</td>
        <td>${d.likes || 0}</td>
        <td>${d.author || '-'}</td>
      </tr>
    `).join("");
  } catch(e) {
    toast("内容数据加载失败", "error");
  }
}

// ========== CALENDAR ==========
async function loadCalendar() { loadMonthCalendar(); }

function loadMonthCalendar(year, month) {
  const now = new Date();
  year = year || now.getFullYear();
  month = month !== undefined ? month : now.getMonth();
  document.getElementById("cal-title").textContent = `${year}年${month + 1}月`;
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const todayStr = now.toISOString().split("T")[0];
  const startDate = `${year}-${String(month + 1).padStart(2, "0")}-01`;
  const endDate = `${year}-${String(month + 1).padStart(2, "0")}-${daysInMonth}`;

  fetch(API + `/content/calendar?start_date=${startDate}&end_date=${endDate}`)
    .then(r => r.json())
    .then(({ data }) => {
      const evtMap = {};
      data.forEach(e => { if (!evtMap[e.scheduled_date]) evtMap[e.scheduled_date] = []; evtMap[e.scheduled_date].push(e); });
      const dayNames = ["日","一","二","三","四","五","六"];
      const platCls = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
      let html = dayNames.map(h => `<div class="calendar-day-header">${h}</div>`).join("");
      for (let i = 0; i < firstDay; i++) html += '<div class="calendar-day" style="opacity:0.3"></div>';
      for (let d = 1; d <= daysInMonth; d++) {
        const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
        const evts = evtMap[ds] || [];
        const isToday = ds === todayStr;
        html += `<div class="calendar-day ${isToday ? 'today' : ''}" onclick="openCreateCalendar('${ds}')">
          <div class="day-num">${d}</div>
          ${evts.map(e => `<div class="calendar-event ${platCls[e.platform]||''}" onclick="event.stopPropagation();editCalendar(${e.id})" title="${e.platform} · ${e.status}"><span class="cal-platform">${e.platform}</span><span class="cal-title">${e.title}</span></div>`).join("")}
        </div>`;
      }
      document.getElementById("cal-grid").innerHTML = html;
    })
    .catch(() => toast("排期数据加载失败", "error"));
}

function calendarPrev() {
  const parts = document.getElementById("cal-title").textContent.match(/(\d+)/g);
  if (!parts) return;
  let y = +parts[0], m = +parts[1] - 1;
  if (m === 0) { y--; m = 11; } else m--;
  loadMonthCalendar(y, m);
}
function calendarNext() {
  const parts = document.getElementById("cal-title").textContent.match(/(\d+)/g);
  if (!parts) return;
  let y = +parts[0], m = +parts[1] - 1;
  if (m === 11) { y++; m = 0; } else m++;
  loadMonthCalendar(y, m);
}

function openCreateCalendar(ds) {
  const id = "cal-modal-" + Date.now();
  const html = `<div class="modal-overlay show" id="${id}"><div class="modal"><h2>新建排期 — ${ds}</h2>
    <div class="form-group"><label>标题 <span class="required">*</span></label><input id="ci-title" placeholder="输入内容标题"><span class="error-msg">请输入标题</span></div>
    <div class="form-group"><label>平台</label><select id="ci-platform">${PLATFORMS.map(p=>`<option>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>内容类型</label><select id="ci-type"><option>短视频</option><option>图文</option><option>长文章</option><option>笔记</option></select></div>
    <div class="form-group"><label>负责人</label><input id="ci-assignee" placeholder="负责人姓名"></div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${id}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveCalendar('${ds}','${id}')">保存排期</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveCalendar(ds, modalId) {
  if (!validateForm(modalId, ["ci-title"])) {
    toast("请填写标题", "error"); return;
  }
  const body = {
    title: $qs("#ci-title").value, platform: $qs("#ci-platform").value,
    content_type: $qs("#ci-type").value, scheduled_date: ds,
    assignee: $qs("#ci-assignee").value, status: "待策划"
  };
  try {
    const r = await fetch(API + "/content/calendar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId); loadCalendar(); toast("排期已创建", "success");
  } catch(e) { toast("排期创建失败，请重试", "error"); }
}

async function editCalendar(id) {
  try {
    const r = await fetch(API + "/content/calendar");
    const { data } = await r.json();
    const item = data.find(d => d.id === id);
    if (!item) { toast("未找到该排期", "error"); return; }
    const mid = "cal-edit-" + Date.now();
    const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>编辑排期</h2>
      <div class="form-group"><label>标题</label><input id="ce-title" value="${item.title}"></div>
      <div class="form-group"><label>状态</label><select id="ce-status">
        ${["待策划","制作中","待审核","待发布","已发布"].map(s => `<option ${item.status===s?'selected':''}>${s}</option>`).join("")}
      </select></div>
      <div class="form-group"><label>负责人</label><input id="ce-assignee" value="${item.assignee||''}"></div>
      <div class="form-actions">
        <button class="btn btn-danger btn-sm" onclick="deleteCalendar(${id},'${mid}')">删除排期</button>
        <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
        <button class="btn btn-primary btn-sm" onclick="updateCalendar(${id},'${mid}')">保存修改</button>
      </div>
    </div></div>`;
    document.body.insertAdjacentHTML("beforeend", html);
  } catch(e) { toast("获取排期详情失败", "error"); }
}

async function updateCalendar(id, modalId) {
  const body = {
    title: $qs("#ce-title").value, status: $qs("#ce-status").value,
    assignee: $qs("#ce-assignee").value,
  };
  try {
    const r = await fetch(API + `/content/calendar/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("更新失败");
    closeModal(modalId); loadCalendar(); toast("排期已更新", "success");
  } catch(e) { toast("更新失败，请重试", "error"); }
}

async function deleteCalendar(id, modalId) {
  if (!confirm("确定要删除这条排期吗？此操作不可撤销。")) return;
  closeModal(modalId);
  try {
    const r = await fetch(API + `/content/calendar/${id}`, { method: "DELETE" });
    const data = await r.json();
    if (!r.ok || !data.ok) throw new Error(data.error || "操作失败");
    loadCalendar(); toast("排期已删除", "success");
  } catch(e) { toast("删除失败：" + e.message, "error"); }
}

// ========== TASKS ==========
async function loadTasks() {
  try {
    const r = await fetch(API + "/tasks");
    if (!r.ok) throw new Error("加载失败");
    const { data } = await r.json();
    const cols = { 待办: [], 进行中: [], 已完成: [] };
    data.forEach(t => { if (cols[t.status]) cols[t.status].push(t); });
    const colIds = { 待办: "kanban-todo", 进行中: "kanban-progress", 已完成: "kanban-done" };
    const count = data.filter(t => t.status !== "已完成").length;
    document.getElementById("task-count").textContent = count;
    const platMap = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };

    Object.keys(cols).forEach(status => {
      const col = document.getElementById(colIds[status]);
      if (!col) return;
      if (!cols[status].length) {
        const msgs = { 待办: "暂无待办任务", 进行中: "暂无进行中任务", 已完成: "暂无已完成任务" };
        col.innerHTML = `<div class="empty-state" style="padding:20px"><p>${msgs[status]}</p></div>`;
        return;
      }
      col.innerHTML = cols[status].map(t => `
        <div class="kanban-item" onclick="editTask(${t.id})">
          <div class="task-title">${t.title}</div>
          <div class="task-meta">
            <span class="priority-${t.priority==='高'?'high':t.priority==='中'?'mid':'low'}">${t.priority==='高'?'高优先':t.priority==='中'?'中优先':'低优先'}</span>
            ${t.assignee ? `<span>👤 ${t.assignee}</span>` : ''}
            ${t.platform ? `<span class="platform-badge ${platMap[t.platform]||''}">${t.platform}</span>` : ''}
            ${t.due_date ? `<span>📅 ${t.due_date}</span>` : ''}
          </div>
        </div>
      `).join("");
    });
  } catch(e) { toast("任务数据加载失败", "error"); }
}

async function editTask(id) {
  try {
    const r = await fetch(API + "/tasks");
    const { data } = await r.json();
    const item = data.find(d => d.id === id);
    if (!item) { toast("未找到该任务", "error"); return; }
    const mid = "tsk-edit-" + Date.now();
    const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>编辑任务</h2>
      <div class="form-group"><label>标题</label><input id="te-title" value="${item.title}"></div>
      <div class="form-group"><label>状态</label><select id="te-status">
        ${["待办","进行中","已完成"].map(s => `<option ${item.status===s?'selected':''}>${s}</option>`).join("")}
      </select></div>
      <div class="form-group"><label>负责人</label><input id="te-assignee" value="${item.assignee||''}"></div>
      <div class="form-group"><label>优先级</label><select id="te-pri"><option ${item.priority==='高'?'selected':''}>高</option><option ${item.priority==='中'?'selected':''}>中</option><option ${item.priority==='低'?'selected':''}>低</option></select></div>
      <div class="form-actions">
        <button class="btn btn-danger btn-sm" onclick="deleteTask(${id},'${mid}')">删除任务</button>
        <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
        <button class="btn btn-primary btn-sm" onclick="updateTask(${id},'${mid}')">保存修改</button>
      </div>
    </div></div>`;
    document.body.insertAdjacentHTML("beforeend", html);
  } catch(e) { toast("获取任务详情失败", "error"); }
}

async function updateTask(id, modalId) {
  const body = {
    title: $qs("#te-title").value, status: $qs("#te-status").value,
    assignee: $qs("#te-assignee").value, priority: $qs("#te-pri").value,
  };
  try {
    const r = await fetch(API + `/tasks/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("更新失败");
    closeModal(modalId); loadTasks(); toast("任务已更新", "success");
  } catch(e) { toast("更新失败，请重试", "error"); }
}

async function deleteTask(id, modalId) {
  if (!confirm("确定要删除这个任务吗？此操作不可撤销。")) return;
  closeModal(modalId);
  try {
    await fetch(API + `/tasks/${id}`, { method: "DELETE" });
    loadTasks(); toast("任务已删除", "success");
  } catch(e) { toast("删除失败", "error"); }
}

// ========== TOPICS ==========
async function loadTopics() {
  showSkeleton("topics-table-body", "table");
  try {
    const r = await fetch(API + "/topics?page_size=50");
    if (!r.ok) throw new Error("加载失败");
    const { data } = await r.json();
    const tbody = $qs("#topics-table tbody");
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="6">
        <div class="empty-state">
          <div class="empty-icon">&#128161;</div>
          <h3>暂无选题</h3>
          <p>捕捉热点灵感、竞品动态，建立选题库</p>
          <button class="btn btn-primary btn-sm empty-cta" onclick="openTopicForm()">创建第一条选题</button>
        </div>
      </td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(d => `
      <tr>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${d.title}</td>
        <td>${d.source}</td>
        <td>${d.platforms || '-'}</td>
        <td><span class="status-dot ${d.status==='已采纳'?'active':d.status==='已发布'?'active':d.status==='待评估'?'warning':'muted'}">${d.status}</span></td>
        <td>${d.creator || '-'}</td>
        <td>${d.status==='待评估'?`<button class="btn btn-primary btn-sm" onclick="openTopicToCal(${d.id},'${d.title.replace(/'/g,"\\'")}')">转为排期</button>`:''}</td>
      </tr>
    `).join("");
  } catch(e) { toast("选题数据加载失败", "error"); }
}

function openTopicToCal(id, title) {
  const mid = "tc-" + Date.now();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>选题转为排期</h2>
    <p style="font-size:14px;color:var(--text-secondary);margin-bottom:16px">「${title}」</p>
    <div class="form-group"><label>发布平台 <span class="required">*</span></label><select id="tc-plat">${PLATFORMS.map(p=>`<option>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>排期日期 <span class="required">*</span></label><input type="date" id="tc-date" value="${new Date().toISOString().split('T')[0]}"></div>
    <div class="form-group"><label>负责人</label><input id="tc-who" placeholder="负责人姓名"></div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="convertTopic(${id},'${mid}')">创建排期</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function convertTopic(id, modalId) {
  if (!validateForm(modalId, ["tc-plat", "tc-date"])) {
    toast("请填写平台和日期", "error"); return;
  }
  const p = $qs("#tc-plat").value, d = $qs("#tc-date").value, a = $qs("#tc-who").value;
  try {
    const r = await fetch(API + `/topics/${id}/to-calendar?scheduled_date=${d}&platform=${p}&assignee=${a}`, { method: "POST" });
    if (!r.ok) throw new Error("操作失败");
    closeModal(modalId); toast("选题已转为排期", "success"); loadTopics();
  } catch(e) { toast("转换失败，请重试", "error"); }
}

// ========== REPORTS ==========
async function loadReports(type) {
  type = type || 'weekly';
  $qs("#report-area").innerHTML = '<div class="empty-state"><div class="skeleton skeleton-title" style="margin:0 auto 16px;width:200px"></div><div class="skeleton skeleton-text" style="margin:0 auto;width:300px"></div><p style="margin-top:12px">正在生成报表...</p></div>';
  try {
    const r = await fetch(API + `/reports?report_type=${type}`);
    if (!r.ok) throw new Error("报表生成失败");
    const { markdown } = await r.json();
    let html = markdown
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^---$/gm, '<hr>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    html = html.replace(/\|(.+)\|/g, m => {
      const cells = m.split('|').filter(c => c.trim());
      if (cells[0] && cells[0].includes('---')) return '</thead><tbody>';
      return `<tr>${cells.map(c => `<td>${c.trim()}</td>`).join('')}</tr>`;
    });
    html = html.replace(/(<tr>.*<\/tr>\n?)+/g, '<table><thead>$&</tbody></table>');
    html = html.replace(/<blockquote>/g, '<blockquote>').replace(/<\/blockquote>/g, '</blockquote>');
    $qs("#report-area").innerHTML = `<div class="report-body">${html}</div>`;
  } catch(e) {
    $qs("#report-area").innerHTML = `<div class="empty-state">
      <div class="empty-icon">&#128203;</div>
      <h3>暂无数据生成报表</h3>
      <p>请先在数据看板中录入平台运营数据，才能自动生成周报。录入后回到此处，点击「生成周报」即可。</p>
      <button class="btn btn-primary btn-sm empty-cta" onclick="openMetricForm()">去录入数据</button>
    </div>`;
  }
}

// ========== MODAL ==========
function closeModal(id) { const el = document.getElementById(id); if (el) el.remove(); }

// ========== BATCH ENTRY ==========
async function openBatchEntry(platform) {
  const accts = ACCOUNTS[platform] || ["主号"];
  const thisWeek = getLastWeek();

  // 查上周数据做参考
  let lastWeekData = {};
  try {
    const lastMon = new Date(); lastMon.setDate(lastMon.getDate() - lastMon.getDay() - 6);
    const y = lastMon.getFullYear(); const m = String(lastMon.getMonth()+1).padStart(2,"0"); const d = String(lastMon.getDate()).padStart(2,"0");
    const lastWeekStart = `${y}-${m}-${d}`;
    const r = await fetch(API + `/data/metrics?platform=${encodeURIComponent(platform)}&start_date=${lastWeekStart}&limit=50`);
    if (r.ok) {
      const { data } = await r.json();
      data.forEach(row => { lastWeekData[row.account || ""] = row; });
    }
  } catch(e) {}

  let rows = accts.map((a, i) => {
    const prev = lastWeekData[a] || {};
    const showBookmark = (platform === "小红书" || platform === "抖音" || platform === "公众号");
    return `<div class="batch-row">
      <div class="batch-account">${a}</div>
      <div class="batch-fields">
        <div class="batch-field"><label>粉丝</label><input id="b${i}-f" type="number" value="${prev.followers||0}" placeholder="粉丝数"></div>
        <div class="batch-field"><label>新增</label><input id="b${i}-nf" type="number" value="${prev.new_followers||0}" placeholder="新增粉丝"></div>
        <div class="batch-field"><label>播放/阅读</label><input id="b${i}-p" type="number" value="${prev.plays||prev.reads||prev.note_reads||0}" placeholder="播放/阅读量"></div>
        <div class="batch-field"><label>点赞</label><input id="b${i}-l" type="number" value="${prev.likes||0}" placeholder="点赞"></div>
        <div class="batch-field"><label>评论</label><input id="b${i}-c" type="number" value="${prev.comments||0}" placeholder="评论"></div>
        ${showBookmark ? `<div class="batch-field"><label>收藏</label><input id="b${i}-bm" type="number" value="${prev.bookmarks||0}" placeholder="收藏"></div>` : ''}
        <div class="batch-field"><label>分享</label><input id="b${i}-s" type="number" value="${prev.shares||0}" placeholder="分享"></div>
        ${platform === "抖音" ? `<div class="batch-field"><label>主页访问</label><input id="b${i}-iv" type="number" value="${prev.in_views||0}" placeholder="主页访问"></div>` : ''}
        ${platform === "视频号" ? `<div class="batch-field"><label>爱心</label><input id="b${i}-ht" type="number" value="${prev.hearts||0}" placeholder="爱心"></div>` : ''}
        ${platform === "抖音" || platform === "视频号" ? `<div class="batch-field"><label>完播率%</label><input id="b${i}-cr" type="number" value="${prev.completion_rate||0}" placeholder="完播率" step="0.1" style="width:60px"></div>` : ''}
        <div class="batch-field"><label>发布数</label><input id="b${i}-pub" type="number" value="${prev.publish_count||0}" placeholder="发布条数" style="width:60px"></div>
      </div>
    </div>`;
  }).join("");

  const mid = "batch-" + Date.now();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:680px"><h2>${platform} · 快速录入本周数据</h2>
    <div class="form-group"><label>周次</label><input type="week" id="b-week" value="${thisWeek}" style="width:200px"></div>
    <div class="batch-container">${rows}</div>
    <div style="font-size:10px;color:var(--text-muted);margin:8px 0">已填入上周数据作为参考，修改后保存</div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveBatch('${mid}','${platform.replace(/'/g,"\\'")}',${accts.length})">一键保存全部</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveBatch(modalId, platform, count) {
  const week = $qs("#b-week").value;
  if (!week) { toast("请选择周次", "error"); return; }
  let saved = 0, errors = [];
  for (let i = 0; i < count; i++) {
    const acctEl = document.querySelector(`#${modalId} .batch-row:nth-child(${i+1}) .batch-account`);
    if (!acctEl) { errors.push(`第${i+1}行账号读取失败`); continue; }
    const acctName = acctEl.textContent;
    const f = +($qs(`#b${i}-f`).value) || 0;
    const nf = +($qs(`#b${i}-nf`).value) || 0;
    const p = +($qs(`#b${i}-p`).value) || 0;
    const l = +($qs(`#b${i}-l`).value) || 0;
    const c = +($qs(`#b${i}-c`).value) || 0;
    const s = +($qs(`#b${i}-s`)?.value) || 0;
    const bm = +($qs(`#b${i}-bm`)?.value) || 0;
    const iv = +($qs(`#b${i}-iv`)?.value) || 0;
    const cr = parseFloat($qs(`#b${i}-cr`)?.value) || 0;
    const ht = +($qs(`#b${i}-ht`)?.value) || 0;
    const pub = +($qs(`#b${i}-pub`).value) || 0;

    const body = {
      week, platform, account: acctName,
      followers: f, new_followers: nf, plays: p, likes: l, comments: c,
      shares: s, bookmarks: bm, hearts: ht, in_views: iv, completion_rate: cr, publish_count: pub,
    };
    if (platform === "小红书") { body.note_reads = p; body.plays = 0; }
    else if (platform === "公众号") { body.reads = p; body.plays = 0; }

    try {
      const r = await fetch(API + "/data/metrics", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (r.ok) saved++;
      else errors.push(`${acctName}: HTTP ${r.status}`);
    } catch(e) { errors.push(`${acctName}: ${e.message}`); }
  }
  closeModal(modalId);
  if (saved === count) toast(`已保存 ${saved}/${count} 个账号`, "success");
  else if (saved > 0) toast(`部分成功 ${saved}/${count}：${errors.join("; ")}`, "warning");
  else toast(`保存失败：${errors.join("; ")}`, "error");
  if (window._pdPlatform) loadPlatformDetail(window._pdPlatform);
  else loadDashboard();
}

// ========== DATA ENTRY (P1: new metric form) ==========
function openMetricForm() {
  const mid = "metric-" + Date.now();
  const thisWeek = getLastWeek();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>录入本周数据</h2>
    <div class="form-group"><label>平台 <span class="required">*</span></label><select id="mf-plat" onchange="updateAccountSelect('mf-plat','mf-acct');togglePlatformFields()">${PLATFORMS.map(p=>`<option>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>账号</label><select id="mf-acct"></select></div>
    <div class="form-group"><label>周次 <span class="required">*</span></label><input type="week" id="mf-week" value="${thisWeek}"><span class="error-msg">请选择周次</span></div>
    <div class="form-group"><label>粉丝数</label><input type="number" id="mf-followers" value="0"></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="form-group"><label>播放 / 阅读</label><input type="number" id="mf-plays" value="0"></div>
      <div class="form-group"><label>点赞</label><input type="number" id="mf-likes" value="0"></div>
      <div class="form-group"><label>评论</label><input type="number" id="mf-comments" value="0"></div>
      <div class="form-group"><label>分享</label><input type="number" id="mf-shares" value="0"></div>
      <div class="form-group" id="mf-bookmark-group" style="display:none"><label>收藏</label><input type="number" id="mf-bookmarks" value="0"></div>
      <div class="form-group" id="mf-home-group" style="display:none"><label>主页访问</label><input type="number" id="mf-inviews" value="0"></div>
      <div class="form-group" id="mf-comp-group" style="display:none"><label>完播率 (%)</label><input type="number" id="mf-comprate" value="0" step="0.1"></div>
      <div class="form-group" id="mf-heart-group" style="display:none"><label>爱心</label><input type="number" id="mf-hearts" value="0"></div>
      <div class="form-group"><label>新增粉丝</label><input type="number" id="mf-newf" value="0"></div>
      <div class="form-group"><label>发布数</label><input type="number" id="mf-pub" value="0"></div>
    </div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveMetric('${mid}')">保存数据</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

function togglePlatformFields() {
  const plat = document.getElementById("mf-plat").value;
  const show = (id, v) => { const el = document.getElementById(id); if (el) el.style.display = v ? "" : "none"; };
  show("mf-bookmark-group", plat === "小红书" || plat === "抖音" || plat === "公众号");
  show("mf-home-group", plat === "抖音");
  show("mf-comp-group", plat === "抖音" || plat === "视频号");
  show("mf-heart-group", plat === "视频号");
}

async function saveMetric(modalId) {
  if (!validateForm(modalId, ["mf-plat", "mf-week"])) {
    toast("请选择平台和周次", "error"); return;
  }
  const body = {
    week: $qs("#mf-week").value,
    platform: $qs("#mf-plat").value,
    account: $qs("#mf-acct").value,
    followers: +$qs("#mf-followers").value||0,
    plays: +$qs("#mf-plays").value||0,
    likes: +$qs("#mf-likes").value||0,
    comments: +$qs("#mf-comments").value||0,
    shares: +$qs("#mf-shares").value||0,
    bookmarks: +($qs("#mf-bookmarks")?.value)||0,
    in_views: +($qs("#mf-inviews")?.value)||0,
    completion_rate: +($qs("#mf-comprate")?.value)||0,
    hearts: +($qs("#mf-hearts")?.value)||0,
    new_followers: +$qs("#mf-newf").value||0,
    publish_count: +$qs("#mf-pub").value||0,
    reads: $qs("#mf-plat").value === "公众号" ? (+$qs("#mf-plays").value||0) : 0,
    note_reads: $qs("#mf-plat").value === "小红书" ? (+$qs("#mf-plays").value||0) : 0,
  };
  try {
    const r = await fetch(API + "/data/metrics", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId);
    toast("数据已保存", "success");
    loadDashboard();
  } catch(e) { toast("数据保存失败，请重试", "error"); }
}

// ========== CONTENT FORM ==========
function openContentForm() {
  const mid = "cf-" + Date.now();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>录入内容明细</h2>
    <div class="form-group"><label>标题 <span class="required">*</span></label><input id="cf-title" placeholder="内容标题"><span class="error-msg">请输入标题</span></div>
    <div class="form-group"><label>平台 <span class="required">*</span></label><select id="cf-plat">${PLATFORMS.map(p=>`<option>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>类型</label><select id="cf-type"><option>短视频</option><option>图文</option><option>长文章</option><option>笔记</option></select></div>
    <div class="form-group"><label>发布日期 <span class="required">*</span></label><input type="date" id="cf-date" value="${new Date().toISOString().split('T')[0]}"><span class="error-msg">请选择日期</span></div>
    <div class="form-group"><label>链接</label><input id="cf-url" placeholder="https://..."></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="form-group"><label>播放 / 阅读</label><input type="number" id="cf-imp" value="0"></div>
      <div class="form-group"><label>点赞</label><input type="number" id="cf-likes" value="0"></div>
    </div>
    <div class="form-group"><label>负责人</label><input id="cf-author" placeholder="负责人姓名"></div>
    <div class="form-group"><label>备注</label><textarea id="cf-notes" rows="2" placeholder="选填"></textarea></div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveContent('${mid}')">保存内容</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveContent(modalId) {
  if (!validateForm(modalId, ["cf-title", "cf-plat", "cf-date"])) {
    toast("请填写标题、平台和日期", "error"); return;
  }
  const body = {
    title: $qs("#cf-title").value, platform: $qs("#cf-plat").value,
    content_type: $qs("#cf-type").value, publish_date: $qs("#cf-date").value,
    url: $qs("#cf-url").value, impressions: +$qs("#cf-imp").value||0,
    likes: +$qs("#cf-likes").value||0, author: $qs("#cf-author").value,
    notes: $qs("#cf-notes").value,
  };
  try {
    const r = await fetch(API + "/content/detail", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId); loadContent(); toast("内容已录入", "success");
  } catch(e) { toast("内容保存失败，请重试", "error"); }
}

// ========== TOPIC FORM ==========
function openTopicForm() {
  const mid = "tf-" + Date.now();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>新增选题</h2>
    <div class="form-group"><label>标题 <span class="required">*</span></label><input id="tf-title" placeholder="选题标题"><span class="error-msg">请输入标题</span></div>
    <div class="form-group"><label>来源</label><select id="tf-src"><option>灵感</option><option>热点</option><option>竞品</option><option>活动</option></select></div>
    <div class="form-group"><label>适配平台</label><input id="tf-plats" placeholder="抖音、公众号（逗号分隔）"></div>
    <div class="form-group"><label>优先级</label><select id="tf-pri"><option>高</option><option selected>中</option><option>低</option></select></div>
    <div class="form-group"><label>创建人</label><input id="tf-creator" placeholder="创建人姓名"></div>
    <div class="form-group"><label>备注</label><textarea id="tf-notes" rows="2" placeholder="选填"></textarea></div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveTopic('${mid}')">保存选题</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveTopic(modalId) {
  if (!validateForm(modalId, ["tf-title"])) {
    toast("请输入选题标题", "error"); return;
  }
  const body = {
    title: $qs("#tf-title").value, source: $qs("#tf-src").value,
    platforms: $qs("#tf-plats").value, priority: $qs("#tf-pri").value,
    creator: $qs("#tf-creator").value, notes: $qs("#tf-notes").value,
  };
  try {
    const r = await fetch(API + "/topics", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId); loadTopics(); toast("选题已创建", "success");
  } catch(e) { toast("选题创建失败，请重试", "error"); }
}

// ========== TASK FORM ==========
function openTaskForm() {
  const mid = "tsk-" + Date.now();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>新建任务</h2>
    <div class="form-group"><label>标题 <span class="required">*</span></label><input id="tsk-title" placeholder="任务标题"><span class="error-msg">请输入标题</span></div>
    <div class="form-group"><label>负责人</label><input id="tsk-who" placeholder="负责人姓名"></div>
    <div class="form-group"><label>优先级</label><select id="tsk-pri"><option>高</option><option selected>中</option><option>低</option></select></div>
    <div class="form-group"><label>关联平台</label><select id="tsk-plat"><option value="">无</option>${PLATFORMS.map(p=>`<option>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>截止日期</label><input type="date" id="tsk-due"></div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveTask('${mid}')">保存任务</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveTask(modalId) {
  if (!validateForm(modalId, ["tsk-title"])) {
    toast("请输入任务标题", "error"); return;
  }
  const body = {
    title: $qs("#tsk-title").value, assignee: $qs("#tsk-who").value,
    priority: $qs("#tsk-pri").value, platform: $qs("#tsk-plat").value,
    due_date: $qs("#tsk-due").value || null,
  };
  try {
    const r = await fetch(API + "/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId); loadTasks(); toast("任务已创建", "success");
  } catch(e) { toast("任务创建失败，请重试", "error"); }
}

// ========== FILTER ==========
function populateFilters(weeks) {
  // 月份下拉
  const months = [...new Set(weeks.map(w => w.cn.replace(/年.*/, '年') + w.cn.match(/\d+月/)[0]))];
  const monthSel = document.getElementById("filter-month");
  if (monthSel) monthSel.innerHTML = '<option value="">全部月份</option>' + months.map(m => `<option>${m}</option>`).join("");

  // 周次下拉
  const weekSel = document.getElementById("filter-week");
  if (weekSel) weekSel.innerHTML = '<option value="">选择周次</option>' + weeks.map(w => `<option value="${w.iso}">${w.cn}</option>`).join("");
}

function onMonthFilter() {
  const m = document.getElementById("filter-month").value;
  if (!m) return resetFilter();
  // Extract year and month numbers
  const [y, mo] = m.match(/\d+/g);
  const year = parseInt(y), month = parseInt(mo);
  // Find first and last week of this month
  const firstDate = new Date(year, month - 1, 1);
  const firstMon = new Date(firstDate);
  firstMon.setDate(firstMon.getDate() + (8 - firstMon.getDay()) % 7);
  const lastDate = new Date(year, month, 0);
  const lastMon = new Date(lastDate);
  lastMon.setDate(lastMon.getDate() - (lastMon.getDay() + 6) % 7);
  // Format as ISO weeks
  const w1 = isoWeek(firstMon);
  const w2 = isoWeek(lastMon);
  loadDashboard(w1, w2);
}

function onWeekFilter() {
  const w = document.getElementById("filter-week").value;
  if (!w) return resetFilter();
  loadDashboard(w, w);
}

function resetFilter() {
  document.getElementById("filter-month").value = "";
  document.getElementById("filter-week").value = "";
  loadDashboard();
}

function isoWeek(d) {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`;
}

// ========== LEADS ==========
async function loadLeads() {
  const s = await fetch(API + "/leads/summary");
  if (!s.ok) return;
  const data = await s.json();

  // Stat cards
  document.getElementById("leads-cards").innerHTML = [
    { label: "总线索", val: data.total, cls: "" },
    { label: "有效线索", val: data.valid, cls: "up", sub: `留资率 ${data.valid_rate}%` },
    { label: "待跟进", val: data.pending, cls: "" },
    { label: "平均沟通", val: data.contact_avg, cls: "" },
  ].map(c => `<div class="stat-card">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value ${c.cls}">${c.val}</div>
    ${c.sub ? `<div class="stat-change up">${c.sub}</div>` : ''}
  </div>`).join("");

  // 渠道来源（10 个平台全部展示）
  const all_sources = ["抖音", "微信视频号", "微信公众号", "微信私域社群/个人", "小红书平台",
                       "本地生活平台", "快手", "AI搜索/智能问答", "其他新媒体平台", "线上+短视频平台"];
  const src_map = {};
  data.by_source.forEach(s => { src_map[s.name] = s.count; });
  const src_data = all_sources.map(k => ({name: k, count: src_map[k] || 0}));
  const maxSrc = Math.max(...src_data.map(s => s.count), 1);
  document.getElementById("leads-source-chart").innerHTML = src_data.map(s => `
      <div class="lead-bar-row">
        <span class="lead-bar-label">${s.name}</span>
        <div class="lead-bar-track"><div class="lead-bar-fill" style="width:${(s.count/maxSrc)*100}%"></div></div>
        <span class="lead-bar-val">${s.count}</span>
      </div>`).join("");

  // 有效性（待定/有效/无效）
  const all_validity = ["有效", "待定", "无效"];
  const validity_data = all_validity.map(k => ({
    name: k,
    count: data.by_validity && data.by_validity[k] || 0
  }));
  const totalForVal = validity_data.reduce((a,b)=>a+b.count, 0) || 1;
  document.getElementById("leads-status-chart").innerHTML = validity_data.map(s => `
      <div class="lead-bar-row">
        <span class="lead-bar-label">${s.name}</span>
        <div class="lead-bar-track"><div class="lead-bar-fill ${s.name==='有效'?'accent':s.name==='待定'?'warning':'invalid'}" style="width:${(s.count/totalForVal)*100}%"></div></div>
        <span class="lead-bar-val">${s.count} (${Math.round(s.count/totalForVal*100)}%)</span>
      </div>`).join("");

  // Daily trend
  if (data.by_day.length) {
    const maxD = Math.max(...data.by_day.map(d => d.count), 1);
    document.getElementById("leads-day-chart").innerHTML = data.by_day.map(d => {
      const h = Math.max(4, (d.count / maxD) * 80);
      return `<div style="flex:1;text-align:center">
        <div style="background:var(--accent);height:${h}px;border-radius:3px 3px 0 0;min-height:2px;opacity:${0.4+(h/80)*0.6}"></div>
        <div style="font-size:8px;color:var(--text-muted);margin-top:2px">${d.date.slice(5)}</div>
      </div>`;
    }).join("");
  }

  // Region
  if (data.by_region.length) {
    const maxR = Math.max(...data.by_region.map(r => r.count));
    document.getElementById("leads-region-chart").innerHTML = data.by_region.map(r => `
      <div class="lead-bar-row">
        <span class="lead-bar-label">${r.name}</span>
        <div class="lead-bar-track"><div class="lead-bar-fill region" style="width:${(r.count/maxR)*100}%"></div></div>
        <span class="lead-bar-val">${r.count}</span>
      </div>`).join("");
  }

  // Intent distribution
  if (data.intent_distribution.length) {
    const maxI = Math.max(...data.intent_distribution.map(i => i.count));
    document.getElementById("leads-intent-chart").innerHTML = data.intent_distribution.map(i => `
      <div class="lead-bar-row">
        <span class="lead-bar-label">意向 ${i.level}</span>
        <div class="lead-bar-track"><div class="lead-bar-fill gold" style="width:${(i.count/maxI)*100}%"></div></div>
        <span class="lead-bar-val">${i.count}</span>
      </div>`).join("");
  }
}

// ========== INIT ==========
loadDashboard();
