/**
 * tiku/assets/app.js — 思格电网模考排位赛 · 网页版（UI 层）
 * ------------------------------------------------------------------
 * 判分/计时/存档在 assets/engine.js（与小程序 utils/exam.js 同口径）。
 * 本文件只做视图与交互。依赖：engine.js 必须先加载。
 */
(function () {
  'use strict';
  var E = window.TikuEngine;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function toast(m) {
    var t = $('toast');
    t.textContent = m; t.classList.add('show');
    setTimeout(function () { t.classList.remove('show'); }, 1800);
  }
  function fmtUse(sec) {
    var h = Math.floor(sec / 3600), m = Math.round((sec % 3600) / 60);
    return h > 0 ? h + ' 小时 ' + m + ' 分' : m + ' 分';
  }
  function st(v, l) { return '<div class="st"><b>' + esc(v) + '</b><span>' + esc(l) + '</span></div>'; }

  /* ══════════ 视图切换 ══════════ */
  var VIEWS = ['home', 'exam', 'result', 'wrong', 'history'];
  function show(name) {
    VIEWS.forEach(function (v) { $('view-' + v).style.display = v === name ? '' : 'none'; });
    window.scrollTo(0, 0);
  }

  /* ══════════ 题面渲染 ══════════ */
  function segsHtml(segs) {
    if (!segs) return '';
    return segs.map(function (x) {
      if (x && typeof x === 'object' && x.img) return '<img src="' + esc(x.img) + '" alt="题目配图">';
      return esc(x);
    }).join('');
  }
  function optSegsHtml(arr) {
    return (arr || []).map(function (x) {
      if (x && typeof x === 'object' && x.img) return '<img src="' + esc(x.img) + '" alt="选项配图">';
      return esc(x);
    }).join('');
  }
  function optKeys(q) {
    if (q.type === '判断题') return ['对', '错'];
    return Object.keys(q.opts || {}).sort();
  }
  function questionHtml(q, answers) {
    var pick = answers[q.id] || '';
    var keys = optKeys(q);
    var opts = keys.map(function (k) {
      var on = pick.indexOf(k) >= 0;
      var body = q.type === '判断题' ? k : optSegsHtml((q.opts || {})[k]);
      return '<div class="opt' + (on ? ' on' : '') + '" data-id="' + q.id + '" data-k="' + esc(k) + '">' +
        '<span class="k">' + esc(k) + '</span><span>' + body + '</span></div>';
    }).join('');
    return '<div class="q" id="q-' + q.id + '">' +
      '<div class="q__head"><span class="q__no">' + q.id + '</span>' +
      '<span class="q__segs">' + (q.type === '多选题' ? '<b>〔多选〕</b>' : '') + segsHtml(q.segs) + '</span></div>' +
      '<div class="q__opts">' + opts + '</div></div>';
  }

  /* ══════════ 首页 ══════════ */
  function renderHome() {
    $('homeTitle').textContent = E.SESSION.name;
    $('homeSubtitle').textContent = E.SESSION.subtitle;
    $('homeNotice').innerHTML = E.NOTICE.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('');
    if (!E.getBank()) {
      $('bankWarn').style.display = '';
      $('homeStats').innerHTML = '';
      $('btnStart').disabled = true;
      $('btnStart').style.opacity = '.5';
      $('btnContinue').style.display = 'none';
      return;
    }
    $('bankWarn').style.display = 'none';
    $('btnStart').disabled = false;
    $('btnStart').style.opacity = '';
    var ov = E.overview();
    $('homeStats').innerHTML =
      st(ov.count, '题数') + st(ov.full, '满分') + st(E.DURATION_MIN + '分', '时长') + st('即时', '交卷出分');
    var hasProgress = E.getStartTs() > 0 && Object.keys(E.getAnswers()).length > 0;
    $('btnContinue').style.display = hasProgress ? '' : 'none';
  }

  /* ══════════ 答题页 ══════════ */
  var answers = {};
  var curPage = 0;
  var timerId = null;
  var submitting = false;
  var byId = {};

  function renderPage() {
    var ps = E.pages();
    var p = ps[curPage];
    $('pageNav').innerHTML = ps.map(function (x) {
      return '<button class="pg' + (x.i === curPage ? ' on' : '') + '" data-pg="' + x.i + '">' + esc(x.name) + '</button>';
    }).join('');
    $('paper').innerHTML = E.getBank().questions
      .filter(function (q) { return q.id >= p.from && q.id <= p.to; })
      .map(function (q) { return questionHtml(q, answers); }).join('');
    updateCount();
  }
  function updateCount() {
    $('answeredCount').textContent = '已答 ' + Object.keys(answers).length + '/' + E.getBank().questions.length;
  }
  function startTimer() {
    if (timerId) clearInterval(timerId);
    var tick = function () {
      var ms = E.remainMs();
      $('timer').textContent = fmtClock(ms);
      $('timer').classList.toggle('low', ms < 10 * 60 * 1000);
      if (ms <= 0 && !submitting) {
        clearInterval(timerId); timerId = null;
        toast('时间到，自动交卷');
        doSubmit();
      }
    };
    tick();
    timerId = setInterval(tick, 1000);
  }
  function startExam() {
    if (!E.getBank()) return;
    byId = E.byId();
    answers = E.getAnswers();
    E.markStart();
    var ids = Object.keys(answers).map(Number).sort(function (a, b) { return a - b; });
    curPage = ids.length ? E.pageOf(ids[ids.length - 1]) : 0;
    show('exam');
    renderPage();
    startTimer();
  }
  function onPick(e) {
    if (submitting) return;
    var opt = e.target.closest('.opt');
    if (!opt) return;
    var id = Number(opt.getAttribute('data-id'));
    var k = opt.getAttribute('data-k');
    var q = byId[id];
    if (!q) return;
    var pick = answers[id] || '';
    if (q.type === '多选题') {
      var set = pick.split('').filter(Boolean);
      var at = set.indexOf(k);
      if (at >= 0) set.splice(at, 1); else set.push(k);
      pick = set.sort().join('');
    } else {
      pick = pick === k ? '' : k;
    }
    if (pick) answers[id] = pick; else delete answers[id];
    var wrap = $('q-' + id);
    if (wrap) {
      Array.prototype.forEach.call(wrap.querySelectorAll('.opt'), function (el) {
        el.classList.toggle('on', (answers[id] || '').indexOf(el.getAttribute('data-k')) >= 0);
      });
    }
    E.saveAnswers(answers);
    updateCount();
  }
  function renderSheet() {
    $('sheetGrid').innerHTML = E.getBank().questions.map(function (q) {
      return '<div class="cell' + (answers[q.id] ? ' on' : '') + '" data-jump="' + q.id + '">' + q.id + '</div>';
    }).join('');
    $('sheetCount').textContent = '已答 ' + Object.keys(answers).length + '/' + E.getBank().questions.length;
    $('sheet').style.display = '';
  }
  function jumpTo(id) {
    $('sheet').style.display = 'none';
    var idx = E.pageOf(Number(id));
    if (idx !== curPage) { curPage = idx; renderPage(); }
    var el = $('q-' + id);
    if (el) el.scrollIntoView({ block: 'start' });
  }
  function doSubmit() {
    if (submitting) return;
    submitting = true;
    var result = E.grade(answers);
    E.saveAttempt(result, answers);   // 🔴 必须在 clearAnswers 之前
    E.saveLast(result);
    E.clearAnswers();
    E.clearStart();
    if (timerId) { clearInterval(timerId); timerId = null; }
    renderResult(result);
    show('result');
    submitting = false;
  }
  function confirmSubmit() {
    var un = E.getBank().questions.length - Object.keys(answers).length;
    if (un > 0 && !window.confirm('还有 ' + un + ' 题未作答，确认交卷？')) return;
    doSubmit();
  }

  /* ══════════ 成绩页 ══════════ */
  function renderResult(r) {
    var tier = E.tierOf(r.total), band = E.bandOf(r.total);
    $('resTier').textContent = '本场段位 · ' + tier.name + '（' + tier.short + '）';
    $('resScore').textContent = r.total;
    $('resBadge').textContent = band.badge;
    $('resLine').textContent = band.line;
    $('resStats').innerHTML =
      st(r.right, '答对') + st(r.wrong, '答错') + st(r.unanswered, '未答') + st(fmtUse(r.durationSec), '用时');
  }

  /* ══════════ 错题本（按次分栏） ══════════ */
  var curAttempt = -1;
  function renderWrongView() {
    var list = E.getAttempts();
    if (!list.length) {
      $('attemptTabs').innerHTML = '';
      $('wrongList').innerHTML = '<div class="empty">还没有作答记录，先去考一场吧</div>';
      return;
    }
    var activeN = curAttempt < 0 ? list[list.length - 1].n : curAttempt;
    $('attemptTabs').innerHTML = list.slice().reverse().map(function (a) {
      return '<button class="tab' + (a.n === activeN ? ' on' : '') + '" data-att="' + a.n + '">第 ' + a.n + ' 次 · ' + a.total + '分</button>';
    }).join('');
    var att = list.filter(function (a) { return a.n === activeN; })[0] || list[list.length - 1];
    var byIdMap = E.byId();
    var r = E.grade(att.answers || {});
    if (!r.wrongItems.length) {
      $('wrongList').innerHTML = '<div class="empty">这一场全对，没有错题 🎉</div>';
      return;
    }
    $('wrongList').innerHTML = r.wrongItems.map(function (w) {
      var q = byIdMap[w.id];
      if (!q) return '';
      var opts = optKeys(q).map(function (k) {
        var body = q.type === '判断题' ? k : optSegsHtml((q.opts || {})[k]);
        var on = String(q.ans).indexOf(k) >= 0 && String(q.ans).split('').indexOf(k) >= 0;
        return '<div class="opt' + (on ? ' on' : '') + '"><span class="k">' + esc(k) + '</span><span>' + body + '</span></div>';
      }).join('');
      return '<div class="q">' +
        '<div class="q__head"><span class="q__no">' + q.id + '</span><span class="q__segs">' + segsHtml(q.segs) + '</span></div>' +
        '<div class="ansline"><span class="mine">我的答案：' + esc(w.mine || '—') + '</span>' +
        '<span class="key">正确答案：' + esc(q.ans) + '</span></div>' +
        '<div class="q__opts">' + opts + '</div></div>';
    }).join('');
  }

  /* ══════════ 历次成绩 ══════════ */
  function renderHistory() {
    var list = E.getAttempts();
    if (!list.length) {
      $('historyList').innerHTML = '<div class="empty">还没有交卷记录</div>';
      return;
    }
    $('historyList').innerHTML = list.slice().reverse().map(function (a) {
      var d = new Date(a.ts);
      var t = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2) +
        ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
      return '<div class="hist"><b>' + a.total + '<i style="font-size:12px;font-style:normal;color:var(--ink3)"> 分</i></b>' +
        '<div class="meta">第 ' + a.n + ' 次 · ' + t + '<br>答对 ' + a.right + ' / 答错 ' + a.wrong + ' / 未答 ' + a.unanswered +
        ' · 用时 ' + fmtUse(a.durationSec) + '</div></div>';
    }).join('');
  }

  /* ══════════ 事件绑定 ══════════ */
  function bind() {
    $('btnStart').onclick = startExam;
    $('btnContinue').onclick = startExam;
    $('btnBackHome').onclick = function () {
      if (timerId) { clearInterval(timerId); timerId = null; }
      renderHome(); show('home');
    };
    $('btnSubmit').onclick = confirmSubmit;
    $('btnSheet').onclick = renderSheet;
    $('btnSheetClose').onclick = function () { $('sheet').style.display = 'none'; };
    $('paper').addEventListener('click', onPick);
    $('pageNav').addEventListener('click', function (e) {
      var b = e.target.closest('.pg');
      if (b) { curPage = Number(b.getAttribute('data-pg')); renderPage(); window.scrollTo(0, 0); }
    });
    $('sheetGrid').addEventListener('click', function (e) {
      var c = e.target.closest('[data-jump]');
      if (c) jumpTo(Number(c.getAttribute('data-jump')));
    });
    $('btnGoWrong').onclick = function () { curAttempt = -1; renderWrongView(); show('wrong'); };
    $('btnGoHome').onclick = function () { renderHome(); show('home'); };
    $('btnWrong').onclick = function () { curAttempt = -1; renderWrongView(); show('wrong'); };
    $('btnWrongBack').onclick = function () { renderHome(); show('home'); };
    $('btnHistory').onclick = function () { renderHistory(); show('history'); };
    $('btnHistoryBack').onclick = function () { renderHome(); show('home'); };
    $('attemptTabs').addEventListener('click', function (e) {
      var t = e.target.closest('.tab');
      if (!t) return;
      curAttempt = Number(t.getAttribute('data-att'));
      renderWrongView();
    });
  }

  bind();
  renderHome();
  show('home');
})();
