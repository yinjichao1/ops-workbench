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
  if (target) target.style.display = "block";
  document.querySelectorAll(".sidebar-sub-item").forEach(s => {
    s.classList.toggle("active", s.dataset.tab === tab);
  });
  // 切换 tab 时按需加载数据
  if (tab === "trend") loadDashboardDetail(null, "抖音");
  if (tab === "hot") loadHotContent();
  if (tab === "leads") {
    const wi = $qs("#leads-week");
    if (wi && !wi.value) wi.value = getLastWeek();
    const yr = $qs("#leads-year");
    if (yr && !yr.value) yr.value = new Date().getFullYear();
    const mn = $qs("#leads-month");
    if (mn && !mn.value) {
      const n = new Date();
      mn.value = `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}`;
    }
    loadLeads();
  }
}

function switchDashtabFromSidebar(tab) {
  switchDashtab(null, tab);
}

let ovCurrentMode = "week";
function getPreviousMonthValue() {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}
function getPreviousWeekDate() {
  const d = new Date();
  d.setDate(d.getDate() - (d.getDay() || 7) - 6);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function getCurrentWeekDate() {
  const d = new Date();
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function getCurrentMonthValue() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}
function switchOvMode(mode) {
  ovCurrentMode = mode;
  const w = document.getElementById("ov-mode-week");
  const m = document.getElementById("ov-mode-month");
  const wkP = document.getElementById("ov-week-picker");
  const moP = document.getElementById("ov-month-picker");
  if (mode === "week") {
    if (w) { w.style.background = "var(--accent)"; w.style.color = "#fff"; w.style.border = "none"; }
    if (m) { m.style.background = "var(--bg-elevated)"; m.style.color = "var(--text-muted)"; m.style.border = "1px solid var(--border)"; }
    if (wkP) wkP.style.display = "";
    if (moP) moP.style.display = "none";
  } else {
    if (m) { m.style.background = "var(--accent)"; m.style.color = "#fff"; m.style.border = "none"; }
    if (w) { w.style.background = "var(--bg-elevated)"; w.style.color = "var(--text-muted)"; w.style.border = "1px solid var(--border)"; }
    if (wkP) wkP.style.display = "none";
    if (moP) moP.style.display = "";
  }
  if (mode === "month" && moP && !moP.value) moP.value = getPreviousMonthValue();
  if (mode === "week" && wkP && !wkP.value) wkP.value = getPreviousWeekDate();
  const entryBtn = document.getElementById("metric-entry-btn");
  if (entryBtn) entryBtn.textContent = mode === "month" ? "录入月度数据" : "录入周度数据";
  onOvFilterChange();
}

function onOvFilterChange() {
  const mode = ovCurrentMode || "week";
  const wkP = document.getElementById("ov-week-picker");
  const moP = document.getElementById("ov-month-picker");
  const lbl = document.getElementById("ov-period-label");
  let start, end;
  if (mode === "month" && moP && moP.value) {
    const parts = moP.value.split("-");
    start = end = moP.value + "-01";
    if (lbl) lbl.textContent = `显示 ${parts[0]}年${parts[1]}月`;
  } else if (wkP && wkP.value) {
    start = end = wkP.value;
    if (lbl) lbl.textContent = `显示 ${wkP.value} 周`;
  } else {
    loadDashboard();
    return;
  }
  loadDashboard(start, end);
}

function toggleSubmenu(el) {
  const sidebarItem = el.closest(".sidebar-item");
  const submenuId = sidebarItem?.dataset.page;
  if (!submenuId) return;
  const submenu = document.querySelector(`[data-submenu="${submenuId}"]`);
  if (submenu) {
    submenu.classList.toggle("open");
    el.setAttribute("aria-expanded", submenu.classList.contains("open") ? "true" : "false");
  }
  el.textContent = submenu?.classList.contains("open") ? "▾" : "▸";
}

function switchTrendTab(platform) {
  document.querySelectorAll("#dashtab-trend .detail-tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");
  loadDashboardDetail(null, platform);
}

// ========== 运营总览（独立页面 · NovaChain 六卡） ==========
let ncMode = "week";

function switchNcMode(mode) {
  ncMode = mode;
  const w = document.getElementById("nc-mode-week");
  const m = document.getElementById("nc-mode-month");
  const on = { background: "var(--accent)", color: "#fff", border: "none" };
  const off = { background: "var(--bg-elevated)", color: "var(--text-muted)", border: "1px solid var(--border)" };
  if (w) Object.assign(w.style, mode === "week" ? on : off);
  if (m) Object.assign(m.style, mode === "month" ? on : off);
  loadOverviewNC();
}

function platColor(p) {
  return { 抖音: "#2563EB", 视频号: "#D97706", 公众号: "#059669", 小红书: "#DC2626" }[p] || "#2563EB";
}

async function loadOverviewNC() {
  const mode = ncMode || "week";
  const wrap = document.getElementById("nc-team");
  if (!wrap) return;
  ["nc-team", "nc-platforms", "nc-stats", "nc-accounts", "nc-hot", "nc-leads"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '<div class="nc-loading">加载中…</div>';
  });
  const lbl = document.getElementById("nc-period-label");
  if (lbl) lbl.textContent = mode === "month" ? "显示上月数据" : "显示上周数据";

  try {
    const [ovR, hotR, leadsR] = await Promise.all([
      fetch(API + "/dashboard/overview?mode=" + mode),
      fetch(API + "/dashboard/hot-content?mode=" + mode),
      fetch(API + "/leads/recent?limit=5"),
    ]);
    const ov = (await ovR.json()).data || [];
    const hot = (await hotR.json()).data || {};
    const leads = (await leadsR.json()).data || [];

    const trendResults = {};
    const accResults = {};
    await Promise.all(PLATFORMS.map(async (p) => {
      const [tR, aR] = await Promise.all([
        fetch(API + `/dashboard/trend?platform=${encodeURIComponent(p)}&mode=${mode}`),
        fetch(API + `/dashboard/platform-detail?platform=${encodeURIComponent(p)}&mode=${mode}`),
      ]);
      trendResults[p] = (await tR.json()).trend || [];
      const agg = await aR.json();
      accResults[p] = (agg.accounts_data || []).map(x => Object.assign({ platform: p }, x));
    }));

    renderNcTeam(ov, mode);
    renderNcPlatforms(ov);
    renderNcStats(ov, trendResults, mode);
    renderNcAccounts(accResults, mode);
    renderNcHot(hot);
    renderNcLeads(leads);
  } catch (e) {
    console.error(e);
    ["nc-team", "nc-platforms", "nc-stats", "nc-accounts", "nc-hot", "nc-leads"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<div class="nc-empty">加载失败，请刷新重试</div>';
    });
    toast("运营总览加载失败", "error");
  }
}

function renderNcTeam(data, mode) {
  const el = document.getElementById("nc-team");
  if (!el) return;
  const total = {
    followers: data.reduce((s, d) => s + (d.followers || 0), 0),
    plays: data.reduce((s, d) => s + (d.plays_reads || 0), 0),
    eng: data.reduce((s, d) => s + (d.engagement || 0), 0),
    pub: data.reduce((s, d) => s + (d.publish_count || 0), 0),
  };
  el.innerHTML = `
    <div class="nc-card-head"><span class="nc-card-title">团队数据</span><span class="nc-card-badge">${mode === "month" ? "月度" : "周度"}</span></div>
    <div class="nc-team-grid">
      <div class="nc-team-item"><div class="nc-team-label">总粉丝</div><div class="nc-team-val">${fmt(total.followers)}</div></div>
      <div class="nc-team-item"><div class="nc-team-label">播放/阅读</div><div class="nc-team-val">${fmt(total.plays)}</div></div>
      <div class="nc-team-item"><div class="nc-team-label">互动量</div><div class="nc-team-val">${fmt(total.eng)}</div></div>
      <div class="nc-team-item"><div class="nc-team-label">发布</div><div class="nc-team-val">${total.pub} 条</div></div>
    </div>
    <div class="nc-team-foot">4 平台账号统一汇总</div>`;
}

function renderNcPlatforms(data) {
  const el = document.getElementById("nc-platforms");
  if (!el) return;
  const platCls = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
  const total = data.reduce((s, d) => s + (d.plays_reads || 0), 0) || 1;
  const segs = data.map(d => ({ label: d.platform, value: d.plays_reads || 0, color: platColor(d.platform) }));
  const list = data.map(d => {
    const pct = Math.round((d.plays_reads || 0) / total * 100);
    const fw = d.plays_reads_wow || 0;
    return `
      <div class="nc-plat-row">
        <span class="nc-plat-dot ${platCls[d.platform] || ''}"></span>
        <span class="nc-plat-name">${d.platform}</span>
        <span class="nc-plat-val">${fmt(d.plays_reads)}</span>
        <span class="nc-plat-chg ${fw >= 0 ? "up" : "down"}">${fw >= 0 ? "↑" : "↓"}${Math.abs(fw)}%</span>
        <span class="nc-plat-pct">${pct}%</span>
      </div>`;
  }).join("");
  el.innerHTML = `
    <div class="nc-card-head"><span class="nc-card-title">平台数据</span><span class="nc-card-badge">播放/阅读占比</span></div>
    <div class="nc-plats-body">
      <div class="nc-ring">${buildRingSvg(segs)}</div>
      <div class="nc-plat-list">${list}</div>
    </div>`;
}

function mergeTrend(trendResults) {
  const map = {};
  PLATFORMS.forEach(p => {
    (trendResults[p] || []).forEach(t => {
      const key = t.date;
      if (!map[key]) map[key] = { label: t.label, date: key, plays_reads: 0, engagement: 0, followers: 0, publish_count: 0 };
      map[key].plays_reads += t.plays_reads || 0;
      map[key].engagement += t.engagement || 0;
      map[key].followers = Math.max(map[key].followers, t.followers || 0);
      map[key].publish_count += t.publish_count || 0;
    });
  });
  return Object.values(map).sort((a, b) => (a.date < b.date ? -1 : 1));
}

function renderNcStats(data, trendResults, mode) {
  const el = document.getElementById("nc-stats");
  if (!el) return;
  const merged = mergeTrend(trendResults);
  const tFollow = data.reduce((s, d) => s + (d.new_followers || 0), 0);
  const tEng = data.reduce((s, d) => s + (d.engagement || 0), 0);
  const tPub = data.reduce((s, d) => s + (d.publish_count || 0), 0);
  el.innerHTML = `
    <div class="nc-card-head"><span class="nc-card-title">数据统计</span><span class="nc-card-badge">${mode === "month" ? "月度" : "周度"}汇总</span></div>
    <div class="nc-stats-metrics">
      <div class="nc-stats-m"><span>新增粉丝</span><b>${fmt(tFollow)}</b></div>
      <div class="nc-stats-m"><span>互动量</span><b>${fmt(tEng)}</b></div>
      <div class="nc-stats-m"><span>发布数</span><b>${tPub}</b></div>
    </div>
    <div class="nc-chart">${buildLineBarSvg(merged)}</div>`;
}

function renderNcAccounts(accResults, mode) {
  const el = document.getElementById("nc-accounts");
  if (!el) return;
  const gCls = { 抖音: "g-douyin", 视频号: "g-shipinhao", 公众号: "g-gzh", 小红书: "g-xhs" };
  const dCls = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
  let html = `<div class="nc-card-head"><span class="nc-card-title">各平台账号</span><span class="nc-card-badge">${mode === "month" ? "月度" : "周度"}</span></div>`;
  PLATFORMS.forEach(p => {
    const list = accResults[p] || [];
    const maxV = Math.max(...list.map(x => x.plays_reads || 0), 1);
    const block = list.map(a => {
      const pct = Math.max(3, Math.round((a.plays_reads || 0) / maxV * 100));
      return `
        <div class="nc-acc-row">
          <span class="nc-acc-name">${a.account}</span>
          <span class="nc-acc-track"><i style="width:${pct}%"></i></span>
          <span class="nc-acc-val">${fmt(a.plays_reads)}</span>
        </div>`;
    }).join("");
    html += `<div class="nc-acc-group ${gCls[p] || ''}">
      <div class="nc-acc-plat"><span class="nc-plat-dot ${dCls[p] || ''}"></span>${p}</div>
      ${block || '<div class="nc-empty">暂无数据</div>'}
    </div>`;
  });
  el.innerHTML = html;
}

function renderNcHot(hot) {
  const el = document.getElementById("nc-hot");
  if (!el) return;
  const platCls = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
  let html = `<div class="nc-card-head"><span class="nc-card-title">热门内容</span><span class="nc-card-badge">按平台 TOP5</span></div>`;
  PLATFORMS.forEach(p => {
    const items = hot[p] || [];
    html += `<div class="nc-lb-group"><div class="nc-lb-plat"><span class="nc-plat-dot ${platCls[p] || ''}"></span>${p}</div>`;
    if (!items.length) {
      html += '<div class="nc-empty">暂无内容</div>';
    } else {
      items.forEach((it, i) => {
        html += `
          <div class="nc-lb-row">
            <span class="nc-lb-rank ${i < 3 ? "top" : ""}">${i + 1}</span>
            <span class="nc-lb-title">${(it.title || "无标题").replace(/</g, "&lt;")}</span>
            <span class="nc-lb-val">${fmt(it.likes)} ❤</span>
          </div>`;
      });
    }
    html += `</div>`;
  });
  el.innerHTML = html;
}

function renderNcLeads(leads) {
  const el = document.getElementById("nc-leads");
  if (!el) return;
  const intentLabel = { 1: "低意向", 3: "中意向", 5: "高意向" };
  const rows = (leads || []).map(l => `
    <div class="nc-lead-row">
      <span class="nc-lead-name">${(l.name || "匿名").replace(/</g, "&lt;")}</span>
      <span class="nc-lead-src">${l.source || "—"}</span>
      <span class="nc-lead-intent i${l.intent || 0}">${intentLabel[l.intent] || "未定"}</span>
      <span class="nc-lead-owner">${l.owner || "—"}</span>
    </div>`).join("");
  el.innerHTML = `
    <div class="nc-card-head"><span class="nc-card-title">最新线索</span><span class="nc-card-badge">最近 5 条</span></div>
    ${rows || '<div class="nc-empty">暂无线索</div>'}`;
}

function buildRingSvg(segs) {
  const total = segs.reduce((s, x) => s + x.value, 0) || 1;
  const R = 42, C = 2 * Math.PI * R;
  let offset = 0;
  const arcs = segs.map(s => {
    const frac = s.value / total;
    const dash = frac * C;
    const el = `<circle r="${R}" cx="52" cy="52" fill="none" stroke="${s.color}" stroke-width="12"
      stroke-dasharray="${dash} ${C - dash}" stroke-dashoffset="${-offset}"
      transform="rotate(-90 52 52)"></circle>`;
    offset += dash;
    return el;
  }).join("");
  return `<svg viewBox="0 0 104 104" width="104" height="104" role="img" aria-label="平台播放阅读占比圆环">
    <circle r="${R}" cx="52" cy="52" fill="none" stroke="#EEF2F9" stroke-width="12"></circle>
    ${arcs}
    <text x="52" y="50" text-anchor="middle" font-size="15" font-weight="700" fill="#0F1B2D">${fmt(total)}</text>
    <text x="52" y="63" text-anchor="middle" font-size="8" fill="#64748B">播放/阅读</text>
  </svg>`;
}

function buildLineBarSvg(trend) {
  const W = 340, H = 110, pad = 8;
  const items = (trend || []).slice(-8);
  if (!items.length) return '<div class="nc-empty">暂无趋势数据</div>';
  const maxV = Math.max(...items.map(t => t.plays_reads || 0), 1);
  const maxE = Math.max(...items.map(t => t.engagement || 0), 1);
  const bw = (W - pad * 2) / items.length;
  const bars = items.map((t, i) => {
    const h = Math.max(4, (t.plays_reads || 0) / maxV * (H - 30));
    const x = pad + i * bw + bw * 0.22;
    return `<rect x="${x.toFixed(1)}" y="${(H - 12 - h).toFixed(1)}" width="${(bw * 0.56).toFixed(1)}" height="${h.toFixed(1)}" rx="3" fill="#2563EB" opacity="0.85"></rect>`;
  }).join("");
  const pts = items.map((t, i) => {
    const x = pad + i * bw + bw * 0.5;
    const y = H - 12 - Math.max(4, (t.engagement || 0) / maxE * (H - 30));
    return { x, y };
  });
  const poly = pts.length > 1 ? `<polyline points="${pts.map(p => p.x.toFixed(1) + "," + p.y.toFixed(1)).join(" ")}" fill="none" stroke="#DC2626" stroke-width="2"></polyline>` : "";
  const dots = pts.map(p => `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="2.6" fill="#DC2626"></circle>`).join("");
  const labels = items.map((t, i) => {
    const x = pad + i * bw + bw * 0.5;
    const short = (t.label || "").replace(/年/g, "").replace(/月/g, "/").replace(/第(\d+)周/g, "W$1");
    return `<text x="${x.toFixed(1)}" y="${H - 2}" text-anchor="middle" font-size="7.5" fill="#94A3B8">${short}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="110" role="img" aria-label="播放阅读与互动趋势">
    <line x1="${pad}" y1="${H - 12}" x2="${W - pad}" y2="${H - 12}" stroke="#E2E8F0"></line>
    ${bars}${poly}${dots}${labels}
  </svg>`;
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
      overview: "运营总览", dashboard: "数据看板", calendar: "内容排期",
      content: "内容明细", tasks: "任务管理",
      topics: "选题库", reports: "报表生成"
    };
    document.getElementById("page-title").textContent = titles[page] || page;

    switch(page) {
      case "overview": loadOverviewNC(); break;
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
    if (ovCurrentMode === "month") {
      // 按月维度：显示上月
      const now = new Date();
      const m = now.getMonth(); // 0-indexed, this is current month
      const lastMonth = m === 0 ? 12 : m;
      const lastYear = m === 0 ? now.getFullYear() - 1 : now.getFullYear();
      startWeek = endWeek = `${lastYear}-${String(lastMonth).padStart(2,'0')}-01`;
    } else {
      // 按周维度：显示上周
      const lw = new Date();
      lw.setDate(lw.getDate() - (lw.getDay() || 7) - 6);
      const y = lw.getFullYear();
      const mo = String(lw.getMonth() + 1).padStart(2, '0');
      const d = String(lw.getDate()).padStart(2, '0');
      startWeek = endWeek = `${y}-${mo}-${d}`;
    }
  }
  showSkeleton("overview-grid", "cards-4");
  showSkeleton("kpi-grid-container", "kpi-3");
  let url = API + "/dashboard/overview";
  if (startWeek && endWeek) url += `?start_week=${startWeek}&end_week=${endWeek}`;
  if (ovCurrentMode === "month") url += "&mode=month";

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
  window._pdMode = ovCurrentMode || "week";
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".sidebar-item[data-page]").forEach(i => i.classList.remove("active"));
  // Highlight dashboard sidebar item since this is accessed from dashboard
  const dashItem = document.querySelector('.sidebar-item[data-page="dashboard"]');
  if (dashItem) dashItem.classList.add("active");
  document.getElementById("page-platform-detail").classList.add("active");
  document.getElementById("page-title").textContent = "平台明细";
  const quickBtn = document.getElementById("pd-quick-entry-btn");
  if (quickBtn) {
    quickBtn.textContent = window._pdMode === "month" ? "快速录入本月" : "快速录入本周";
    quickBtn.onclick = () => openBatchEntry(window._pdPlatform || "抖音", window._pdMode || "week");
  }
  loadPlatformDetail(platform, window._pdMode || "week");
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

async function loadPlatformDetail(platform, mode) {
  mode = mode || window._pdMode || "week";
  document.getElementById("pd-platform-name").textContent = platform;
  document.getElementById("pd-title").textContent = `${platform} · 数据明细`;

  // Skeleton
  document.getElementById("pd-aggregate").innerHTML = Array(4).fill(0).map(() => '<div class="skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-stat"></div><div class="skeleton skeleton-text"></div></div>').join("");
  document.getElementById("pd-accounts").innerHTML = "";

  try {
    const r = await fetch(API + `/dashboard/platform-detail?platform=${encodeURIComponent(platform)}&mode=${encodeURIComponent(mode)}`);
    if (!r.ok) throw new Error("平台明细加载失败");
    const data = await r.json();
    renderPlatformDetail(data, platform, mode);
  } catch(e) {
    console.error(e);
    toast("平台明细加载失败", "error");
  }
}

function renderPlatformDetail(data, platform, mode) {
  mode = mode || window._pdMode || "week";
  const platClasses = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
  const cls = platClasses[platform] || "";
  const agg = data.aggregate;

  document.getElementById("pd-week-label").textContent = `${mode === "month" ? "本月汇总" : "本周汇总"} · ${data.accounts_data.length} 个账号`;

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
    const mode = ovCurrentMode || "week";
    const r = await fetch(API + `/dashboard/trend?platform=${encodeURIComponent(platform)}&account=${encodeURIComponent(account)}&mode=${mode}`);
    if (!r.ok) throw new Error("趋势数据加载失败");
    const { trend } = await r.json();
    const bars = $qs("#trend-bars");
    const barColor = platColor(platform);
    if (trend && trend.length) {
      const maxVal = Math.max(...trend.map(t => t.plays_reads || 0), 1);
      bars.innerHTML = trend.map(t => {
        const val = t.plays_reads || 0;
        const h = Math.max(4, (val / maxVal) * 120);
        return `
          <div data-tooltip="${t.label}: ${fmt(val)}" style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:4px">
            <div style="background:${barColor};border-radius:3px 3px 0 0;min-height:4px;height:${h}px;opacity:${0.3 + (h/120)*0.7};transition:height 0.3s"></div>
            <div style="font-size:9px;color:var(--text-muted);text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.label}</div>
          </div>`;
      }).join("");
    } else {
      bars.innerHTML = '<div class="empty-state" style="flex:1"><p>该平台暂无趋势数据</p></div>';
    }

    // 数据表格与柱状图使用同一份数据
    const tbody = $qs("#trend-table tbody");
    if (trend && trend.length) {
      tbody.innerHTML = trend.slice().reverse().map(t => `
        <tr>
          <td>${t.label}</td>
          <td>${fmt(t.plays_reads || 0)}</td>
          <td>${fmt(t.new_followers || 0)}</td>
          <td>${fmt(t.engagement || 0)}</td>
          <td>${t.publish_count || 0}</td>
          <td>${(t.completion_rate || 0).toFixed(1)}%</td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><p>该平台暂无数据</p></td></tr>';
    }
  } catch(e) { /* no data - silent */ }
}

// Top 5 — 「本周/月热门」与内容明细共享同一周期，点击条目跳转内容明细
async function loadHotContent() {
  const top5Div = $qs("#top5-container");
  if (!top5Div) return;
  top5Div.innerHTML = '<div class="empty-state"><p>加载中…</p></div>';
  try {
    ensureContentPeriodDefaults();
    const mode = $qs("#content-mode")?.value || "week";
    const week = $qs("#content-week")?.value || dateToIsoWeek(getPreviousWeekDate());
    const month = $qs("#content-month")?.value || getPreviousMonthValue();
    const url = mode === "month"
      ? API + `/dashboard/hot-content?mode=month&month=${month}`
      : API + `/dashboard/hot-content?mode=week&week=${week}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error("加载失败");
    const { data } = await r.json();
    // 周期标签 + 标题
    const titleEl = document.getElementById("hot-title");
    if (titleEl) titleEl.textContent = mode === "month" ? "本月热门" : "本周热门";
    const lbl = document.getElementById("hot-period-label");
    if (lbl) {
      if (mode === "month") {
        const [y, m] = month.split("-");
        lbl.textContent = `${y}年${Number(m)}月 · 与内容明细同周期`;
      } else {
        const [y, wk] = week.split("-W");
        lbl.textContent = `${y}年 第${Number(wk)}周 · 与内容明细同周期`;
      }
    }
    const platCls = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
    let html = "";
    PLATFORMS.forEach(plat => {
      const items = data[plat] || [];
      if (!items.length) return;
      html += `<div class="hot-plat-block">
        <div class="hot-plat-header">
          <span class="platform-badge ${platCls[plat] || ''}">${plat}</span>
          <span class="hot-plat-count">TOP5</span>
        </div>`;
      items.forEach((c, i) => {
        const rankCls = i === 0 ? 'r1' : i === 1 ? 'r2' : i === 2 ? 'r3' : 'rn';
        const viral = c.is_viral ? '<span class="content-item-viral" style="font-size:9px">爆款</span>' : '';
        html += `
        <div class="top-item hot-clickable" title="点击查看内容明细" onclick="gotoContentDetail(${c.id})">
          <div class="top-rank ${rankCls}">${i + 1}</div>
          <div class="top-info">
            <div class="tt">${c.title || '未命名'} ${viral}</div>
            <div class="tm">${c.author || c.platform} · ${c.publish_date} · 播放 ${fmt(c.impressions || 0)}</div>
          </div>
          <div class="top-stat-r">👍 ${fmt(c.likes)}</div>
        </div>`;
      });
      html += `</div>`;
    });
    top5Div.innerHTML = html || '<div class="empty-state"><h3>暂无热门内容</h3><p>录入内容数据后，各平台排名会自动出现</p></div>';
  } catch(e) {
    top5Div.innerHTML = '<div class="empty-state"><h3>暂无热门内容</h3><p>热门内容加载失败</p></div>';
  }
}

// 热门 → 内容明细 联动：切页 + 等待加载 + 滚动定位 + 高亮
async function gotoContentDetail(id) {
  const nav = document.querySelector('.sidebar-item[data-page="content"]');
  if (nav) nav.click();
  // 轮询等 loadContent 完成（异步 fetch + 渲染）
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 100));
    const row = document.querySelector(`.content-tbl-row[data-id="${id}"]`);
    if (row) {
      row.scrollIntoView({ behavior: "smooth", block: "center" });
      row.classList.add("highlight-flash");
      setTimeout(() => row.classList.remove("highlight-flash"), 2600);
      return;
    }
  }
  toast("该内容不在当前周期的内容明细中，请调整周期查看", "");
}
function gotoContentPage() {
  const nav = document.querySelector('.sidebar-item[data-page="content"]');
  if (nav) nav.click();
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
function dateToIsoWeek(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  const day = (d.getDay() + 6) % 7; // 周一=0
  const thurs = new Date(d);
  thurs.setDate(d.getDate() - day + 3);
  const jan1 = new Date(thurs.getFullYear(), 0, 1);
  const week = Math.ceil((((thurs - jan1) / 86400000) + 1) / 7);
  return `${d.getFullYear()}-W${String(week).padStart(2, "0")}`;
}
function ensureContentPeriodDefaults() {
  const mode = $qs("#content-mode")?.value || "week";
  const week = $qs("#content-week");
  const month = $qs("#content-month");
  if (mode === "month") {
    if (month && !month.value) month.value = getPreviousMonthValue();
  } else {
    if (week && !week.value) week.value = dateToIsoWeek(getPreviousWeekDate());
  }
}
function getWeekFilterRange(value) {
  if (!value) return { start: "", end: "" };
  const [y, w] = value.split("-W").map(Number);
  const jan4 = new Date(y, 0, 4);
  const monday = new Date(jan4); monday.setDate(jan4.getDate() - ((jan4.getDay() || 7) - 1) + (w - 1) * 7);
  const sunday = new Date(monday); sunday.setDate(monday.getDate() + 6);
  const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  return { start: iso(monday), end: iso(sunday) };
}
function getMonthFilterRange(value) {
  if (!value) return { start: "", end: "" };
  const [y, m] = value.split("-").map(Number);
  const last = new Date(y, m, 0);
  const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  return { start: `${value}-01`, end: iso(last) };
}
function getFilterRange(prefix) {
  const mode = document.getElementById(`${prefix}-mode`)?.value || "week";
  if (mode === "month") return getMonthFilterRange(document.getElementById(`${prefix}-month`)?.value);
  return getWeekFilterRange(document.getElementById(`${prefix}-week`)?.value);
}
function onPeriodFilterChange(prefix, loader) {
  const mode = document.getElementById(`${prefix}-mode`)?.value || "week";
  const week = document.getElementById(`${prefix}-week`), month = document.getElementById(`${prefix}-month`);
  if (week) week.style.display = mode === "week" ? "" : "none";
  if (month) month.style.display = mode === "month" ? "" : "none";
  loader();
}
function contentRowHtml(c) {
  const viral = c.is_viral ? '<span class="content-item-viral">爆款</span>' : '';
  const type = c.content_type ? `<span class="content-item-type">${c.content_type}</span>` : '';
  const title = (c.title || "未命名").replace(/</g, "&lt;");
  const date = (c.publish_date || "").slice(5); // MM-DD
  return `
  <div class="content-tbl-row" data-id="${c.id}">
    <span class="ct-date">${date}</span>
    <span class="ct-title">
      <span class="ct-title-text" title="${title.replace(/"/g, "&quot;")}">${title}</span>
      ${type}${viral}
    </span>
    <span class="ct-num">${fmt(c.impressions || 0)}</span>
    <span class="ct-num">${fmt(c.likes || 0)}</span>
    <span class="ct-num">${fmt(c.comments || 0)}</span>
    <span class="ct-num">${fmt(c.shares || 0)}</span>
    <span class="ct-act">
      <button type="button" class="ct-btn edit" title="编辑" aria-label="编辑这条内容" onclick="event.stopPropagation();editContent(${c.id})">✎</button>
      <button type="button" class="ct-btn del" title="删除" aria-label="删除这条内容" onclick="event.stopPropagation();deleteContent(${c.id})">🗑</button>
    </span>
  </div>`;
}

async function loadContent() {
  const container = $qs("#content-cards");
  if (!container) return;
  container.innerHTML = '<div class="empty-state"><p>加载中…</p></div>';
  const countEl = document.getElementById("content-count");
  if (countEl) countEl.textContent = "";
  try {
    ensureContentPeriodDefaults();
    const range = getFilterRange("content");
    // 按月/周周期下分页循环拉取全部内容，保证一屏内全部展示、不截断
    let data = [], page = 1;
    while (true) {
      const params = new URLSearchParams({ page_size: "100", page: String(page), start_date: range.start, end_date: range.end });
      const r = await fetch(API + "/content/detail?" + params.toString());
      if (!r.ok) throw new Error("加载失败");
      const j = await r.json();
      const batch = j.data || [];
      data = data.concat(batch);
      if (!batch.length || data.length >= (j.total || 0)) break;
      page++;
    }
    if (!data.length) {
      if (countEl) countEl.textContent = "共 0 条";
      container.innerHTML = `<div class="empty-state">
        <div class="empty-icon">&#128196;</div>
        <h3>暂无内容数据</h3>
        <p>录入已发布内容的播放量、点赞等数据，开始追踪表现</p>
        <button class="btn btn-primary btn-sm empty-cta" onclick="openContentForm()">录入第一条内容</button>
      </div>`;
      return;
    }
    if (countEl) countEl.textContent = `共 ${data.length} 条内容`;
    const platMap = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
    // 按平台分组
    const byPlat = {};
    data.forEach(d => { (byPlat[d.platform] = byPlat[d.platform] || []).push(d); });
    let html = "";
    PLATFORMS.forEach(plat => {
      const list = byPlat[plat] || [];
      if (!list.length) return;
      // 平台内按账号分组
      const byAcct = {};
      list.forEach(d => { const a = d.author || "未分配账号"; (byAcct[a] = byAcct[a] || []).push(d); });
      const platPlays = list.reduce((s, d) => s + (d.impressions || 0), 0);
      const platLikes = list.reduce((s, d) => s + (d.likes || 0), 0);
      const platEng = list.reduce((s, d) => s + (d.likes || 0) + (d.comments || 0) + (d.shares || 0), 0);
      const acctHtml = Object.keys(byAcct).map(acct => {
        const items = byAcct[acct];
        const acctPlays = items.reduce((s, d) => s + (d.impressions || 0), 0);
        const acctLikes = items.reduce((s, d) => s + (d.likes || 0), 0);
        return `
        <div class="content-acct-section">
          <div class="content-acct-section-head">
            <span class="content-acct-dot">${acct.slice(0, 1)}</span>
            <span class="content-acct-name">${acct}</span>
            <span class="content-acct-count">${items.length} 条 · 播放 ${fmt(acctPlays)} · 赞 ${fmt(acctLikes)}</span>
          </div>
          <div class="content-tbl">
            <div class="content-tbl-head">
              <span class="ct-date">日期</span>
              <span class="ct-title">标题 / 类型</span>
              <span class="ct-num">播放</span>
              <span class="ct-num">点赞</span>
              <span class="ct-num">评论</span>
              <span class="ct-num">分享</span>
              <span class="ct-act">操作</span>
            </div>
            ${items.map(contentRowHtml).join("")}
          </div>
        </div>`;
      }).join("");
      html += `<div class="content-plat-card ${platMap[plat] || ''}">
        <div class="content-plat-card-head">
          <span class="content-plat-card-name">
            <span class="platform-badge ${platMap[plat] || ''}">${plat}</span>
            <span class="content-plat-card-count">${list.length} 条内容</span>
          </span>
          <span class="content-plat-card-sum">播放 ${fmt(platPlays)} · 赞 ${fmt(platLikes)} · 互动 ${fmt(platEng)}</span>
        </div>
        ${acctHtml}
      </div>`;
    });
    container.innerHTML = html || '<div class="empty-state"><p>当前周期暂无内容</p></div>';
  } catch(e) {
    toast("内容数据加载失败", "error");
    container.innerHTML = '<div class="empty-state"><p>内容数据加载失败</p></div>';
  }
}

async function deleteContent(id) {
  if (!confirm("确定删除这条内容吗？删除后不可恢复。")) return;
  const r = await fetch(API + `/content/detail/${id}`, { method: "DELETE" });
  if (!r.ok) { toast("删除失败", "error"); return; }
  loadContent(); toast("内容已删除", "success");
}

async function editContent(id) {
  let item = null;
  try {
    const r = await fetch(API + `/content/detail?page_size=100`);
    if (!r.ok) throw new Error("加载失败");
    const { data } = await r.json();
    item = data.find(x => x.id === id);
  } catch(e) { toast("获取内容详情失败", "error"); return; }
  if (!item) { toast("未找到该内容", "error"); return; }
  const mid = "content-edit-" + Date.now();
  const acctOpts = (ACCOUNTS[item.platform] || ["未分配账号"]).map(a => `<option ${item.author === a ? "selected" : ""}>${a}</option>`).join("");
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>编辑内容明细</h2>
    <div class="form-group"><label>标题</label><input id="ec-title" value="${(item.title || "").replace(/"/g, "&quot;")}"></div>
    <div class="form-group"><label>平台</label><select id="ec-plat" onchange="updateAccountSelect('ec-plat','ec-acct')">${PLATFORMS.map(p=>`<option ${p===item.platform?"selected":""}>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>账号</label><select id="ec-acct">${acctOpts}</select></div>
    <div class="form-group"><label>发布日期</label><input type="date" id="ec-date" value="${item.publish_date || ""}"></div>
    <div class="form-group"><label>播放/曝光</label><input type="number" id="ec-imp" value="${item.impressions || 0}"></div>
    <div class="form-group"><label>点赞</label><input type="number" id="ec-likes" value="${item.likes || 0}"></div>
    <div class="form-group"><label>评论</label><input type="number" id="ec-comments" value="${item.comments || 0}"></div>
    <div class="form-group"><label>分享</label><input type="number" id="ec-shares" value="${item.shares || 0}"></div>
    <div class="form-group"><label>备注</label><textarea id="ec-notes">${(item.notes || "").replace(/</g, "&lt;")}</textarea></div>
    <div class="form-actions">
      <button type="button" class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button type="button" class="btn btn-primary btn-sm" onclick="saveContentEdit(${id},'${mid}')">保存修改</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
  updateAccountSelect("ec-plat", "ec-acct");
}

async function saveContentEdit(id, modalId) {
  const acctEl = $qs("#ec-acct");
  const body = {
    title: $qs("#ec-title").value,
    platform: $qs("#ec-plat").value,
    publish_date: $qs("#ec-date").value || undefined,
    author: acctEl ? acctEl.value : undefined,
    impressions: +($qs("#ec-imp").value) || 0,
    likes: +($qs("#ec-likes").value) || 0,
    comments: +($qs("#ec-comments").value) || 0,
    shares: +($qs("#ec-shares").value) || 0,
    notes: $qs("#ec-notes").value,
  };
  try {
    const r = await fetch(API + `/content/detail/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId);
    loadContent();
    toast("内容已更新", "success");
  } catch(e) { toast("保存失败，请重试", "error"); }
}

// ========== CALENDAR ==========
let calView = "list";
function loadCalendar() {
  ensureCalPeriodDefaults();
  if (calView === "cal") loadMonthCalendarFromPicker();
  else loadCalendarList();
}
function ensureCalPeriodDefaults() {
  const mode = $qs("#cal-mode")?.value || "week";
  const week = $qs("#cal-week"), month = $qs("#cal-month");
  if (mode === "month") { if (month && !month.value) month.value = getPreviousMonthValue(); }
  else { if (week && !week.value) week.value = dateToIsoWeek(getPreviousWeekDate()); }
}
function onCalModeChange() {
  const mode = $qs("#cal-mode")?.value || "week";
  const week = $qs("#cal-week"), month = $qs("#cal-month");
  if (week) week.style.display = mode === "week" ? "" : "none";
  if (month) month.style.display = mode === "month" ? "" : "none";
  ensureCalPeriodDefaults();
  loadCalendar();
}
function switchCalendarView(view) {
  calView = view;
  const lb = document.getElementById("cal-view-list"), cb = document.getElementById("cal-view-cal");
  if (lb) lb.classList.toggle("active", view === "list");
  if (cb) cb.classList.toggle("active", view === "cal");
  const listEl = document.getElementById("calendar-list"), calEl = document.getElementById("calendar-card");
  if (listEl) listEl.style.display = view === "list" ? "" : "none";
  if (calEl) calEl.style.display = view === "cal" ? "" : "none";
  loadCalendar();
}
function calRowHtml(c) {
  const statusCls = { "待策划": "muted", "制作中": "blue", "待审核": "warn", "待发布": "purple", "已发布": "done" }[c.status] || "muted";
  const type = c.content_type ? `<span class="content-item-type">${c.content_type}</span>` : "";
  const title = (c.title || "未命名").replace(/</g, "&lt;");
  return `
  <div class="cal-tbl-row" data-id="${c.id}">
    <span class="cal-c-date">${(c.scheduled_date || "").slice(5)}</span>
    <span class="cal-c-title"><span class="ct-title-text" title="${title.replace(/"/g, "&quot;")}">${title}</span>${type}</span>
    <span class="cal-c-status"><span class="cal-status ${statusCls}">${c.status}</span></span>
    <span class="cal-c-assignee">${c.assignee || "—"}</span>
    <span class="cal-c-act">
      <button type="button" class="ct-btn edit" title="编辑" aria-label="编辑排期" onclick="event.stopPropagation();editCalendar(${c.id})">✎</button>
      <button type="button" class="ct-btn del" title="删除" aria-label="删除排期" onclick="event.stopPropagation();deleteCalendar(${c.id})">🗑</button>
    </span>
  </div>`;
}
async function loadCalendarList() {
  const container = document.getElementById("calendar-list");
  if (!container) return;
  container.innerHTML = '<div class="empty-state"><p>加载中…</p></div>';
  const countEl = document.getElementById("cal-count");
  if (countEl) countEl.textContent = "";
  ensureCalPeriodDefaults();
  const mode = $qs("#cal-mode")?.value || "week";
  let start, end;
  if (mode === "month") {
    const rng = getMonthFilterRange($qs("#cal-month")?.value || getPreviousMonthValue());
    start = rng.start; end = rng.end;
  } else {
    const rng = getWeekFilterRange($qs("#cal-week")?.value || dateToIsoWeek(getPreviousWeekDate()));
    start = rng.start; end = rng.end;
  }
  try {
    const r = await fetch(API + `/content/calendar?start_date=${start}&end_date=${end}`);
    if (!r.ok) throw new Error("加载失败");
    const { data } = await r.json();
    if (countEl) countEl.textContent = `共 ${data.length} 条排期`;
    if (!data.length) {
      container.innerHTML = `<div class="empty-state">
        <h3>该周期暂无排期</h3>
        <p>点击右上角"新建排期"添加，或切换到日历视图查看</p></div>`;
      return;
    }
    const platMap = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
    const byPlat = {};
    data.forEach(d => { (byPlat[d.platform] = byPlat[d.platform] || []).push(d); });
    let html = "";
    PLATFORMS.forEach(p => {
      const list = byPlat[p] || [];
      if (!list.length) return;
      const byAcct = {};
      list.forEach(d => { const a = d.assignee || "未分配"; (byAcct[a] = byAcct[a] || []).push(d); });
      const waitPublish = list.filter(x => x.status === "待发布").length;
      const making = list.filter(x => x.status === "制作中").length;
      const acctHtml = Object.keys(byAcct).map(acct => `
        <div class="content-acct-section">
          <div class="content-acct-section-head">
            <span class="content-acct-dot">${acct.slice(0, 1)}</span>
            <span class="content-acct-name">${acct}</span>
            <span class="content-acct-count">${byAcct[acct].length} 条排期</span>
          </div>
          <div class="cal-tbl">
            <div class="cal-tbl-head">
              <span>日期</span><span>标题 / 类型</span><span>状态</span><span>负责人</span><span>操作</span>
            </div>
            ${byAcct[acct].map(calRowHtml).join("")}
          </div>
        </div>`).join("");
      html += `<div class="content-plat-card ${platMap[p] || ''}">
        <div class="content-plat-card-head">
          <span class="content-plat-card-name">
            <span class="platform-badge ${platMap[p] || ''}">${p}</span>
            <span class="content-plat-card-count">${list.length} 条排期</span>
          </span>
          <span class="content-plat-card-sum">待发布 ${waitPublish} · 制作中 ${making}</span>
        </div>
        ${acctHtml}
      </div>`;
    });
    container.innerHTML = html;
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><p>排期加载失败</p></div>';
  }
}
function loadMonthCalendarFromPicker() {
  const month = $qs("#cal-month")?.value;
  if (month) { const [y, m] = month.split("-"); loadMonthCalendar(+y, +m - 1); }
  else loadMonthCalendar();
}

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
      <div class="form-group"><label>标题</label><input id="ce-title" value="${(item.title || "").replace(/"/g, "&quot;")}"></div>
      <div class="form-group"><label>平台</label><select id="ce-platform">${PLATFORMS.map(p=>`<option ${p===item.platform?"selected":""}>${p}</option>`).join("")}</select></div>
      <div class="form-group"><label>内容类型</label><select id="ce-type">${["短视频","图文","长文章","笔记"].map(t=>`<option ${t===item.content_type?"selected":""}>${t}</option>`).join("")}</select></div>
      <div class="form-group"><label>排期日期</label><input type="date" id="ce-date" value="${item.scheduled_date || ""}"></div>
      <div class="form-group"><label>状态</label><select id="ce-status">
        ${["待策划","制作中","待审核","待发布","已发布"].map(s => `<option ${item.status===s?'selected':''}>${s}</option>`).join("")}
      </select></div>
      <div class="form-group"><label>负责人</label><input id="ce-assignee" value="${(item.assignee||'').replace(/"/g, "&quot;")}"></div>
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
    title: $qs("#ce-title").value,
    platform: $qs("#ce-platform").value,
    content_type: $qs("#ce-type").value,
    scheduled_date: $qs("#ce-date").value,
    status: $qs("#ce-status").value,
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
        <td><button type="button" class="btn btn-outline btn-sm" onclick="event.stopPropagation();editTopic(${d.id})">编辑</button> <button type="button" class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteTopic(${d.id})">删除</button> ${d.status==='待评估'?`<button class="btn btn-primary btn-sm" onclick="openTopicToCal(${d.id},'${d.title.replace(/'/g,"\\'")}')">转为排期</button>`:''}</td>
      </tr>
    `).join("");
  } catch(e) { toast("选题数据加载失败", "error"); }
}

async function deleteTopic(id) {
  if (!confirm("确定删除这个选题吗？删除后不可恢复。")) return;
  const r = await fetch(API + `/topics/${id}`, { method: "DELETE" });
  if (!r.ok) { toast("删除失败", "error"); return; }
  loadTopics(); toast("选题已删除", "success");
}
async function editTopic(id) {
  const r = await fetch(API + "/topics?page_size=100");
  const { data } = await r.json();
  const item = data.find(x => x.id === id);
  if (!item) { toast("未找到选题", "error"); return; }
  const mid = "topic-edit-" + Date.now();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>编辑选题</h2>
    <div class="form-group"><label>标题</label><input id="et-title" value="${item.title || ""}"></div>
    <div class="form-group"><label>来源</label><input id="et-source" value="${item.source || ""}"></div>
    <div class="form-group"><label>适配平台</label><input id="et-platforms" value="${item.platforms || ""}"></div>
    <div class="form-group"><label>优先级</label><select id="et-priority">${["高","中","低"].map(v => `<option ${item.priority===v?"selected":""}>${v}</option>`).join("")}</select></div>
    <div class="form-group"><label>状态</label><select id="et-status">${["待评估","已采纳","已发布"].map(v => `<option ${item.status===v?"selected":""}>${v}</option>`).join("")}</select></div>
    <div class="form-group"><label>备注</label><textarea id="et-notes">${item.notes || ""}</textarea></div>
    <div class="form-actions"><button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button><button class="btn btn-primary btn-sm" onclick="saveTopicEdit(${id},'${mid}')">保存修改</button></div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}
async function saveTopicEdit(id, modalId) {
  const body = { title: $qs("#et-title").value, source: $qs("#et-source").value, platforms: $qs("#et-platforms").value, priority: $qs("#et-priority").value, status: $qs("#et-status").value, notes: $qs("#et-notes").value };
  const r = await fetch(API + `/topics/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) { toast("保存失败", "error"); return; }
  closeModal(modalId); loadTopics(); toast("选题已更新", "success");
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
async function openBatchEntry(platform, mode) {
  mode = mode || window._pdMode || "week";
  const accts = ACCOUNTS[platform] || ["主号"];
  const periodValue = mode === "month" ? getPreviousMonthValue() : getLastWeek();

  // 查询同一维度的上一期数据作为参考，周月互不混用
  let lastPeriodData = {};
  try {
    const refDate = mode === "month" ? `${getPreviousMonthValue()}-01` : (() => {
      const lastMon = new Date(); lastMon.setDate(lastMon.getDate() - lastMon.getDay() - 6);
      const y = lastMon.getFullYear(); const m = String(lastMon.getMonth()+1).padStart(2,"0"); const d = String(lastMon.getDate()).padStart(2,"0");
      return `${y}-${m}-${d}`;
    })();
    const r = await fetch(API + `/data/metrics?platform=${encodeURIComponent(platform)}&start_date=${refDate}&limit=50`);
    if (r.ok) {
      const { data } = await r.json();
      data.forEach(row => { lastPeriodData[row.account || ""] = row; });
    }
  } catch(e) {}

  let rows = accts.map((a, i) => {
    const prev = lastPeriodData[a] || {};
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
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:680px"><h2>${platform} · 快速录入${mode === "month" ? "本月" : "本周"}数据</h2>
    <div class="form-group"><label>${mode === "month" ? "月份" : "周次"}</label><input type="${mode === "month" ? "month" : "week"}" id="b-period" value="${periodValue}" style="width:200px"></div>
    <div class="batch-container">${rows}</div>
    <div style="font-size:10px;color:var(--text-muted);margin:8px 0">已填入${mode === "month" ? "上月" : "上周"}数据作为参考，修改后保存；周度与月度数据分别统计</div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveBatch('${mid}','${platform.replace(/'/g,"\\'")}',${accts.length},'${mode}')">一键保存全部</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveBatch(modalId, platform, count, mode) {
  mode = mode || window._pdMode || "week";
  const periodEl = document.querySelector(`#${modalId} #b-period`);
  const period = periodEl?.value || "";
  if (!period) { toast(mode === "month" ? "请选择月份" : "请选择周次", "error"); return; }
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
      week: mode === "month" ? `${period}-01` : period, platform, account: acctName,
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
  if (window._pdPlatform) loadPlatformDetail(window._pdPlatform, mode);
  else loadDashboard();
}

// ========== DATA ENTRY (P1: new metric form) ==========
function openMetricForm(mode) {
  mode = mode || ovCurrentMode || "week";
  const mid = "metric-" + Date.now();
  const thisWeek = getPreviousWeekDate();
  const thisMonth = getPreviousMonthValue();
  const isMonth = mode === "month";
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal"><h2>${isMonth ? '录入本月数据' : '录入本周数据'}</h2>
    <div class="form-group"><label>平台 <span class="required">*</span></label><select id="mf-plat" onchange="updateAccountSelect('mf-plat','mf-acct');togglePlatformFields()">${PLATFORMS.map(p=>`<option>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>账号</label><select id="mf-acct"></select></div>
    ${isMonth ? `
    <div class="form-group"><label>月份 <span class="required">*</span></label><input type="month" id="mf-month" value="${thisMonth}"><span class="error-msg">请选择月份</span></div>
    <div style="font-size:11px;color:var(--text-warning);margin:-4px 0 10px 0">整月汇总数据会保存为该月 1 号的记录，请与按周录入分开使用，避免重复统计。</div>`
    : `
    <div class="form-group"><label>周次 <span class="required">*</span></label><input type="week" id="mf-week" value="${thisWeek}"><span class="error-msg">请选择周次</span></div>`}
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
      <button class="btn btn-primary btn-sm" onclick="saveMetric('${mid}','${mode}')">保存数据</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
  updateAccountSelect('mf-plat','mf-acct');
  togglePlatformFields();
}

function togglePlatformFields() {
  const plat = document.getElementById("mf-plat").value;
  const show = (id, v) => { const el = document.getElementById(id); if (el) el.style.display = v ? "" : "none"; };
  show("mf-bookmark-group", plat === "小红书" || plat === "抖音" || plat === "公众号");
  show("mf-home-group", plat === "抖音");
  show("mf-comp-group", plat === "抖音" || plat === "视频号");
  show("mf-heart-group", plat === "视频号");
}

async function saveMetric(modalId, mode) {
  mode = mode || "week";
  const platEl = document.getElementById("mf-plat");
  const acctEl = document.getElementById("mf-acct");
  if (!platEl || (mode === "month" ? !document.getElementById("mf-month")?.value : !document.getElementById("mf-week")?.value)) {
    toast(mode === "month" ? "请选择平台和月份" : "请选择平台和周次", "error"); return;
  }
  const week = mode === "month" ? `${document.getElementById("mf-month").value}-01` : document.getElementById("mf-week").value;
  const body = {
    week,
    platform: platEl.value,
    account: acctEl.value,
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
    <div class="form-group"><label>平台 <span class="required">*</span></label><select id="cf-plat" onchange="updateAccountSelect('cf-plat','cf-acct')">${PLATFORMS.map(p=>`<option>${p}</option>`).join("")}</select></div>
    <div class="form-group"><label>账号 <span class="required">*</span></label><select id="cf-acct"></select></div>
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
  updateAccountSelect("cf-plat", "cf-acct");
}

async function saveContent(modalId) {
  if (!validateForm(modalId, ["cf-title", "cf-plat", "cf-date"])) {
    toast("请填写标题、平台和日期", "error"); return;
  }
  const acctEl = $qs("#cf-acct");
  const body = {
    title: $qs("#cf-title").value, platform: $qs("#cf-plat").value,
    content_type: $qs("#cf-type").value, publish_date: $qs("#cf-date").value,
    url: $qs("#cf-url").value, impressions: +$qs("#cf-imp").value||0,
    likes: +$qs("#cf-likes").value||0, author: acctEl ? acctEl.value : $qs("#cf-author").value,
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

// ========== BATCH ENTRY: Content / Calendar / Topics ==========
function openBatchTopicForm() {
  const mid = "bt-" + Date.now();
  const PLAT = ["抖音","视频号","公众号","小红书"];
  const rows = Array(10).fill(0).map((_, i) => `
    <div class="batch-row">
      <input class="bt-title" placeholder="选题标题" style="flex:2">
      <select class="bt-plat" style="flex:1">${PLAT.map(p=>`<option>${p}</option>`).join("")}</select>
      <select class="bt-status" style="flex:1"><option>待评估</option><option>已采纳</option><option>已发布</option></select>
      <input class="bt-cat" placeholder="分类" style="flex:1">
      <input class="bt-note" placeholder="备注" style="flex:2">
    </div>`).join("");
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:780px">
    <h2>批量录入选题</h2>
    <div class="batch-container">${rows}</div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveBatchTopics('${mid}')">全部保存</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveBatchTopics(modalId) {
  const items = [];
  document.querySelectorAll(`#${modalId} .batch-row`).forEach(row => {
    const title = row.querySelector(".bt-title").value.trim();
    if (!title) return;
    items.push({
      title,
      platforms: row.querySelector(".bt-plat").value,
      status: row.querySelector(".bt-status").value,
      source: "灵感",
      creator: row.querySelector(".bt-cat")?.value || "",
      notes: row.querySelector(".bt-note").value,
    });
  });
  if (!items.length) { toast("请至少填写一个选题标题", "error"); return; }
  try {
    const r = await fetch(API + "/batch/topic", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(items) });
    if (!r.ok) throw new Error("");
    const result = await r.json();
    closeModal(modalId);
    toast(`已录入 ${result.count} 条选题`, "success");
    loadTopics();
  } catch(e) { toast("批量录入失败", "error"); }
}

function openBatchCalendarForm() {
  const mid = "bc-" + Date.now();
  const PLAT = ["抖音","视频号","公众号","小红书"];
  const today = new Date().toISOString().split('T')[0];
  const rows = Array(10).fill(0).map((_, i) => `
    <div class="batch-row">
      <input class="bc-title" placeholder="事件标题" style="flex:2">
      <select class="bc-plat" style="flex:1">${PLAT.map(p=>`<option>${p}</option>`).join("")}</select>
      <input type="date" class="bc-date" value="${today}" style="flex:1.3">
      <input class="bc-person" placeholder="负责人" style="flex:1">
      <select class="bc-status" style="flex:1"><option>待策划</option><option>制作中</option><option>待审核</option><option>待发布</option></select>
      <input class="bc-desc" placeholder="描述(选填)" style="flex:2">
    </div>`).join("");
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:800px">
    <h2>批量录入内容排期</h2>
    <div class="batch-container">${rows}</div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveBatchCalendar('${mid}')">全部保存</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveBatchCalendar(modalId) {
  const items = [];
  document.querySelectorAll(`#${modalId} .batch-row`).forEach(row => {
    const title = row.querySelector(".bc-title").value.trim();
    if (!title) return;
    items.push({
      title,
      platform: row.querySelector(".bc-plat").value,
      content_type: "短视频",
      scheduled_date: row.querySelector(".bc-date").value,
      status: row.querySelector(".bc-status").value,
      assignee: row.querySelector(".bc-person").value,
      description: row.querySelector(".bc-desc").value,
    });
  });
  if (!items.length) { toast("请至少填写一个排期标题", "error"); return; }
  try {
    const r = await fetch(API + "/batch/calendar", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(items) });
    if (!r.ok) throw new Error("");
    const result = await r.json();
    closeModal(modalId);
    toast(`已录入 ${result.count} 条排期`, "success");
    loadCalendar(new Date().getFullYear(), new Date().getMonth() + 1);
  } catch(e) { toast("批量录入失败", "error"); }
}

function openBatchContentForm() {
  const mid = "bd-" + Date.now();
  const PLAT = ["抖音","视频号","公众号","小红书"];
  const today = new Date().toISOString().split('T')[0];
  const rows = Array(10).fill(0).map((_, i) => `
    <div class="batch-row">
      <input class="bd-title" placeholder="内容标题" style="flex:2.5">
      <select class="bd-plat" style="flex:1">${PLAT.map(p=>`<option>${p}</option>`).join("")}</select>
      <input type="date" class="bd-date" value="${today}" style="flex:1.2">
      <input class="bd-imp" type="number" placeholder="播放/阅读" style="flex:1">
      <input class="bd-likes" type="number" placeholder="点赞" style="flex:0.8">
      <input class="bd-comments" type="number" placeholder="评论" style="flex:0.8">
    </div>`).join("");
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:860px">
    <h2>批量录入内容明细</h2>
    <div class="batch-container">${rows}</div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveBatchContent('${mid}')">全部保存</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveBatchContent(modalId) {
  const items = [];
  document.querySelectorAll(`#${modalId} .batch-row`).forEach(row => {
    const title = row.querySelector(".bd-title").value.trim();
    if (!title) return;
    items.push({
      title,
      platform: row.querySelector(".bd-plat").value,
      content_type: "短视频",
      publish_date: row.querySelector(".bd-date").value,
      impressions: +row.querySelector(".bd-imp").value || 0,
      likes: +row.querySelector(".bd-likes").value || 0,
      comments: +row.querySelector(".bd-comments").value || 0,
    });
  });
  if (!items.length) { toast("请至少填写一个内容标题", "error"); return; }
  try {
    const r = await fetch(API + "/batch/detail", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(items) });
    if (!r.ok) throw new Error("");
    const result = await r.json();
    closeModal(modalId);
    toast(`已录入 ${result.count} 条内容`, "success");
    loadContent();
  } catch(e) { toast("批量录入失败", "error"); }
}

// ===== 内容明细 CSV/Excel 智能导入（自动识别各平台导出列名） =====
function openContentImport() {
  const mid = "content-import-" + Date.now();
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:540px">
    <h2>&#128229; 导入内容明细</h2>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:14px;line-height:1.7">
      支持从 <b>抖音 / 视频号 / 公众号 / 小红书</b> 后台导出的 Excel（.xlsx/.xls）或 CSV 文件，<br>
      系统会自动识别列名（标题、日期、平台、播放量、点赞、评论、分享、收藏、账号、备注等）并写入内容明细。
    </p>
    <div class="form-group">
      <label>文件所属平台（单平台导出文件无"平台"列时必选）</label>
      <select id="ci-platform" style="font-size:12px">
        <option value="">自动识别（文件含平台列时推荐）</option>
        <option>抖音</option><option>视频号</option><option>公众号</option><option>小红书</option>
      </select>
    </div>
    <div class="form-group">
      <label>默认账号（可选，文件无"账号"列时写入该负责人）</label>
      <input id="ci-account" placeholder="如：思格电网" style="font-size:12px">
    </div>
    <div class="form-group">
      <label>选择文件</label>
      <input type="file" id="ci-file" accept=".xlsx,.xls,.csv" style="font-size:12px;padding:8px;border:1px solid var(--border);border-radius:8px;background:var(--bg-surface)" onchange="guessPlatformByFilename(this)">
    </div>
    <div class="import-hint" style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:var(--bg-elevated);border-radius:10px;font-size:11px;color:var(--text-muted)">
      <span>&#128161;</span>
      <span>若导出的文件列名无法自动识别，可先下载模板整理后再导入</span>
    </div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="window.open('/api/content/import-template')">&#11015; 下载模板</button>
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="uploadContentImport('${mid}')">开始导入</button>
    </div>
    <div id="ci-result" style="margin-top:14px"></div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

// 根据文件名自动预选平台（视频号动态数据明细.csv → 视频号）
function guessPlatformByFilename(input) {
  const f = input && input.files && input.files[0];
  if (!f) return;
  const name = f.name;
  const sel = document.getElementById("ci-platform");
  if (!sel || sel.value) return;
  const guess = ["抖音", "视频号", "公众号", "小红书"].find(p => name.includes(p));
  if (guess) sel.value = guess;
}

async function uploadContentImport(modalId) {
  const input = document.getElementById("ci-file");
  const resultEl = document.getElementById("ci-result");
  if (!input || !input.files || !input.files.length) { toast("请先选择文件", "error"); return; }
  const file = input.files[0];
  resultEl.innerHTML = '<div class="empty-state" style="padding:16px"><p>导入中，请稍候…</p></div>';
  const fd = new FormData();
  fd.append("file", file);
  const platEl = document.getElementById("ci-platform");
  const acctEl = document.getElementById("ci-account");
  const qs = [];
  if (platEl && platEl.value) qs.push("platform=" + encodeURIComponent(platEl.value));
  if (acctEl && acctEl.value.trim()) qs.push("account=" + encodeURIComponent(acctEl.value.trim()));
  try {
    const r = await fetch(API + "/content/import" + (qs.length ? "?" + qs.join("&") : ""), { method: "POST", body: fd });
    const j = await r.json();
    if (!r.ok || j.ok === false) {
      resultEl.innerHTML = `<div style="padding:12px;background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.2);border-radius:10px;font-size:12px;color:var(--text-secondary)">
        <b style="color:var(--down)">导入失败：</b>${j.error || "未知错误"}</div>`;
      return;
    }
    let errHtml = "";
    if (j.errors && j.errors.length) {
      errHtml = `<div style="margin-top:8px;font-size:11px;color:var(--text-muted);line-height:1.6">${j.errors.slice(0, 5).map(e => `· 第 ${e.row} 行：${e.error}`).join("<br>")}</div>`;
    }
    const ok = j.imported > 0;
    resultEl.innerHTML = `<div style="padding:12px;background:${ok ? "rgba(16,185,129,.1)" : "rgba(245,158,11,.12)"};border:1px solid ${ok ? "rgba(16,185,129,.25)" : "rgba(245,158,11,.3)"};border-radius:10px;font-size:12px;color:var(--text-secondary)">
      <b style="color:${ok ? "#059669" : "#B45309"}">导入完成</b>：成功 ${j.imported} 条${j.skipped ? `，跳过 ${j.skipped} 条` : ""}（共 ${j.total} 行）${errHtml}</div>`;
    setTimeout(() => closeModal(modalId), 1600);
    loadContent();
    if (ok) toast(`成功导入 ${j.imported} 条内容`, "success");
  } catch(e) {
    resultEl.innerHTML = '<div style="padding:12px;background:rgba(220,38,38,.08);border-radius:10px;font-size:12px;color:var(--down)">网络错误，请重试</div>';
  }
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
async function uploadLeadsFile(input) {
  const file = input.files[0]; if (!file) return;
  const mode = $qs("#leads-mode")?.value || "week";
  let week = "", month = "", year = 0;
  if (mode === "week") week = $qs("#leads-week")?.value || getLastWeek();
  else if (mode === "month") month = $qs("#leads-month")?.value || getPreviousMonthValue();
  else if (mode === "year") {
    const yv = parseInt($qs("#leads-year")?.value);
    year = (yv >= 2020 && yv <= 2030) ? yv : new Date().getFullYear();
  }
  const params = new URLSearchParams({mode, week_val: week, month_val: month, year_val: year});
  const url = API + "/leads/upload?" + params;
  const formData = new FormData(); formData.append("file", file);
  toast("正在上传并解析...", "info");
  try {
    const r = await fetch(url, { method: "POST", body: formData });
    const result = await r.json();
    if (result.ok) {
      toast(`导入成功: ${result.imported} 条新增, 清除 ${result.deleted} 条旧数据`, "success");
      loadLeads();
    } else {
      const errMsg = result.error || result.detail?.[0]?.msg || "未知错误";
      toast("上传失败: " + errMsg, "error", 8000);
      console.error("Upload error:", result);
    }
  } catch(e) { toast("上传失败: " + (e.message || e), "error"); }
  input.value = "";
}

function onLeadsModeChange() {
  const mode = $qs("#leads-mode")?.value || "week";
  const wk = $qs("#leads-week"), mn = $qs("#leads-month"), yr = $qs("#leads-year");
  if (wk) wk.style.display = mode === "week" ? "" : "none";
  if (mn) mn.style.display = mode === "month" ? "" : "none";
  if (yr) yr.style.display = mode === "year" ? "" : "none";
  loadLeads();
}

async function loadLeads() {
  const mode = $qs("#leads-mode")?.value || "week";
  let week = "", month = "", year = 0;
  if (mode === "week") week = $qs("#leads-week")?.value || getCurrentWeekDate();
  else if (mode === "month") month = $qs("#leads-month")?.value || getCurrentMonthValue();
  else if (mode === "year") {
    const yv = parseInt($qs("#leads-year")?.value);
    year = (yv >= 2020 && yv <= 2030) ? yv : new Date().getFullYear();
  }
  const params = new URLSearchParams({mode, week_val: week, month_val: month, year_val: year});
  const s = await fetch(API + "/leads/summary?" + params);
  if (!s.ok) {
    console.error("Leads API failed:", s.status, await s.text().catch(() => ""));
    return;
  }
  const data = await s.json();

  // 4 张统计卡：总线索 / 有效 / 无效 / 待定
  document.getElementById("leads-cards").innerHTML = [
    { label: "总线索", val: data.total, cls: "" },
    { label: "有效线索", val: data.valid, cls: "up", sub: `有效率 ${data.valid_rate}%` },
    { label: "无效线索", val: data.invalid, cls: "down" },
    { label: "待跟进", val: data.pending, cls: "" },
  ].map(c => `<div class="stat-card">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value ${c.cls}">${c.val}</div>
    ${c.sub ? `<div class="stat-change up">${c.sub}</div>` : ''}
  </div>`).join("");

  // 渠道有效性汇总（两级：录入渠道 → 备注细分）
  const sv = (data.by_source_note || []).filter(s => s.total > 0);
  const summaryTable = (rows, nameKey) => `
    <div class="lead-table-head">
      <span>${nameKey}</span><span class="v">有效</span><span class="p">待定</span><span class="i">无效</span><span>有效率</span><span>意向1</span><span>意向3</span><span>意向5</span><span>合计</span>
    </div>
    ${rows.map(s => `
      <div class="lead-table-row">
        <span class="lt-name" title="${s.name}">${s.name}</span>
        <span class="lt-num v">${s.valid}</span>
        <span class="lt-num p">${s.pending}</span>
        <span class="lt-num i">${s.invalid}</span>
        <span class="lt-rate">${s.valid_rate}%</span>
        <span class="lt-num i1">${s.intent1}</span>
        <span class="lt-num i3">${s.intent3}</span>
        <span class="lt-num i5">${s.intent5}</span>
        <span class="lt-num">${s.total}</span>
      </div>`).join("")}`;
  // 两级渠道：渠道行 + 备注细分子行
  const srcNoteHtml = (rows) => `
    <div class="lead-table-head">
      <span>渠道 / 备注细分</span><span class="v">有效</span><span class="p">待定</span><span class="i">无效</span><span>有效率</span><span class="sub-hide">意向1</span><span class="sub-hide">意向3</span><span class="sub-hide">意向5</span><span>合计</span>
    </div>
    ${rows.map(s => `
      <div class="lead-table-row lead-src-row">
        <span class="lt-name lead-src-name">▾ ${s.name}</span>
        <span class="lt-num v">${s.valid}</span>
        <span class="lt-num p">${s.pending}</span>
        <span class="lt-num i">${s.invalid}</span>
        <span class="lt-rate">${s.valid_rate}%</span>
        <span class="sub-hide"></span><span class="sub-hide"></span><span class="sub-hide"></span>
        <span class="lt-num">${s.total}</span>
      </div>
      ${(s.subs || []).map(sub => `
        <div class="lead-table-row lead-sub-row">
          <span class="lt-name" title="${sub.name}">　└ ${sub.name}</span>
          <span class="lt-num v">${sub.valid}</span>
          <span class="lt-num p">${sub.pending}</span>
          <span class="lt-num i">${sub.invalid}</span>
          <span class="lt-rate">${sub.valid_rate}%</span>
          <span class="sub-hide"></span><span class="sub-hide"></span><span class="sub-hide"></span>
          <span class="lt-num">${sub.total}</span>
        </div>`).join("")}
    `).join("")}`;
  document.getElementById("leads-validity-summary").innerHTML = sv.length
    ? srcNoteHtml(sv) + `
      <div class="lead-table-foot">
        <span class="lt-name">总计</span>
        <span class="lt-num v">${data.valid}</span>
        <span class="lt-num p">${data.pending}</span>
        <span class="lt-num i">${data.invalid}</span>
        <span class="lt-rate">${data.valid_rate}%</span>
        <span class="sub-hide"></span><span class="sub-hide"></span><span class="sub-hide"></span>
        <span class="lt-num">${data.total}</span>
      </div>`
    : '<div class="empty-state"><p>暂无数据</p></div>';

  // 地区有效性汇总（含意向级别）
  const rv = (data.by_region_validity || []).filter(s => s.total > 0);
  document.getElementById("leads-region-summary").innerHTML = rv.length
    ? summaryTable(rv, "地区") + `
      <div class="lead-table-foot">
        <span class="lt-name">总计</span>
        <span class="lt-num v">${data.valid}</span>
        <span class="lt-num p">${data.pending}</span>
        <span class="lt-num i">${data.invalid}</span>
        <span class="lt-rate">${data.valid_rate}%</span>
        <span class="lt-num i1">${rv.reduce((a,b)=>a+(b.intent1||0),0)}</span>
        <span class="lt-num i3">${rv.reduce((a,b)=>a+(b.intent3||0),0)}</span>
        <span class="lt-num i5">${rv.reduce((a,b)=>a+(b.intent5||0),0)}</span>
        <span class="lt-num">${data.total}</span>
      </div>`
    : '<div class="empty-state"><p>暂无数据</p></div>';

  // 成单统计：与线索数据共用同一筛选维度（周/月/年联动）
  loadDeads(mode, week, month, year);
}

async function loadDeads(mode, week, month, year) {
  const params = new URLSearchParams({ mode, week_val: week || "", month_val: month || "", year_val: year || 0 });
  let d;
  try {
    const r = await fetch(API + "/leads/deals?" + params);
    if (!r.ok) throw new Error("fail");
    d = await r.json();
  } catch(e) {
    document.getElementById("deals-cards").innerHTML = '<div class="empty-state" style="grid-column:1/-1"><p>成单数据加载失败</p></div>';
    return;
  }
  const lbl = document.getElementById("deals-period-label");
  const periodTxt = mode === "month" ? (month || getCurrentMonthValue()) : mode === "year" ? (year || new Date().getFullYear()) : (week || getCurrentWeekDate());
  if (lbl) lbl.textContent = `与线索同周期（${periodTxt}）· 成单 ${d.total} 笔 · 金额 ¥${(d.total_amount||0).toLocaleString()}`;
  document.getElementById("deals-cards").innerHTML = [
    { label: "成单总数", val: d.total, cls: "" },
    { label: "成单总金额", val: "¥" + (d.total_amount||0).toLocaleString(), cls: "up" },
    { label: "当月成单", val: d.cur_month_count, cls: "", sub: "本月成交笔数" },
    { label: "当月金额", val: "¥" + (d.cur_month_amount||0).toLocaleString(), cls: "up", sub: "本月成交金额" },
  ].map(c => `<div class="stat-card">
    <div class="stat-label">${c.label}</div>
    <div class="stat-value ${c.cls}">${c.val}</div>
    ${c.sub ? `<div class="stat-change up">${c.sub}</div>` : ''}
  </div>`).join("");

  const rows = d.data || [];
  const platCls = { 抖音: "douyin", 视频号: "shipinhao", 公众号: "gzh", 小红书: "xhs" };
  document.getElementById("deals-table").innerHTML = rows.length ? `
    <div class="deal-table-head">
      <span>姓名</span><span>学校</span><span>年级</span><span>渠道来源</span><span>成单校区</span><span>成单金额</span><span>成单日期</span><span>当月成单</span><span>操作</span>
    </div>
    ${rows.map(x => `
      <div class="deal-table-row">
        <span class="dt-name">${x.name || "—"}</span>
        <span class="dt-school">${x.school || "—"}</span>
        <span class="dt-grade">${x.grade || "—"}</span>
        <span><span class="platform-badge ${platCls[x.source] || ''}">${x.source || "—"}</span></span>
        <span class="dt-campus">${x.campus || "—"}</span>
        <span class="dt-amount">¥${(x.amount||0).toLocaleString()}</span>
        <span class="dt-date">${x.deal_date}</span>
        <span>${x.is_current_month ? '<span class="cal-status done">当月</span>' : '<span class="cal-status muted">历史</span>'}</span>
        <span class="dt-act"><button type="button" class="ct-btn del" title="删除" onclick="deleteDeal(${x.id})">🗑</button></span>
      </div>`).join("")}`
    : '<div class="empty-state"><p>当前周期暂无成单，点击右上角"＋ 录入成单"添加</p></div>';
}

function openDealForm() {
  const mid = "deal-" + Date.now();
  const today = new Date().toISOString().split("T")[0];
  const html = `<div class="modal-overlay show" id="${mid}"><div class="modal" style="max-width:460px">
    <h2>录入成单</h2>
    <div class="form-group"><label>姓名 <span class="required">*</span></label><input id="dl-name" placeholder="学员姓名"><span class="error-msg">请输入姓名</span></div>
    <div class="form-group"><label>学校</label><input id="dl-school" placeholder="如：华中科技大学"></div>
    <div class="form-group"><label>年级</label><select id="dl-grade"><option value="">未选择</option><option>大一</option><option>大二</option><option>大三</option><option>大四</option><option>研究生</option></select></div>
    <div class="form-group"><label>渠道来源</label><select id="dl-source"><option>抖音</option><option>微信视频号</option><option>微信公众号</option><option>小红书</option></select></div>
    <div class="form-group"><label>成单校区</label><input id="dl-campus" placeholder="如：武汉校区 / 郑州校区"></div>
    <div class="form-group"><label>成单金额（元）</label><input type="number" id="dl-amount" placeholder="0" min="0"></div>
    <div class="form-group"><label>成单日期</label><input type="date" id="dl-date" value="${today}"></div>
    <div class="form-group"><label>负责人</label><input id="dl-owner" placeholder="可选"></div>
    <div class="form-actions">
      <button class="btn btn-outline btn-sm" onclick="closeModal('${mid}')">取消</button>
      <button class="btn btn-primary btn-sm" onclick="saveDeal('${mid}')">保存</button>
    </div>
  </div></div>`;
  document.body.insertAdjacentHTML("beforeend", html);
}

async function saveDeal(modalId) {
  if (!validateForm(modalId, ["dl-name"])) { toast("请填写姓名", "error"); return; }
  const body = {
    name: $qs("#dl-name").value,
    school: $qs("#dl-school").value,
    grade: $qs("#dl-grade").value,
    source: $qs("#dl-source").value,
    campus: $qs("#dl-campus").value,
    amount: +($qs("#dl-amount").value) || 0,
    deal_date: $qs("#dl-date").value,
    owner: $qs("#dl-owner").value,
  };
  try {
    const r = await fetch(API + "/leads/deals", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error("保存失败");
    closeModal(modalId);
    toast("成单已录入", "success");
    loadLeads();
  } catch(e) { toast("保存失败，请重试", "error"); }
}

async function deleteDeal(id) {
  if (!confirm("确定删除这条成单记录吗？")) return;
  const r = await fetch(API + `/leads/deals/${id}`, { method: "DELETE" });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.ok === false) { toast("删除失败", "error"); return; }
  toast("成单已删除", "success");
  loadLeads();
}

// ========== INIT ==========
loadDashboard();
