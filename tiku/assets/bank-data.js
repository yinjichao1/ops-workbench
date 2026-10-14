/**
 * tiku/assets/bank-data.js — 题库数据插槽
 * ------------------------------------------------------------------
 * 由《1年真题.docx》《1年真题答案.docx》经转换脚本生成后替换本文件。
 * 结构与小程序 miniprogram/data/exam-bank.js 同一口径：
 *   window.EXAM_BANK = { questions: [...] }
 *   q: {
 *     id:     题号（1 起，连续）,
 *     type:   '单选题' | '多选题' | '判断题',
 *     segs:   [ '题干文本' | {img:'assets/exam/xxx.png'} , ... ],   // 题干分段
 *     opts:   { A:['选项文本'|{img:...},...], B:[...], ... },        // 判断题可为 null
 *     ans:    'A' | 'ABD' | '对' | '错',
 *     score:  1 | 0.5
 *   }
 * 未生成时保持 window.EXAM_BANK = null，页面会提示"题库未加载"。
 */
window.EXAM_BANK = null;
