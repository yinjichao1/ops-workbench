/**
 * tiku/build/verify_tiku_engine.js — 判分引擎冒烟测试（Node，localStorage 打桩）
 * 跑法：node tiku/build/verify_tiku_engine.js
 * 全过输出 ALL n CHECKS PASSED，任何失败 process.exit(1)。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');

// ── 浏览器环境打桩 ──
const storage = {};
const sandbox = {
  window: {},
  localStorage: {
    getItem: (k) => (k in storage ? storage[k] : null),
    setItem: (k, v) => { storage[k] = String(v); },
    removeItem: (k) => { delete storage[k]; }
  },
  Date, Math, JSON, console, Number, String, Array, Object
};
sandbox.window = sandbox; // engine 挂 window 也挂 globalThis
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'assets', 'engine.js'), 'utf8'), sandbox);
const E = sandbox.window.TikuEngine;

let passed = 0;
function check(name, cond) {
  if (!cond) { console.error('FAIL', name); process.exit(1); }
  passed += 1; console.log('ok', passed, name);
}

// ── 无题库态 ──
check('无题库时 getBank 为 null', E.getBank() === null);

// ── 注入样例题库（与正式 exam-bank.js 同结构） ──
sandbox.window.EXAM_BANK = {
  questions: [
    { id: 1, type: '单选题', segs: ['1+1=?'], opts: { A: ['1'], B: ['2'], C: ['3'], D: ['4'] }, ans: 'B', score: 1 },
    { id: 2, type: '多选题', segs: ['下列哪些是偶数？'], opts: { A: ['2'], B: ['3'], C: ['4'], D: ['6'] }, ans: 'ACD', score: 0.5 },
    { id: 3, type: '判断题', segs: ['地球绕太阳转。'], opts: null, ans: '对', score: 0.5 },
    { id: 4, type: '单选题', segs: ['3-1=?'], opts: { A: ['1'], B: ['2'], C: ['3'], D: ['4'] }, ans: 'B', score: 0.5 }
  ]
};
check('题库加载', E.getBank() && E.getBank().questions.length === 4);
const ov = E.overview();
check('overview 题型统计', ov.single === 2 && ov.multi === 1 && ov.judge === 1);
check('overview 满分', ov.full === 2.5);

// ── 判分 ──
let r = E.grade({ 1: 'B', 2: 'ACD', 3: '对', 4: 'B' });
check('全对得分', r.total === 2.5 && r.right === 4 && r.wrong === 0 && r.unanswered === 0);
r = E.grade({ 1: 'A', 2: 'AC', 3: '对', 4: 'B' });
// 多选少选不得分（口径：完全一致）；q1='A' 也错（正确 B）
check('多选少选不得分', r.total === 1 && r.right === 2 && r.wrong === 2);
check('错题进本且含我的作答', r.wrongItems.some(function (w) { return w.id === 2 && w.mine === 'AC'; }));
r = E.grade({ 1: 'B' });
check('未答不入错题本', r.wrongItems.length === 0 && r.unanswered === 3 && r.total === 1);
r = E.grade({ 1: 'B', 2: 'ACD', 3: '错', 4: 'B' });
check('判断题判错', r.right === 3 && r.wrongItems[0].id === 3);

// ── 分屏 ──
check('小卷单屏', E.pages().length === 1 && E.pageOf(3) === 0);

// ── 计时 ──
const DUR = E.DURATION_MIN * 60 * 1000;
check('未进场剩余=整场', E.remainMs(1000) === DUR);
const t0 = 1750000000000;
E.markStart(t0);
check('markStart 后进场时间生效', E.getStartTs() === t0);
check('剩余时间递减', E.remainMs(t0 + 60000) === DUR - 60000);
E.markStart(t0 + 1000); // 二次调用不覆盖
check('markStart 幂等', E.getStartTs() === t0);

// ── 存档与按次档案 ──
E.saveAnswers({ 1: 'B', 2: 'ACD' });
check('作答存取', JSON.stringify(E.getAnswers()) === JSON.stringify({ 1: 'B', 2: 'ACD' }));
const r1 = E.grade({ 1: 'B', 2: 'ACD', 3: '对', 4: 'B' });
E.saveAttempt(r1, { 1: 'B', 2: 'ACD', 3: '对', 4: 'B' });
E.saveAttempt(r1, { 1: 'B' });
const atts = E.getAttempts();
check('按次档案计数', atts.length === 2 && atts[0].n === 1 && atts[1].n === 2);
E.clearAnswers();
check('clearAnswers 清空', Object.keys(E.getAnswers()).length === 0);
E.clearStart();
check('clearStart 清空', E.getStartTs() === 0);
check('存档仍保留（不随作答清除）', E.getAttempts().length === 2);

// ── 档位 ──
check('档位 92 → 电网尖子', E.tierOf(92).name === '电网尖子');
check('档位 61 → 临界线', E.tierOf(61).name === '临界线');
check('档位 30 → 打基础', E.tierOf(30).name === '打基础');
check('分档 82 → 优秀', E.bandOf(82).badge === '优秀');
check('分档 12 → 待提升', E.bandOf(12).badge === '待提升');

// ── sessionId 隔离（模拟换题库：清掉 tiku_start 但保持其他键注入旧 sessionId） ──
storage[E._keys.K_ATTEMPTS] = JSON.stringify({ sessionId: 'old-session', list: [{ n: 1, ts: 1, answers: {} }] });
check('换场次档案自动归零', E.getAttempts().length === 0);

console.log(`\nALL ${passed} CHECKS PASSED`);
