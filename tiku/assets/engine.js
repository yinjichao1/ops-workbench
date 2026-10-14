/**
 * tiku/assets/engine.js — 判分/计时/存档引擎（纯逻辑，无 DOM，可 Node 冒烟测试）
 * ------------------------------------------------------------------
 * 口径与小程序 miniprogram/utils/exam.js 完全一致（2026-09-21 定稿版）：
 *   · 多选必须完全一致才得分，少选多选均不得分
 *   · 总分 = 答对题分值之和（满分 100，165 题）
 *   · 未作答的题不进错题本
 *   · 存档按 sessionId 隔离，换题库自动重开
 * 依赖：浏览器环境注入 window.EXAM_BANK（assets/bank-data.js）与 localStorage。
 */
(function (root) {
  'use strict';

  var SESSION = {
    id: 'web-mock-2026-10-p3',
    name: '思格电网模考排位赛',
    subtitle: '公共与行业知识 + 专业知识综合卷'
  };
  var DURATION_MIN = 180;
  var BANDS = [
    { min: 80, badge: '优秀', line: '成绩优异，保持状态冲刺目标' },
    { min: 65, badge: '良好', line: '基础扎实，向目标线冲刺' },
    { min: 50, badge: '中等', line: '有差距，需要针对薄弱环节系统补强' },
    { min: 0,  badge: '待提升', line: '先把基础过一遍，再做整卷' }
  ];
  var TIERS = [
    { min: 90, name: '电网尖子', short: 'S' },
    { min: 80, name: '稳进面', short: 'A' },
    { min: 70, name: '中上游', short: 'B' },
    { min: 60, name: '临界线', short: 'C' },
    { min: 45, name: '需补强', short: 'D' },
    { min: 0,  name: '打基础', short: 'E' }
  ];
  var NOTICE = [
    '满分 100 分，共 165 题：单选 95 题、多选 40 题、判断 30 题。',
    '多选需全部选对才得分，少选、多选均不得分。',
    '开考后计时 ' + DURATION_MIN + ' 分钟，中途关闭页面可继续答题，计时不暂停。',
    '交卷后立即出分，可查看错题解析；成绩保存在本机（最近 10 次）。'
  ];
  var PAGE_SIZE = 40;
  var MAX_ATTEMPTS = 10;

  var K_START = 'tiku_start_v1';
  var K_ANSWERS = 'tiku_answers_v1';
  var K_LAST = 'tiku_last_v1';
  var K_ATTEMPTS = 'tiku_attempts_v1';

  function getBank() {
    var b = root.EXAM_BANK;
    return b && Array.isArray(b.questions) ? b : null;
  }
  function byId() {
    var b = getBank();
    var m = {};
    if (b) b.questions.forEach(function (q) { m[q.id] = q; });
    return m;
  }
  function fullScore() {
    var b = getBank();
    return b ? Math.round(b.questions.reduce(function (s, q) { return s + (Number(q.score) || 0); }, 0) * 10) / 10 : 0;
  }
  function overview() {
    var b = getBank();
    var single = 0, multi = 0, judge = 0;
    b.questions.forEach(function (q) {
      if (q.type === '多选题') multi += 1;
      else if (q.type === '判断题') judge += 1;
      else single += 1;
    });
    return { count: b.questions.length, single: single, multi: multi, judge: judge, full: fullScore() };
  }

  /* ── 存档（localStorage，sessionId 隔离） ── */
  function store(key, val) {
    if (val === undefined) {
      try {
        var raw = root.localStorage.getItem(key);
        return raw == null ? null : JSON.parse(raw);
      } catch (e) { return null; }
    }
    try { root.localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* 静默 */ }
  }
  function storeDel(key) { try { root.localStorage.removeItem(key); } catch (e) {} }

  function getStartTs() {
    var v = store(K_START);
    return v && v.sessionId === SESSION.id ? (Number(v.ts) || 0) : 0;
  }
  function markStart(now) {
    if (getStartTs()) return getStartTs();
    var ts = now || Date.now();
    store(K_START, { ts: ts, sessionId: SESSION.id });
    return ts;
  }
  function clearStart() { storeDel(K_START); }
  function getAnswers() {
    var v = store(K_ANSWERS);
    return v && v.sessionId === SESSION.id && v.answers ? v.answers : {};
  }
  function saveAnswers(a) { store(K_ANSWERS, { sessionId: SESSION.id, answers: a, ts: Date.now() }); }
  function clearAnswers() { storeDel(K_ANSWERS); }
  function getAttempts() {
    var v = store(K_ATTEMPTS);
    return v && v.sessionId === SESSION.id && Array.isArray(v.list) ? v.list : [];
  }
  function saveAttempt(result, answers) {
    var list = getAttempts();
    var rec = {
      n: list.length ? (Number(list[list.length - 1].n) || list.length) + 1 : 1,
      ts: Date.now(),
      total: result.total, right: result.right, wrong: result.wrong,
      unanswered: result.unanswered, durationSec: result.durationSec || 0,
      answers: answers || {}
    };
    list.push(rec);
    store(K_ATTEMPTS, { sessionId: SESSION.id, list: list.slice(-MAX_ATTEMPTS) });
    return rec;
  }
  function saveLast(result) {
    var payload = {
      sessionId: SESSION.id, ts: Date.now(),
      total: result.total, right: result.right, wrong: result.wrong,
      unanswered: result.unanswered, durationSec: result.durationSec
    };
    store(K_LAST, payload);
    return payload;
  }

  /* ── 判分 ── */
  function grade(answers) {
    var b = getBank();
    var ans = answers || {};
    var total = 0, right = 0, wrong = 0, unanswered = 0;
    var wrongItems = [];
    b.questions.forEach(function (q) {
      var mine = ans[q.id] == null ? '' : String(ans[q.id]);
      var ok = false;
      if (!mine) { unanswered += 1; }
      else if (q.type === '多选题') {
        ok = mine.split('').sort().join('') === String(q.ans).split('').sort().join('');
      } else {
        ok = mine === String(q.ans);
      }
      if (ok) { right += 1; total += Number(q.score) || 0; }
      else if (mine) { wrong += 1; wrongItems.push({ id: q.id, mine: mine }); }
    });
    total = Math.round(total * 10) / 10;
    var startTs = getStartTs();
    return {
      total: total, right: right, wrong: wrong, unanswered: unanswered,
      answered: b.questions.length - unanswered,
      scoreRate: Math.round((total / 100) * 100),
      wrongItems: wrongItems,
      durationSec: startTs ? Math.round((Date.now() - startTs) / 1000) : 0
    };
  }
  function bandOf(t) { for (var i = 0; i < BANDS.length; i++) if (t >= BANDS[i].min) return BANDS[i]; return BANDS[BANDS.length - 1]; }
  function tierOf(t) { for (var i = 0; i < TIERS.length; i++) if (t >= TIERS[i].min) return TIERS[i]; return TIERS[TIERS.length - 1]; }
  function pages() {
    var b = getBank();
    var out = [];
    for (var i = 0; i < b.questions.length; i += PAGE_SIZE) {
      var seg = b.questions.slice(i, i + PAGE_SIZE);
      out.push({ name: seg[0].id + '-' + seg[seg.length - 1].id, from: seg[0].id, to: seg[seg.length - 1].id, i: out.length });
    }
    return out;
  }
  function pageOf(id) {
    var list = pages();
    for (var i = 0; i < list.length; i++) if (id >= list[i].from && id <= list[i].to) return i;
    return 0;
  }
  function remainMs(now) {
    var DUR = Math.max(1, DURATION_MIN) * 60 * 1000;
    var startTs = getStartTs();
    if (!startTs) return DUR;
    return Math.max(0, startTs + DUR - (now || Date.now()));
  }

  root.TikuEngine = {
    SESSION: SESSION, DURATION_MIN: DURATION_MIN, BANDS: BANDS, TIERS: TIERS, NOTICE: NOTICE,
    PAGE_SIZE: PAGE_SIZE, getBank: getBank, byId: byId, overview: overview, fullScore: fullScore,
    getStartTs: getStartTs, markStart: markStart, clearStart: clearStart,
    getAnswers: getAnswers, saveAnswers: saveAnswers, clearAnswers: clearAnswers,
    getAttempts: getAttempts, saveAttempt: saveAttempt, saveLast: saveLast,
    grade: grade, bandOf: bandOf, tierOf: tierOf, pages: pages, pageOf: pageOf, remainMs: remainMs,
    _keys: { K_START: K_START, K_ANSWERS: K_ANSWERS, K_LAST: K_LAST, K_ATTEMPTS: K_ATTEMPTS }
  };
})(typeof window !== 'undefined' ? window : globalThis);
