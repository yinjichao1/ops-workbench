/* ============================================================
 * 主应用 · 表单渲染 / 交互 / 校验 / 存档
 * ============================================================ */

const LS_KEY = 'sg_wangshen_sim_v1';

/* ---------------- 状态 ---------------- */
let DATA = JSON.parse(JSON.stringify(window.EMPTY_DATA));
let collapsed = {};        // 模块折叠状态
let tagOpen = {};          // 求职意向候选项展开状态
let errMap = {};           // path -> 错误消息
let dirty = false;

/* ---------------- 工具 ---------------- */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function toast(msg, type) {
  const t = $('#toast');
  t.className = 'toast show' + (type ? ' ' + type : '');
  t.textContent = msg;
  clearTimeout(t._tm);
  t._tm = setTimeout(() => { t.className = 'toast'; }, 2200);
}

/* ---------------- 渲染：通用字段 ---------------- */
function ctlHtml(f, val) {
  const p = f.p, id = 'f_' + p.replace(/\./g, '_');
  const common = `data-path="${p}" id="${id}"`;

  switch (f.type) {
    case 'select': {
      const opts = window.DICT[f.src] || [];
      let h = `<select ${common}${f.auto ? ` data-auto="${f.auto}"` : ''}><option value="">请选择</option>`;
      opts.forEach(o => { h += `<option value="${esc(o)}"${val === o ? ' selected' : ''}>${esc(o)}</option>`; });
      return h + '</select>';
    }
    case 'radio': {
      const opts = window.DICT[f.src] || [];
      let h = '<div class="radio-group">';
      opts.forEach(o => {
        const ck = val === o ? ' checked' : '';
        h += `<label><input type="radio" name="${id}" value="${esc(o)}" ${common}${ck}>${esc(o)}</label>`;
      });
      return h + '</div>';
    }
    case 'date':
      return `<input type="date" ${common} value="${esc(val)}">`;
    case 'textarea':
      return `<textarea ${common} maxlength="${f.max || 300}" placeholder="请输入">${esc(val)}</textarea>`;
    case 'region':
      return regionHtml(p, f.group, val);
    case 'tags':
      return tagsHtml(p, f, val);
    default: {
      const extra = [
        f.max ? `maxlength="${f.max}"` : '',
        f.numeric ? 'inputmode="numeric"' : '',
        f.ph ? `placeholder="${esc(f.ph)}"` : ''
      ].filter(Boolean).join(' ');
      return `<input type="text" ${common} value="${esc(val)}" ${extra}>`;
    }
  }
}

/* 省市区三级联动 */
function regionHtml(path, group, val) {
  const base = path.replace(/Prov$/, '');
  const p = window.getPath(DATA, base + 'Prov') || '';
  const c = window.getPath(DATA, base + 'City') || '';
  const d = window.getPath(DATA, base + 'Dist') || '';
  const provinces = (window.REGION_DATA || []).map(x => x.name);
  let pc = provinces.map(n => `<option value="${esc(n)}"${p === n ? ' selected' : ''}>${esc(n)}</option>`).join('');
  let cc = '', dc = '';
  if (p) {
    const pv = window.REGION_DATA.find(x => x.name === p);
    if (pv) cc = pv.cities.map(x => `<option value="${esc(x.name)}"${c === x.name ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    if (p && c) {
      const pv2 = window.REGION_DATA.find(x => x.name === p);
      const cv = pv2 && pv2.cities.find(x => x.name === c);
      if (cv) dc = cv.districts.map(x => `<option value="${esc(x)}"${d === x ? ' selected' : ''}>${esc(x)}</option>`).join('');
    }
  }
  return `<div class="region-row" data-region="${base}">
    <select data-rk="Prov" data-path="${base}Prov"><option value="">省/直辖市</option>${pc}</select>
    <select data-rk="City" data-path="${base}City"${!p ? ' disabled' : ''}><option value="">市</option>${cc}</select>
    <select data-rk="Dist" data-path="${base}Dist"${!c ? ' disabled' : ''}><option value="">区/县</option>${dc}</select>
  </div>`;
}

/* 求职意向标签 */
function tagsHtml(path, f, val) {
  const arr = Array.isArray(val) ? val : [];
  const limit = f.limit || 3;
  const open = !!tagOpen[path];
  let h = `<div class="tag-block" data-tagblock="${path}">`;
  h += `<div class="tag-picker" data-tags="${path}">`;
  if (arr.length) {
    arr.forEach(t => { h += `<span class="tag-chip">${esc(t)}<i data-rm="${esc(t)}">×</i></span>`; });
  } else {
    h += '<span class="ph">点击下方「展开候选项」选择求职意向</span>';
  }
  h += `<span class="count">${arr.length}/${limit}</span></div>`;
  h += `<div class="tag-more" data-more="${path}">${open ? '▲ 收起候选项' : '▼ 展开候选项（最多选 ' + limit + ' 个）'}</div>`;
  h += `<div class="tag-pool${open ? ' show' : ''}" data-pool="${path}">` +
    window.INTENTION_TAGS.map(t => `<span class="tag-chip" style="cursor:pointer;opacity:${arr.includes(t) ? .35 : 1}" data-add="${esc(t)}">${esc(t)}</span>`).join('') +
    '</div>';
  h += '</div>';
  return h;
}

/* ---------------- 渲染：表格模块 ---------------- */
function tableHtml(sec, rows) {
  const cols = sec.columns;
  let h = '<div class="tbl-wrap"><table class="dtbl"><thead><tr>';
  h += '<th class="tbl-pick"></th>';
  cols.forEach(c => { h += `<th>${esc(c.t)}</th>`; });
  h += '<th style="width:60px">操作</th></tr></thead><tbody id="tb_' + sec.id + '">';

  if (!rows.length) {
    h += `<tr><td class="tbl-empty" colspan="${cols.length + 2}">暂无数据，点击右上角「添加」录入</td></tr>`;
  } else {
    rows.forEach((r, i) => {
      h += '<tr>';
      h += `<td class="tbl-pick"><input type="radio" name="pick_${sec.id}" ${i === 0 ? 'checked' : ''}></td>`;
      cols.forEach(c => {
        let v = c.fmt ? c.fmt(r) : (r[c.k] == null ? '' : r[c.k]);
        if (c.k === 'file' && v) v = '📎 ' + v;
        h += `<td>${v === '' || v == null ? '<span style="color:#bbb">—</span>' : esc(v)}</td>`;
      });
      h += `<td><span class="row-del" data-del="${sec.id}" data-idx="${i}">🗑 删除</span></td>`;
      h += '</tr>';
    });
  }
  h += '</tbody></table></div>';
  return h;
}

/* ---------------- 渲染模块头 ---------------- */
function secHead(sec, count) {
  const isCollapsed = collapsed[sec.id];
  const tagCls = sec.req ? 'sec-tag' : 'sec-tag optional';
  const tagTxt = sec.req ? '必填' : '非必填';
  let tools = '';
  if (sec.kind === 'table') {
    tools = `<button class="sec-btn" data-act="add" data-sec="${sec.id}">⊕ 添加</button>
             <button class="sec-btn" data-act="edit" data-sec="${sec.id}">✎ 编辑</button>
             <button class="sec-btn danger" data-act="delrow" data-sec="${sec.id}">🗑 删除</button>
             <button class="sec-btn" data-act="clearall" data-sec="${sec.id}">清空</button>`;
  }
  return `<div class="sec-head" data-toggle="${sec.id}">
    <div class="sec-title">${esc(sec.title)}</div>
    <div class="sec-line"></div>
    <div class="sec-tools">${tools}
      <span class="${tagCls}" data-tag="${sec.id}">${tagTxt}</span>
      <span class="sec-arrow">⌃</span>
    </div>
  </div>`;
}

/* ---------------- 渲染整个表单 ---------------- */
function render() {
  const wrap = $('#formWrap');
  let h = '';

  window.SCHEMA.forEach(sec => {
    const isCollapsed = collapsed[sec.id];
    h += `<section class="sec${isCollapsed ? ' collapsed' : ''}" data-sec="${sec.id}">`;
    h += secHead(sec);
    h += '<div class="sec-body">';

    if (sec.kind === 'table') {
      const rows = DATA[sec.id] || [];
      h += tableHtml(sec, rows);
    } else if (sec.layout === 'grid-basic') {
      h += '<div class="grid grid-basic">';
      sec.fields.forEach(f => {
        const val = window.getPath(DATA, f.p);
        h += fieldHtml(f, val, 'basic');
      });
      // 照片列
      h += photoHtml();
      h += '</div>';
    } else {
      h += `<div class="grid${sec.layout === 'grid-2' ? ' grid-2' : ''}">`;
      sec.fields.forEach(f => {
        const val = window.getPath(DATA, f.p);
        h += fieldHtml(f, val);
      });
      h += '</div>';
    }

    h += '</div></section>';
  });

  /* 其他情况说明 */
  const o = window.OTHER_SECTION;
  h += `<section class="sec${collapsed[o.id] ? ' collapsed' : ''}" data-sec="${o.id}">`;
  h += secHead(o);
  h += `<div class="sec-body"><div class="form-tips">${esc(o.tip || '')}</div>
        <div class="field full"><div class="field-ctl">
        <textarea data-path="other" maxlength="${o.max}" placeholder="请输入其他需要说明的信息，最多${o.max}个字符">${esc(DATA.other || '')}</textarea>
        <div class="counter"><span data-cnt="other">${(DATA.other || '').length}</span>/${o.max}</div>
        <div class="err-msg"></div></div></div></div></section>`;

  wrap.innerHTML = h;
  applyErrors();
  updateProgress();
}

/* 单个字段 */
function fieldHtml(f, val) {
  const reqCls = f.noReq ? '' : '';
  const reqMark = f.noReq ? '' : '<span class="req">*</span>';
  const cls = ['field'];
  if (f.full) cls.push('full');
  if (f.span === 2) cls.push('span2');
  if (f.span === 3) cls.push('span3');
  const labelCls = 'field-label' + (f.labelTwo ? ' two-line' : '');
  let h = `<div class="${cls.join(' ')}" data-field="${f.p}">`;
  h += `<div class="${labelCls}">${reqMark}${esc(f.label)}</div>`;
  h += `<div class="field-ctl">${ctlHtml(f, val)}`;
  h += '<div class="err-msg"></div>';
  if (f.help) h += `<div class="field-help${f.helpGreen ? ' green' : ''}${f.helpLink ? ' link' : ''}">${esc(f.help)}</div>`;
  h += '</div></div>';
  return h;
}

/* 照片上传列 */
function photoHtml() {
  const ph = DATA.basic.photo;
  return `<div class="photo-col" data-field="basic.photo">
    <div class="photo-box" id="photoBox">
      ${ph ? `<img src="${ph}" alt="证件照">` : '<div class="ph-text">点击上传<br>证件照</div>'}
    </div>
    <input type="file" id="photoFile" accept="image/jpeg,image/png" style="display:none">
    <div class="photo-modify" id="photoModify">修改</div>
    <div class="photo-spec">
      尺寸<br>120*160px~600*800px<br>JPG、PNG文件<br>5~200kb<br>清晰的人脸头像
    </div>
    <div class="err-msg" style="text-align:center"></div>
  </div>`;
}

/* ---------------- 校验 ---------------- */
function validateAll() {
  errMap = {};
  window.RULES.forEach(r => {
    const v = window.getPath(DATA, r.path);
    let msg = '';
    try { msg = r.fn(v, DATA) || ''; } catch (e) { msg = ''; }
    if (msg) errMap[r.path] = msg;
  });
  return errMap;
}

/* 表格模块的校验（数据行） */
function validateTables() {
  const errs = [];
  const edu = DATA.education || [];
  if (!edu.length) errs.push({ sec: 'education', msg: '「教育经历」为必填模块，至少需添加 1 条记录' });
  edu.forEach((r, i) => {
    if (r.entrance && r.graduate && r.entrance > r.graduate) errs.push({ sec: 'education', msg: `教育经历第 ${i + 1} 条：入学时间晚于毕业时间` });
    if (r.graduate && DATA.basic.gradDate && r.graduate > DATA.basic.gradDate) errs.push({ sec: 'education', msg: `教育经历第 ${i + 1} 条：毕业时间晚于预计毕业时间（${DATA.basic.gradDate}）` });
  });
  const fam = DATA.family || [];
  if (!fam.length) errs.push({ sec: 'family', msg: '「主要家庭成员」为必填模块，至少需添加 1 条记录' });
  return errs;
}

/* 应用错误样式 */
function applyErrors() {
  $$('[data-field]').forEach(el => {
    el.querySelectorAll('.field-ctl, .photo-col').forEach(() => {});
    el.classList.remove('ctl-err', 'ctl-ok');
    const em = el.querySelector('.err-msg');
    if (em) em.textContent = '';
  });
  $$('.ctl-err').forEach(el => el.classList.remove('ctl-err'));

  Object.keys(errMap).forEach(p => {
    const el = document.querySelector(`[data-field="${p}"]`);
    if (!el) return;
    const ctl = el.querySelector('.field-ctl') || el;
    ctl.classList.add('ctl-err');
    const em = el.querySelector('.err-msg');
    if (em) em.textContent = errMap[p];
  });

  // 照片错误
  if (errMap['basic.photo']) {
    const pb = $('#photoBox');
    if (pb) pb.classList.add('ctl-err');
    const pc = document.querySelector('[data-field="basic.photo"] .err-msg');
    if (pc) pc.textContent = errMap['basic.photo'];
  }
}

/* ---------------- 进度计算 ---------------- */
function updateProgress() {
  let total = 0, done = 0;
  window.RULES.forEach(r => {
    if (!r.req) return;
    total++;
    if (V.notEmpty(window.getPath(DATA, r.path))) done++;
  });
  // 表格必填模块
  total += 2;
  if ((DATA.education || []).length) done++;
  if ((DATA.family || []).length) done++;
  const pct = Math.round(done / total * 100);
  $('#bbProgress').textContent = pct + '%';
  $('#progBar').style.width = pct + '%';

  // 模块角标
  window.SCHEMA.forEach(sec => {
    const tag = document.querySelector(`[data-tag="${sec.id}"]`);
    if (!tag) return;
    if (!sec.req) return;
    let filled = false;
    if (sec.kind === 'table') {
      filled = (DATA[sec.id] || []).length > 0;
    } else {
      const reqs = window.RULES.filter(r => r.req && r.path.startsWith(sec.id + '.'));
      filled = reqs.length > 0 && reqs.every(r => V.notEmpty(window.getPath(DATA, r.path)));
    }
    if (filled) { tag.className = 'sec-tag done'; tag.textContent = '已填写 ✓'; }
    else { tag.className = 'sec-tag'; tag.textContent = '必填'; }
  });
}

/* ---------------- 存档 ---------------- */
function save(manual) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({ data: DATA, ts: Date.now() }));
    dirty = false;
    const h = $('#saveHint');
    if (manual) { h.textContent = '✓ 已保存（' + new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) + '）'; h.className = 'saved'; }
    else { h.textContent = '草稿已自动保存到本机浏览器'; h.className = ''; }
  } catch (e) {
    $('#saveHint').textContent = '⚠ 本地存储空间不足（照片可能过大），请重新上传较小照片';
  }
}
function load() {
  try {
    const s = localStorage.getItem(LS_KEY);
    if (!s) return false;
    const o = JSON.parse(s);
    if (o && o.data) { DATA = Object.assign(JSON.parse(JSON.stringify(window.EMPTY_DATA)), o.data); return true; }
  } catch (e) {}
  return false;
}

/* ---------------- 事件绑定 ---------------- */
function bindEvents() {

  /* 折叠 */
  $('#formWrap').addEventListener('click', e => {
    const head = e.target.closest('[data-toggle]');
    if (head && !e.target.closest('.sec-btn')) {
      const id = head.dataset.toggle;
      collapsed[id] = !collapsed[id];
      head.parentElement.classList.toggle('collapsed', collapsed[id]);
      return;
    }
    /* 表格工具按钮 */
    const btn = e.target.closest('[data-act]');
    if (btn) { handleSecAct(btn.dataset.act, btn.dataset.sec); return; }
    /* 删除行 */
    const del = e.target.closest('[data-del]');
    if (del) { handleDelRow(del.dataset.del, +del.dataset.idx); return; }
    /* 标签删除 */
    const rm = e.target.closest('[data-rm]');
    if (rm) { const box = rm.closest('[data-tags]'); toggleTag(box.dataset.tags, rm.dataset.rm, false); return; }
    /* 标签添加 */
    const add = e.target.closest('[data-add]');
    if (add) { const pool = add.closest('[data-pool]'); toggleTag(pool.dataset.pool, add.dataset.add, true); return; }
    /* 展开/收起候选项 */
    const more = e.target.closest('[data-more]');
    if (more) {
      const p = more.dataset.more;
      tagOpen[p] = !tagOpen[p];
      const pool = document.querySelector(`[data-pool="${p}"]`);
      if (pool) pool.classList.toggle('show', tagOpen[p]);
      more.textContent = tagOpen[p] ? '▲ 收起候选项' : '▼ 展开候选项（最多选 3 个）';
      return;
    }
    /* 照片 */
    if (e.target.closest('#photoBox') || e.target.closest('#photoModify')) { $('#photoFile').click(); return; }
  });

  /* 输入（事件委托） */
  $('#formWrap').addEventListener('input', onInput);
  $('#formWrap').addEventListener('change', onChange);
  $('#formWrap').addEventListener('blur', onInput, true);

  /* 照片上传 */
  document.addEventListener('change', e => {
    if (e.target.id === 'photoFile') { handlePhoto(e.target.files[0]); e.target.value = ''; }
  });

  /* 底部按钮 */
  $('#btnClear').onclick = () => {
    if (!confirm('确定清空全部已填内容？此操作不可撤销。')) return;
    localStorage.removeItem(LS_KEY);
    DATA = JSON.parse(JSON.stringify(window.EMPTY_DATA));
    collapsed = {};
    render(); toast('已清空', 'ok');
  };
  $('#btnDemo').onclick = () => { if (confirm('将填入一套示例数据（覆盖当前内容），用于快速预览效果？')) { fillDemo(); } };
  $('#btnSaveForm').onclick = () => { validateAll(); applyErrors(); save(true); toast('保存成功', 'ok'); };
  $('#btnCancelForm').onclick = () => {
    if (confirm('取消将放弃未保存的修改并返回初始状态，确定？')) {
      localStorage.removeItem(LS_KEY);
      DATA = JSON.parse(JSON.stringify(window.EMPTY_DATA));
      render(); toast('已取消');
    }
  };
  $('#btnSubmit').onclick = submit;
  $('#btnBackEdit').onclick = showForm;
  $('#btnPrint').onclick = () => window.print();
  $('#btnTop').onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* 输入处理 */
function onInput(e) {
  const el = e.target;
  if (!el.dataset || !el.dataset.path) return;
  const p = el.dataset.path;
  let v = el.value;

  /* 数字类过滤 */
  const fd = findField(p);
  if (fd && fd.numeric) { v = v.replace(/[^\d.]/g, ''); if (v !== el.value) el.value = v; }

  window.setPath(DATA, p, v);

  /* 身份证自动带出 */
  if (fd && fd.auto === 'idcard') {
    const b = V.idcardBirth(v), g = V.idcardGender(v);
    if (b) { DATA.basic.birthday = b; const bi = document.querySelector('[data-path="basic.birthday"]'); if (bi) bi.value = b; }
    if (g) { DATA.basic.gender = g; const gi = document.querySelector('[data-path="basic.gender"]'); if (gi) gi.value = g; }
  }

  /* 单字段即时校验 */
  const rule = window.RULES.find(r => r.path === p);
  if (rule) {
    let msg = '';
    try { msg = rule.fn(v, DATA) || ''; } catch (err) {}
    const wrap = document.querySelector(`[data-field="${p}"]`);
    if (wrap) {
      const ctl = wrap.querySelector('.field-ctl') || wrap;
      const em = wrap.querySelector('.err-msg');
      ctl.classList.toggle('ctl-err', !!msg);
      ctl.classList.remove('ctl-ok');
      if (em) em.textContent = msg;
    }
    errMap[p] = msg;
  }

  const cnt = document.querySelector(`[data-cnt="${p}"]`);
  if (cnt) cnt.textContent = v.length;

  dirty = true;
  updateProgress();
  clearTimeout(window._autoSave);
  window._autoSave = setTimeout(() => { if (dirty) save(false); }, 800);
}

/* 下拉/省市区联动 */
function onChange(e) {
  const el = e.target;
  if (!el.dataset || !el.dataset.path) return;
  const p = el.dataset.path;

  /* 省市区级联 */
  if (el.dataset.rk) {
    const base = p.replace(/(Prov|City|Dist)$/, '');   // 如 basic.native / basic.birth
    const lv = el.dataset.rk;
    window.setPath(DATA, p, el.value);
    if (lv === 'Prov') { window.setPath(DATA, base + 'City', ''); window.setPath(DATA, base + 'Dist', ''); }
    if (lv === 'City') { window.setPath(DATA, base + 'Dist', ''); }
    // 重建整个 region-row（以 base+'Prov' 为入口再解析）
    const row = el.closest('[data-region]');
    if (row) {
      const tmp = document.createElement('div');
      tmp.innerHTML = regionHtml(base + 'Prov', null, '');
      row.replaceWith(tmp.firstElementChild);
    }
    updateProgress();
    clearTimeout(window._autoSave); window._autoSave = setTimeout(() => save(false), 600);
    return;
  }

  onInput(e);
}

function findField(p) {
  for (const sec of window.SCHEMA) {
    if (!sec.fields) continue;
    const f = sec.fields.find(x => x.p === p);
    if (f) return f;
  }
  return null;
}

/* 标签切换 */
function toggleTag(path, tag, add) {
  const arr = Array.isArray(window.getPath(DATA, path)) ? window.getPath(DATA, path) : [];
  const limit = 3;
  if (add) {
    if (arr.includes(tag)) return;
    if (arr.length >= limit) { toast('求职意向最多选择 ' + limit + ' 个', 'err'); return; }
    arr.push(tag);
  } else {
    const i = arr.indexOf(tag); if (i >= 0) arr.splice(i, 1);
  }
  window.setPath(DATA, path, arr);

  /* 整体重绘标签块 */
  const block = document.querySelector(`[data-tagblock="${path}"]`);
  if (block) {
    const tmp = document.createElement('div');
    tmp.innerHTML = tagsHtml(path, { limit }, arr);
    block.replaceWith(tmp.firstElementChild);
  }
  dirty = true; updateProgress();
  clearTimeout(window._autoSave); window._autoSave = setTimeout(() => save(false), 600);
}

/* 照片处理 */
function handlePhoto(file) {
  if (!file) return;
  const err = [];
  if (!/^image\/(jpeg|png)$/.test(file.type)) err.push('仅支持 JPG / PNG 格式');
  const kb = file.size / 1024;
  if (kb < 5) err.push('文件过小（当前 ' + kb.toFixed(1) + 'kb），要求 5~200kb');
  if (kb > 200) err.push('文件过大（当前 ' + kb.toFixed(0) + 'kb），要求 5~200kb');

  const img = new Image();
  img.onload = () => {
    const w = img.naturalWidth, h = img.naturalHeight;
    if (w < 120 || h < 160) err.push('尺寸过小（' + w + '*' + h + 'px），要求不小于 120*160px');
    if (w > 600 || h > 800) err.push('尺寸过大（' + w + '*' + h + 'px），要求不超过 600*800px');
    const ar = w / h;
    if (Math.abs(ar - 120 / 160) > 0.04) err.push('宽高比不符（当前约 ' + ar.toFixed(2) + '，要求约 0.75 即 3:4）');

    if (err.length) {
      dataURL = null;
      toast('照片不合规：' + err[0], 'err');
      const pb = $('#photoBox'); if (pb) pb.classList.add('ctl-err');
      const em = document.querySelector('[data-field="basic.photo"] .err-msg');
      if (em) em.textContent = err.join('；');
      return;
    }
    // 通过：压缩到合适尺寸
    const cv = document.createElement('canvas');
    cv.width = Math.min(w, 600); cv.height = Math.round(cv.width / ar);
    cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
    const dataURL = cv.toDataURL('image/jpeg', 0.85);
    DATA.basic.photo = dataURL;
    const pb = $('#photoBox');
    pb.innerHTML = `<img src="${dataURL}" alt="证件照">`;
    pb.classList.remove('ctl-err');
    const em = document.querySelector('[data-field="basic.photo"] .err-msg');
    if (em) em.textContent = '';
    errMap['basic.photo'] = '';
    toast('照片已上传（' + cv.width + '*' + cv.height + '，' + kb.toFixed(0) + 'kb）', 'ok');
    updateProgress(); save(false);
  };
  img.onerror = () => toast('图片读取失败', 'err');
  img.src = URL.createObjectURL(file);
}

/* 表格增删 */
function handleSecAct(act, secId) {
  const sec = window.SCHEMA.find(s => s.id === secId);
  if (!sec) return;
  if (act === 'add') { openRowModal(sec, null); return; }
  if (act === 'edit') { openRowModal(sec, 0); return; }
  if (act === 'delrow') { handleDelRow(secId, 0); return; }
  if (act === 'clearall') {
    if (!(DATA[secId] || []).length) { toast('该模块暂无数据'); return; }
    if (confirm('确定清空「' + sec.title + '」的全部记录？')) { DATA[secId] = []; rerenderSec(secId); recomputeTableErrs(); }
  }
}
function handleDelRow(secId, idx) {
  const rows = DATA[secId] || [];
  if (!rows[idx]) return;
  if (confirm('确定删除该条记录？')) { rows.splice(idx, 1); rerenderSec(secId); recomputeTableErrs(); }
}
function rerenderSec(secId) {
  const sec = window.SCHEMA.find(s => s.id === secId);
  const el = document.querySelector(`section[data-sec="${secId}"] .sec-body`);
  if (el) el.innerHTML = tableHtml(sec, DATA[secId] || []);
  updateProgress(); save(false);
}
function recomputeTableErrs() {
  const tErrs = validateTables();
  // 更新必填模块角标
  updateProgress();
}

/* 子表单弹窗 */
function openRowModal(sec, idx) {
  const row = idx == null ? {} : (DATA[sec.id][idx] || {});
  let h = '<div class="modal-mask show" id="rowModal"><div class="modal">';
  h += `<div class="modal-head">${idx == null ? '添加' : '编辑'} · ${esc(sec.title)}<span class="x" data-close>×</span></div>`;
  h += `<div class="modal-body">`;
  if (sec.tips && sec.tips.length) {
    h += `<div class="form-tips">` + sec.tips.map(t => esc(t)).join('<br>') + `</div>`;
  }
  h += `<div class="grid ${sec.cols === 3 ? 'grid-3' : 'grid-2'}">`;
  sec.subFields.forEach(f => {
    const val = f.type === 'rankpair' ? row : (row[f.k] == null ? '' : row[f.k]);
    h += '<div class="field' + (f.full ? ' full' : '') + '">';
    h += `<div class="field-label">${f.req ? '<span class="req">*</span>' : ''}${esc(f.label)}</div>`;
    h += '<div class="field-ctl">' + subCtl(f, val) + '<div class="err-msg"></div>';
    if (f.help) h += `<div class="field-help">${esc(f.help)}</div>`;
    h += '</div></div>';
  });
  h += '</div></div>';
  h += `<div class="modal-foot"><button class="btn" data-close>取消</button><button class="btn btn-primary" data-ok>保存</button></div>`;
  h += '</div></div>';
  const div = document.createElement('div');
  div.innerHTML = h;
  const modal = div.firstElementChild;
  document.body.appendChild(modal);

  modal.addEventListener('click', e => {
    if (e.target.closest('[data-close]')) { modal.remove(); return; }
    if (e.target.closest('[data-ok]')) { commitRow(sec, idx, modal); return; }
  });
  modal.addEventListener('change', e => {
    const fi = e.target.closest('input[type=file][data-sf]');
    if (fi && fi.files[0]) {
      const nameSpan = modal.querySelector(`[data-file-name="${fi.dataset.sf}"]`);
      if (nameSpan) nameSpan.textContent = fi.files[0].name;
    }
  });
  modal.addEventListener('keydown', e => { if (e.key === 'Escape') modal.remove(); });
}

function subCtl(f, val) {
  const k = 'sf_' + f.k + '_' + Math.random().toString(36).slice(2, 6);
  if (f.type === 'select') {
    let opts;
    if (f.src === 'provinces') opts = (window.REGION_DATA || []).map(x => x.name);
    else opts = Array.isArray(f.src) ? f.src : (window.DICT[f.src] || []);
    let h = `<select data-sf="${f.k}"><option value="">--请选择--</option>`;
    opts.forEach(o => { h += `<option value="${esc(o)}"${val === o ? ' selected' : ''}>${esc(o)}</option>`; });
    return h + '</select>';
  }
  if (f.type === 'date') return `<input type="date" data-sf="${f.k}" value="${esc(val)}">`;
  if (f.type === 'textarea') return `<textarea data-sf="${f.k}" maxlength="${f.max || 300}" placeholder="${esc(f.ph || '')}">${esc(val)}</textarea>`;
  if (f.type === 'rankpair') {
    return `<div class="rankpair">第 <input type="text" data-sf="rankN" data-num="1" maxlength="3" inputmode="numeric" value="${esc(val.rankN || '')}"> 名，共 <input type="text" data-sf="rankTotal" data-num="1" maxlength="4" inputmode="numeric" value="${esc(val.rankTotal || '')}"> 人</div>`;
  }
  if (f.type === 'school') {
    const list = window.DICT.schoolList.map(s => s.n);
    return `<input type="text" data-sf="${f.k}" list="schoolList" value="${esc(val)}" placeholder="${esc(f.ph || '输入或选择学校名称')}">
      <datalist id="schoolList">${list.map(n => `<option value="${esc(n)}">`).join('')}</datalist>`;
  }
  if (f.type === 'major') {
    const all = [];
    window.DICT.majorGroups.forEach(g => g.items.forEach(i => all.push(i)));
    return `<input type="text" data-sf="${f.k}" list="majorList" value="${esc(val)}" placeholder="${esc(f.ph || '输入或选择专业名称')}">
      <datalist id="majorList">${all.map(n => `<option value="${esc(n)}">`).join('')}</datalist>`;
  }
  if (f.type === 'file') {
    return `<div class="file-row"><span class="file-name" data-file-name="${f.k}">${esc(val || '请选择')}</span>
            <label class="file-btn">浏览<input type="file" data-sf="${f.k}" data-limit="${f.limit || 0}" accept="${f.accept || ''}" style="display:none"></label></div>
            <input type="hidden" data-sf-name="${f.k}" value="${esc(val)}">`;
  }
  const extra = [f.max ? `maxlength="${f.max}"` : '', f.ph ? `placeholder="${esc(f.ph)}"` : ''].filter(Boolean).join(' ');
  return `<input type="text" data-sf="${f.k}" value="${esc(val)}" ${extra}${f.num ? ' data-num="1" inputmode="numeric"' : ''}>`;
}

function commitRow(sec, idx, modal) {
  const obj = {};
  let ok = true;
  sec.subFields.forEach(f => {
    if (f.type === 'file') {
      const fi = modal.querySelector(`[data-sf="${f.k}"]`);
      const nm = modal.querySelector(`[data-sf-name="${f.k}"]`);
      const file = fi && fi.files[0];
      if (file) {
        const kb = file.size / 1024;
        if (f.limit && kb > f.limit) {
          ok = false;
          const wrap = fi.closest('.field');
          wrap.querySelector('.field-ctl').classList.add('ctl-err');
          wrap.querySelector('.err-msg').textContent = '文件大小 ' + kb.toFixed(0) + 'kb，超出 ' + f.limit + 'kb 限制';
          return;
        }
        obj[f.k] = file.name;
        obj.size = kb.toFixed(0) + 'kb';
      } else obj[f.k] = nm ? nm.value : '';
      if (f.req && !obj[f.k] && ok) {
        ok = false;
        const wrap = fi.closest('.field');
        wrap.querySelector('.field-ctl').classList.add('ctl-err');
        wrap.querySelector('.err-msg').textContent = '请上传' + f.label;
      }
    } else if (f.type === 'rankpair') {
      const n = modal.querySelector('[data-sf="rankN"]');
      const t = modal.querySelector('[data-sf="rankTotal"]');
      obj.rankN = n ? n.value.trim() : '';
      obj.rankTotal = t ? t.value.trim() : '';
    } else {
      const el = modal.querySelector(`[data-sf="${f.k}"]`);
      let v = el ? el.value.trim() : '';
      if (el && el.dataset.num) v = v.replace(/[^\d.]/g, '');
      obj[f.k] = v;
    }
    if (f.req && f.type !== 'file' && !obj[f.k] && ok) {
      ok = false;
      const el = modal.querySelector(`[data-sf="${f.k}"]`);
      const wrap = el.closest('.field');
      wrap.querySelector('.field-ctl').classList.add('ctl-err');
      wrap.querySelector('.err-msg').textContent = '请填写' + f.label;
    }
  });
  if (!ok) { toast('请完善必填项', 'err'); return; }

  /* 条件必填：外语四六级/专四专八 → 成绩+证书编号必填 */
  if (sec.id === 'language') {
    const l4 = ['大学英语四级', '大学英语六级', '英语专业四级', '英语专业八级'];
    if (l4.includes(obj.level) && (!obj.score || !obj.certNo)) {
      modal.querySelectorAll('[data-sf="score"],[data-sf="certNo"]').forEach(el => {
        el.closest('.field').querySelector('.field-ctl').classList.add('ctl-err');
        el.closest('.field').querySelector('.err-msg').textContent = '该级别下必填';
      });
      toast('该外语级别下，成绩及其证书编号必须填写', 'err');
      return;
    }
  }
  /* 条件必填：参加国内高考 → 高考成绩必填 */
  if (sec.id === 'education' && obj.gaokao === '是' && !obj.gaokaoScore) {
    const el = modal.querySelector('[data-sf="gaokaoScore"]');
    el.closest('.field').querySelector('.field-ctl').classList.add('ctl-err');
    el.closest('.field').querySelector('.err-msg').textContent = '参加了国内高考时必填';
    toast('参加了国内高考时，高考成绩必填', 'err');
    return;
  }
  /* 额外格式校验 */
  if (sec.id === 'family' && obj.phone) {
    const pe = V.phone(obj.phone);
    if (pe) { toast('家庭成员手机号格式不正确', 'err'); return; }
  }
  if (sec.id === 'education') {
    if (obj.entrance && obj.graduate && obj.entrance > obj.graduate) { toast('入学时间不能晚于毕业时间', 'err'); return; }
  }
  if (sec.id === 'practice') {
    if (obj.from && obj.to && obj.from > obj.to) { toast('开始时间不能晚于结束时间', 'err'); return; }
  }
  if (sec.id === 'research') {
    if (obj.from && obj.to && obj.from > obj.to) { toast('开始时间不能晚于结束时间', 'err'); return; }
  }

  if (!DATA[sec.id]) DATA[sec.id] = [];
  if (idx == null) DATA[sec.id].push(obj); else DATA[sec.id][idx] = obj;
  modal.remove();
  rerenderSec(sec.id);
  toast('已保存', 'ok');
}

/* ---------------- 示例数据 ---------------- */
function fillDemo() {
  const d = JSON.parse(JSON.stringify(window.EMPTY_DATA));
  d.basic = {
    name: '尹继超', gender: '男', idcard: '220681199310051333', birthday: '1993-10-05',
    gradDate: '2024-06-30', nation: '汉族',
    nativeProv: '吉林省', nativeCity: '白山市', nativeDist: '临江市',
    birthProv: '吉林省', birthCity: '白山市', birthDist: '临江市',
    height: '185', gradType: '国内毕业生', marital: '未婚', weight: '80',
    healthy: '是', political: '中共预备党员', veteran: '否', xjCode: 'XJ2024063012358',
    intention: ['国家电网', '电气工程', '变电运维'], photo: ''
  };
  d.contact = {
    phone: '17649997204', tel: '', email: 'yinjichao1234@163.com',
    addr: '吉林省长春市工大家属楼', zip: '130000', wechat: '', qq: '1027543959'
  };
  d.education = [{
    entrance: '2021-09-01', graduate: '2024-06-30', studyForm: '普通全日制',
    level: '大学本科毕业', school: '清华大学', diplomaNo: '',
    batch: '本科一批', highest: '是', degree: '学士', degreeNo: '',
    subjectLevel: '', major: '电气工程及其自动化', rankN: '15', rankTotal: '180',
    researchDir: '电力系统自动化', thesisTitle: '基于深度学习的配电网故障诊断方法研究',
    gpa: '3.6', gaokao: '是', gaokaoScore: '652', trainMode: '统招统分', gaokaoPlace: '吉林省'
  }];
  d.family = [{
    title: '父亲', name: '尹伟', birth: '1968-05-12', position: '农民',
    unit: '无', phone: '18401794504', addr: '吉林省白山市临江市'
  }];
  d.language = [{
    type: '英语', level: '大学英语六级', proficiency: '熟练',
    certDate: '2023-06-15', certOrg: '教育部教育考试院', score: '512', certNo: '123456789012345',
    certFile: '', remark: ''
  }];
  d.computer = [{
    certName: '全国计算机等级考试二级（MS Office）', certDate: '2023-09-20',
    org: '教育部教育考试院', level: '二级', score: '85', certNo: '2023092012345',
    certFile: '', remark: ''
  }];
  d.award = [{ name: '校级优秀学生干部', level: '校级', date: '2023-12-01', org: '清华大学', certNo: '', certFile: '', remark: '' }];
  d.practice = [{
    from: '2023-07-01', to: '2023-08-31', unit: '国网吉林供电公司',
    position: '变电运维实习生', workForm: '实习', witness: '王老师',
    detail: '参与220kV变电站日常巡检与倒闸操作观摩'
  }];
  d.attachment = [{ type: '学籍认证', file: '学籍在线验证报告.pdf', size: '356kb' }];
  d.basic.photo = demoPhoto();   // 生成一张合规的示例证件照，保证提交链路完整
  DATA = d;
  render(); save(false);
  toast('示例数据已填入（含示例证件照）', 'ok');
}

/* 生成一张 480*640（3:4）的合规示例证件照 */
function demoPhoto() {
  try {
    const cv = document.createElement('canvas');
    cv.width = 480; cv.height = 640;
    const g = cv.getContext('2d');
    const grad = g.createLinearGradient(0, 0, 0, 640);
    grad.addColorStop(0, '#dce9f8'); grad.addColorStop(1, '#c3d8ee');
    g.fillStyle = grad; g.fillRect(0, 0, 480, 640);
    g.fillStyle = '#5b7ea8';
    g.beginPath(); g.arc(240, 245, 92, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.moveTo(120, 640); g.quadraticCurveTo(240, 350, 360, 640); g.closePath(); g.fill();
    g.fillStyle = 'rgba(255,255,255,.85)';
    g.font = 'bold 26px sans-serif'; g.textAlign = 'center';
    g.fillText('示例照片', 240, 600);
    return cv.toDataURL('image/jpeg', 0.85);
  } catch (e) { return ''; }
}

/* ---------------- 提交 → 报告 ---------------- */
function submit() {
  validateAll();
  const tErrs = validateTables();

  // 滚动到第一个错误
  const firstP = Object.keys(errMap)[0];
  const hardCount = Object.keys(errMap).length + tErrs.length;

  if (hardCount > 0) {
    applyErrors();
    // 展开含错误的模块
    if (firstP) {
      const secId = firstP.split('.')[0];
      collapsed[secId] = false;
      const secEl = document.querySelector(`section[data-sec="${secId}"]`);
      if (secEl) { secEl.classList.remove('collapsed'); }
      const el = document.querySelector(`[data-field="${firstP}"]`);
      if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.classList.add('ctl-err'); }
    } else if (tErrs.length) {
      collapsed[tErrs[0].sec] = false;
      const s = document.querySelector(`section[data-sec="${tErrs[0].sec}"]`);
      if (s) { s.classList.remove('collapsed'); s.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
    }
    toast('还有 ' + hardCount + ' 处必填/格式问题需完善，已定位到第 1 处', 'err');
    return;
  }

  save(false);
  renderReport();          // 先出报告（顺带产生最新统计），再异步上后端
  tryBackendSubmit();

  showReport();
  window.scrollTo({ top: 0 });
}

/* 后端提交：未配置端点时静默降级为本地 */
function tryBackendSubmit() {
  const ENDPOINT = window.SG_SUBMIT_ENDPOINT || '';
  if (!ENDPOINT) { console.log('[模拟] 未配置后端接口，数据仅存本地'); return; }
  const rep = window.SG_LAST_REPORT || {};
  // 投放渠道：入口链接 ?ch= 参数（与匹配工具同款约定）
  let ch = '';
  try { ch = new URLSearchParams(location.search).get('ch') || ''; } catch (e) {}
  fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      summary: {
        name: DATA.basic.name, phone: DATA.contact.phone, email: DATA.contact.email,
        school: (DATA.education[0] || {}).school || '', major: (DATA.education[0] || {}).major || '',
        level: (DATA.education[0] || {}).level || '', gradDate: DATA.basic.gradDate,
        score: rep.score || 0, complete: rep.complete || 0,
        hard: rep.hard || 0, risk: rep.risk || 0, tip: rep.tip || 0,
        submittedAt: new Date().toISOString()
      },
      platform: ch,
      archive: DATA
    })
  }).then(r => r.json()).then(res => {
    if (res && res.ok) toast('档案已提交，老师可以看到你的体检结果', 'ok');
    else toast('提交未成功：' + ((res && res.error) || '未知原因') + '（数据已保存在本机）', 'err');
  }).catch(err => {
    console.warn('[模拟] 后端提交失败（已降级为本地）', err);
    toast('网络异常，档案暂存在本机，可稍后重新提交', 'err');
  });
}

function showReport() {
  $('#formPage').style.display = 'none';
  $('#actionBar').style.display = 'none';
  $('#reportPage').classList.add('show');
  $('#reportBar').style.display = 'flex';
}
function showForm() {
  $('#reportPage').classList.remove('show');
  $('#formPage').style.display = 'block';
  $('#actionBar').style.display = 'flex';
  $('#reportBar').style.display = 'none';
  window.scrollTo({ top: 0 });
}

/* ---------------- 启动 ---------------- */
(function init() {
  const has = load();
  // 默认展开必填模块
  window.SCHEMA.forEach(s => { collapsed[s.id] = !s.req && s.id !== 'award'; });
  collapsed['other'] = true;
  render();
  bindEvents();
  if (has) toast('已恢复上次填写的草稿', 'ok');
})();

/* ---------------- 调试 / 自动化钩子 ---------------- */
window.SG = {
  get data() { return DATA; },
  validateAll: () => validateAll(),
  validateTables: () => validateTables(),
  submit: () => submit(),
  fillDemo: () => fillDemo(),
  handlePhoto: f => handlePhoto(f),
  buildReport: () => buildReport(),
  render: () => render(),
  errMap: () => errMap
};
