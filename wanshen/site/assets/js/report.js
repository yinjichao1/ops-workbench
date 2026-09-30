/* ============================================================
 * 《网申体检报告》生成引擎
 * 三级判定：硬伤(必须修) / 风险(建议核实) / 提示(可优化)
 * ============================================================ */

function buildReport() {
  const hard = [], risk = [], tip = [];
  const b = DATA.basic, c = DATA.contact;
  const edu = DATA.education || [];
  const fam = DATA.family || [];

  /* ============ 硬伤（会被正式网申打回） ============ */
  // 兜底：必填规则未过的项
  window.RULES.forEach(r => {
    if (!r.req) return;
    const v = window.getPath(DATA, r.path);
    let msg = '';
    try { msg = r.fn(v, DATA) || ''; } catch (e) {}
    if (msg) hard.push({ t: r.label + '：' + msg.replace(/^请(填写|选择)/, '未'), d: suggestFix(r.path) });
  });

  if (!edu.length) hard.push({ t: '教育经历：必填模块为空', d: '现阶段教育经历必须填写，并标识为最高学历；高中及以下无需填写。' });
  if (!fam.length) hard.push({ t: '主要家庭成员：必填模块为空', d: '至少填写 1 位家庭成员信息。' });

  /* ---- 教育经历：官方 4 条规则 + 逻辑校验 ---- */
  const RANK = window.EDU_RANK || {};
  const hasHigher = edu.some(r => r.level === '硕士研究生毕业' || r.level === '博士研究生毕业');
  const hasBenZhuan = edu.some(r => r.level === '大学本科毕业' || r.level === '大学专科毕业');
  const hasZhuanKe = edu.some(r => r.level === '大学专科毕业');

  if (hasHigher && !hasBenZhuan)
    hard.push({ t: '教育经历：研究生缺少本科/专科记录', d: '官方规则第 2 条：研究生必须填写一条本科或专科记录。' });
  if (edu.some(r => r.batch === '专升本') && !hasZhuanKe)
    hard.push({ t: '教育经历：专升本缺少专科记录', d: '官方规则第 3 条：专升本人员必须填写一条专科记录。' });

  const highestCnt = edu.filter(r => r.highest === '是').length;
  if (edu.length && highestCnt === 0)
    hard.push({ t: '教育经历：未标识最高学历', d: '官方规则第 1 条：现阶段教育经历必须填写，并标识为最高学历（其中一条「是否最高学历」选「是」）。' });
  if (highestCnt > 1)
    risk.push({ t: `教育经历：最高学历标识了 ${highestCnt} 条`, d: '「是否最高学历」只能有一条记录选「是」，请核对。' });

  edu.forEach((r, i) => {
    if (r.entrance && r.graduate && r.entrance > r.graduate)
      hard.push({ t: `教育经历第${i + 1}条：入学时间晚于毕业时间`, d: '请核对起止时间。' });
    if (r.graduate && b.gradDate && r.highest === '是' && r.graduate !== b.gradDate)
      risk.push({ t: `教育经历第${i + 1}条：毕业时间（${r.graduate}）与预计毕业时间（${b.gradDate}）不一致`, d: '最高学历的毕业时间应与「预计毕业时间」一致，不一致易被审核质疑。' });
    if (r.level === '大学本科毕业' && r.entrance && r.graduate) {
      const y = (+r.graduate.slice(0, 4)) - (+r.entrance.slice(0, 4));
      if (y > 5) risk.push({ t: `教育经历第${i + 1}条：学制 ${y} 年偏长`, d: '本科通常为 4 年（专升本 2 年、医学 5 年），如有休学等特殊情况建议在「其他情况说明」中注明。' });
    }
    if (r.gaokao === '是' && !r.gaokaoScore)
      hard.push({ t: `教育经历第${i + 1}条：参加了国内高考但未填高考成绩`, d: '高考成绩为必填项，请补充。' });
    if (r.gaokao === '否')
      tip.push({ t: `教育经历第${i + 1}条：未参加国内高考`, d: '如为专升本/高职单招/保送等入学方式，建议在「其他情况说明」中注明，避免审核疑问。' });
    if (r.studyForm && r.studyForm !== '普通全日制')
      tip.push({ t: `教育经历第${i + 1}条：学习形式为「${r.studyForm}」`, d: '部分省公司岗位要求「全日制普通高等教育学历」，非全日制学历报考前请核对岗位公告的学历要求。' });
  });

  /* 从高往低填写检查 */
  if (edu.length >= 2) {
    let bad = -1;
    for (let i = 1; i < edu.length; i++) {
      const prev = RANK[edu[i - 1].level] || 0, cur = RANK[edu[i].level] || 0;
      if (cur > prev) { bad = i; break; }
    }
    if (bad >= 0)
      risk.push({ t: `教育经历未按"从高往低"排序`, d: `第 ${bad + 1} 条学历高于上一条，官方要求从高往低填写，请调整顺序。` });
  }

  /* 双学士学位规则 */
  if (edu.some(r => r.degree === '双学士') && edu.length < 2)
    tip.push({ t: '学位选择「双学士」但仅有一条教育经历', d: '官方规则第 4 条：双学士学位人员必须填写主修、辅修教育经历（"是否辅修学位"应正确标识），且学位均选择"双学士"。' });
  if (edu.some(r => r.level === '大学本科毕业' && r.degree === '无'))
    tip.push({ t: '本科学历但学位为「无」', d: '部分省公司岗位要求「取得相应学位」，无学位报考前请核对岗位公告；如因挂科未授位，建议在「其他情况说明」注明。' });

  /* ============ 风险（易被质疑/影响通过率） ============ */
  if (b.nativeProv && b.birthProv && b.nativeProv !== b.birthProv)
    risk.push({ t: '籍贯与生源地省份不一致', d: `籍贯为 ${b.nativeProv}，生源地为 ${b.birthProv}。生源地指出生/入学前户籍所在地，部分省公司对属地生源有倾斜，如确实不一致属正常，但请确认无误。` });

  if (b.idcard && b.birthday && V.idcardBirth(b.idcard) !== b.birthday)
    risk.push({ t: '出生日期与身份证号不匹配', d: `身份证推算为 ${V.idcardBirth(b.idcard)}，当前填写 ${b.birthday}。` });

  if (b.height && b.weight) {
    const h = +b.height / 100, w = +b.weight;
    const bmi = w / (h * h);
    if (bmi > 28) risk.push({ t: `BMI 偏高（${bmi.toFixed(1)}）`, d: '部分岗位（如变电运维、输电运检）体检对体重有隐性要求，建议提前了解目标省公司体检标准。' });
    if (bmi < 17) tip.push({ t: `BMI 偏低（${bmi.toFixed(1)}）`, d: '体检标准通常要求身体健康、营养状况良好，建议关注。' });
  }

  if (b.healthy === '否')
    risk.push({ t: '「是否健康」选择了「否」', d: '国网网申体检环节较严格，如存在慢性病或既往病史，建议提前咨询目标省公司人资。' });

  if (b.political === '中共预备党员')
    tip.push({ t: '政治面貌为「中共预备党员」', d: '预备党员在部分岗位（如党务、电网调度）有加分，但需在党员发展有效期内涵盖入职时间，建议确认转正时间。' });

  /* 联系方式风险 */
  if (c.phone && c.phone.startsWith('17'))
    risk.push({ t: '手机号为 17 号段', d: '个别省公司系统对 17 号段短信送达率较低，建议同时填写座机或备用邮箱，确保面试通知能收到。' });
  if (c.email && /(qq|163)\.com$/.test(c.email))
    tip.push({ t: '使用公共邮箱（QQ/163）', d: '建议优先使用 163/QQ 邮箱没问题，但请确保经常查看；部分单位批量发信可能被归入垃圾箱，建议同步关注短信通知。' });
  if (c.wechat && !V.notEmpty(c.email))
    tip.push({ t: '未填写微信但填了邮箱', d: '国网面试通知多以短信 + 邮件为主，微信可选填，建议保持手机畅通。' });

  /* 家庭成员风险 */
  if (!fam.some(r => r.title === '父亲') && !fam.some(r => r.title === '母亲'))
    risk.push({ t: '家庭成员未填写父母信息', d: '家庭成员一般需填写父母双方，仅填「其他」易被审核关注，请确认。' });
  fam.forEach((r, i) => {
    if (r.unit && r.unit.trim() === '无' && r.position && !/农|无|自由职业|个体|退休/.test(r.position))
      tip.push({ t: `家庭成员第${i + 1}条：工作单位填「无」但职务为「${r.position}」`, d: '建议统一表述，如「务农」「自由职业」「个体经营」，避免前后矛盾。' });
  });

  /* ============ 提示（竞争力优化） ============ */
  const langs = DATA.language || [];
  if (!langs.length)
    tip.push({ t: '未填写外语能力', d: '英语四六级是国网网申的重要加分项，尤其英语四级 425 分以上为多数省公司隐性门槛，建议务必填写。' });
  else {
    const l4 = ['大学英语四级', '大学英语六级', '英语专业四级', '英语专业八级'];
    if (!langs.some(r => l4.includes(r.level)))
      tip.push({ t: '外语水平未包含四六级/专四专八', d: '多数省公司对英语四级有隐性要求（425 分以上），如已通过建议补充记录。' });
  }
  if (!(DATA.computer || []).length)
    tip.push({ t: '未填写计算机能力', d: '计算机二级（尤其 MS Office / C 语言）是常见加分项，有则填、无则建议尽早备考。' });
  if (!(DATA.award || []).length)
    tip.push({ t: '未填写获奖情况', d: '奖学金、学科竞赛、荣誉称号等对网申初筛有正面作用，建议至少填写 1~2 项。' });
  if (!(DATA.practice || []).length)
    tip.push({ t: '未填写社会实践/工作经历', d: '实习、社会实践、学生干部经历可体现综合素质，建议补充与电力相关的实践经历。' });
  if (!(DATA.certificate || []).length)
    tip.push({ t: '未填写资格证书', d: '电力相关的职业资格、技能证书（如电工证）可作为加分项。' });
  const atts = DATA.attachment || [];
  if (!atts.length)
    tip.push({ t: '未上传电子附件', d: '建议提前准备并上传：学籍认证（学籍在线验证报告）、成绩单扫描件、就业推荐表、各类等级证书扫描件。' });
  if (!V.notEmpty(b.photo))
    tip.push({ t: '未上传证件照', d: '正式网申中证件照为必传项，且规格卡得严（3:4 比例、JPG/PNG、5~200kb），建议现在按规格传一张练手，正式填报时一次通过。' });
  else {
    if (!atts.some(r => r.type === '学籍认证'))
      tip.push({ t: '附件缺少「学籍认证」', d: '学籍在线验证报告是网申审核的重要材料，建议登录学信网申请后上传。' });
    if (!atts.some(r => r.type === '成绩单扫描件'))
      tip.push({ t: '附件缺少「成绩单扫描件」', d: '成绩单反映专业基础与核心课程成绩（尤其电路/电力系统等），建议上传。' });
  }
  if (!b.intention || !b.intention.length)
    tip.push({ t: '未填写求职意向', d: '求职意向虽仅作收集，但填写与目标省公司/岗位方向一致的标签，有助于后续岗位匹配沟通。' });
  if (!(DATA.paper || []).length && !(DATA.research || []).length)
    tip.push({ t: '未填写学术成果', d: '本科生一般无需填写；如有论文、科研项目、专利等，请补充以增强竞争力。' });

  /* 生源与目标省公司匹配提示 */
  if (b.birthProv) {
    const target = (b.intention || []).find(x => x.includes('省电力') || x.includes('供电'));
    tip.push({ t: `生源地：${b.birthProv}`, d: `国网各省公司普遍对属地生源友好（如吉林省电力对吉林生源、辽宁省电力对辽宁生源）。建议重点关注 ${b.birthProv} 及相邻省份的招聘公告，属地生源在同等条件下有明显优势。` });
  }

  return { hard, risk, tip };
}

/* 修复建议 */
function suggestFix(path) {
  const map = {
    'basic.photo': '按规格重新上传：120*160px~600*800px、JPG/PNG、5~200kb、清晰正面免冠照。',
    'basic.xjCode': '登录「学信网 → 学籍查询 → 在线验证报告」，申请后获取 12 位以上验证码（有效期通常 6 个月）。',
    'basic.idcard': '核对 18 位号码，注意最后一位校验码（可能是 X）。',
    'basic.birthday': '按身份证号推算填写，格式 YYYY-MM-DD。',
    'contact.phone': '填写常用手机号，确保能接收面试通知短信。',
    'contact.email': '填写常用邮箱，建议与手机号保持同步查看。',
    'contact.addr': '填写详细到门牌号的通信地址，用于寄送材料。',
    'contact.zip': '按通信地址填写 6 位邮政编码。',
    'basic.height': '填写真实身高（cm），体检会复核。',
    'basic.weight': '填写真实体重（kg），体检会复核。'
  };
  return map[path] || '请在对应模块中补充完整。';
}

/* ---------------- 渲染报告 ---------------- */
function renderReport() {
  const r = buildReport();
  const now = new Date();
  const ts = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0')
    + ' ' + String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');

  /* 完整度得分 */
  let total = 0, done = 0;
  window.RULES.forEach(x => { if (x.req) { total++; if (V.notEmpty(window.getPath(DATA, x.path))) done++; } });
  total += 2; if ((DATA.education || []).length) done++; if ((DATA.family || []).length) done++;
  const completeness = Math.round(done / total * 100);

  const hardPenalty = r.hard.length * 12;
  const riskPenalty = r.risk.length * 4;
  const score = Math.max(0, Math.min(100, Math.round(completeness * 0.55 + 45) - hardPenalty - riskPenalty));

  // 暴露最近一次报告统计（提交后端时随档案一并上报）
  window.SG_LAST_REPORT = {
    score: score, complete: completeness,
    hard: r.hard.length, risk: r.risk.length, tip: r.tip.length
  };

  const lv = score >= 90 ? { t: '优秀 · 可以直接提交', c: '#009944' }
    : score >= 75 ? { t: '良好 · 建议微调后提交', c: '#0a69cd' }
      : score >= 60 ? { t: '及格 · 存在明显缺项', c: '#f77f00' }
        : { t: '待完善 · 缺项较多', c: '#e63946' };

  const ringLen = 2 * Math.PI * 40;
  const ringFill = ringLen * score / 100;

  let h = '';
  h += `<div class="rp-head">
    <h2>网申体检报告</h2>
    <p>基于国家电网招聘平台填报规则，对你填写的模拟简历进行合规性与完整度诊断</p>
    <div class="rp-meta">
      <span>学员姓名：<b>${esc(DATA.basic.name || '未填写')}</b></span>
      <span>目标方向：<b>${esc((DATA.basic.intention || []).join(' / ') || '未填写')}</b></span>
      <span>生成时间：<b>${ts}</b></span>
    </div>
  </div>`;

  h += `<div class="rp-score-row">
    <div class="rp-score-card">
      <div class="rp-ring">
        <svg width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="40" fill="none" stroke="#eef1f5" stroke-width="9"/>
          <circle cx="48" cy="48" r="40" fill="none" stroke="${lv.c}" stroke-width="9"
            stroke-linecap="round" stroke-dasharray="${ringFill} ${ringLen}"/>
        </svg>
        <div class="val">${score}<small>综合评分</small></div>
      </div>
      <div class="rp-score-txt">
        <h3 style="color:${lv.c}">${lv.t}</h3>
        <p>完整度 <b>${completeness}%</b> · 硬伤 <b style="color:#e63946">${r.hard.length}</b> 项 ·
           风险 <b style="color:#f77f00">${r.risk.length}</b> 项 · 优化建议 <b style="color:#0a69cd">${r.tip.length}</b> 项</p>
      </div>
    </div>
    <div class="rp-stats">
      <div class="rp-stat hard"><div class="n">${r.hard.length}</div><div class="l">必须修改</div></div>
      <div class="rp-stat risk"><div class="n">${r.risk.length}</div><div class="l">建议核实</div></div>
      <div class="rp-stat tip"><div class="n">${r.tip.length}</div><div class="l">优化提示</div></div>
      <div class="rp-stat ok"><div class="n">${completeness}%</div><div class="l">完整度</div></div>
    </div>
  </div>`;

  /* 硬伤 */
  h += rpCard('hard', '🔴 必须修改（否则正式网申会被打回）', r.hard,
    '太棒了！未发现硬性问题，必填项与格式校验全部通过。');
  /* 风险 */
  h += rpCard('risk', '🟡 建议核实（易被审核质疑）', r.risk,
    '未发现明显风险项，填报逻辑自洽。');
  /* 提示 */
  h += rpCard('tip', '🔵 优化提示（提升竞争力）', r.tip, '各项加分项均已覆盖，简历完整度很高。');

  /* CTA */
  h += `<div class="rp-cta">
    <div class="cta-txt">
      <h3>这只是模拟填报，正式网申还有更多坑</h3>
      <p>证件照规格、学籍验证报告申请、专业与岗位匹配、属地生源优势判断、面试通知接收……思格就业研究院深耕国网招聘 13 年，可为你做一次 1v1 网申诊断，逐项核对你的真实材料。</p>
    </div>
    <div class="cta-btns">
      <button class="btn btn-brand" id="btnCta">预约网申诊断</button>
    </div>
  </div>`;

  h += `<div class="rp-foot">
    本报告由思格就业研究院网申模拟系统自动生成，判定规则依据国家电网招聘平台公开填报要求整理，仅供参考，<br>
    最终以国家电网各省公司招聘公告及官方系统要求为准。<br>
    思格就业研究院 · 专注电力电网央国企招聘培训
  </div>`;

  $('#reportWrap').innerHTML = h;

  const cta = document.getElementById('btnCta');
  if (cta) cta.onclick = async () => {
    const wx = 'sigedu001';
    const ok = await copyText(wx);
    toast(ok
      ? `微信号 ${wx} 已复制，请打开微信 → 添加朋友 → 粘贴搜索，预约思格老师 1v1 网申诊断`
      : `请手动添加思格老师微信：${wx}`, 'ok');
  };
}

/* 复制文本到剪贴板：HTTPS 下走 Clipboard API，降级 execCommand */
async function copyText(txt) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(txt);
      return true;
    }
  } catch (e) { /* 降级 */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = txt;
    ta.style.cssText = 'position:fixed;opacity:0;left:-999px';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch (e) { return false; }
}

function rpCard(type, title, arr, emptyTxt) {
  const lvMap = { hard: '必须修改', risk: '建议核实', tip: '优化提示' };
  let h = `<div class="rp-card">
    <div class="rp-card-head"><span class="dot ${type}"></span><h3>${title}</h3><span class="cnt">${arr.length} 项</span></div>`;
  if (!arr.length) {
    h += `<div class="rp-empty"><span class="ico">✓</span>${emptyTxt}</div>`;
  } else {
    arr.forEach(it => {
      h += `<div class="rp-item">
        <span class="lv ${type}">${lvMap[type]}</span>
        <div class="txt"><div class="t">${esc(it.t)}</div><div class="d">${esc(it.d)}</div></div>
      </div>`;
    });
  }
  return h + '</div>';
}
