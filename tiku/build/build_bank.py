# -*- coding: utf-8 -*-
"""从《1年真题.docx》《1年真题答案.docx》重建 tiku 题库（干净重写版）。

产出：
  ../assets/bank-data.js      题库（window.EXAM_BANK）
  ../assets/exam/<name>.png   图片素材（png/jpeg 直拷，wmf/emf 经 PowerShell GDI+ 3x 渲染）
  _bank_check.txt             构建报告
  _convert.ps1 / _media/      wmf/emf 转换中间产物

口径（2026-09-21 教研定稿）：
  1-20   综合单选   0.5 分/题                 小计 10
  21-85  专业单选   5 道 1 分(SEED=20260921 随机) + 60 道 0.5   小计 35
  86-95  综合多选   0.5                       小计 5
  96-125 专业多选   1.0                       小计 30
  126-155 专业判断  0.5                       小计 15
  156-165 资料分析  0.5                       小计 5
  全卷 165 题 100 分。判断题答案 A→对 B→错；多选按字母序输出。
"""
import json
import os
import random
import re
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # 仓库根
ASSETS = os.path.join(ROOT, "tiku", "assets")
EXAM_IMG = os.path.join(ASSETS, "exam")
Q_DOCX = os.path.join(HERE, "_src", "1年真题.docx")
A_DOCX = os.path.join(HERE, "_src", "1年真题答案.docx")
MEDIA_DIR = os.path.join(HERE, "_media")

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A_NS = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
V_NS = 'urn:schemas-microsoft-com:vml'

SEED = 20260921

SECTIONS = [
    (1, 20, "综合单选题", 0.5, "单选题"),
    (21, 85, "专业单选题", "special", "单选题"),   # 5 道 1 分 + 60 道 0.5
    (86, 95, "综合多选题", 0.5, "多选题"),
    (96, 125, "专业多选题", 1.0, "多选题"),
    (126, 155, "专业判断题", 0.5, "判断题"),
    (156, 165, "资料分析题", 0.5, "单选题"),
]
SECTION_RE = re.compile(r'^[一二三四五六七八九十]+、\s*(.+?)（(\d+)分）$')
MAT_RE = re.compile(r'^\d+、根据下面资料回答(\d+)-(\d+)题')
Q_RE = re.compile(r'^(\d+)[.．](.*)$')          # 题号后是点号（材料头用顿号，不会误匹配）
OPT_RE = re.compile(r'^([A-F])[.．、]\s*(.*)$')
ANS_RE = re.compile(r'^(\d+)[.、．]\s*([A-F]+|对|错)\s*$')
JUNK_RE = re.compile(r'^(扫码观看|教授视频精讲)$')   # 卷尾推广残留


def rels_of(z):
    rels = {}
    rx = ET.fromstring(z.read('word/_rels/document.xml.rels'))
    for rel in rx:
        rels[rel.get('Id')] = rel.get('Target')
    return rels


def para_tokens(p):
    """段落内按文档顺序产出 ('t', 文本) / ('i', rel目标)。"""
    out = []
    for node in p.iter():
        if node.tag == W + 't':
            out.append(('t', node.text or ''))
        elif node.tag == A_NS + 'blip':
            out.append(('i', node.get(R_NS + 'embed')))
        elif node.tag == '{%s}imagedata' % V_NS:
            out.append(('i', node.get(R_NS + 'id')))
    return out


def parse_paper(path):
    """返回 (段落数组, rels)。段落 = {'text': str, 'imgs': [媒体目标]}。"""
    z = zipfile.ZipFile(path)
    rels = rels_of(z)
    doc = ET.fromstring(z.read('word/document.xml'))
    body = doc.find(W + 'body')
    paras = []
    for p in body.iter(W + 'p'):
        toks = para_tokens(p)
        text = ''.join(t for k, t in toks if k == 't').strip()
        imgs = [rels[rid] for k, rid in toks if k == 'i' and rid in rels]
        if text or imgs:
            paras.append({'text': text, 'imgs': imgs})
    return paras, rels


def segs_append(segs, text, imgs):
    if text:
        segs.append(text)
    for t in imgs:
        segs.append({'img': 'assets/exam/%s.png' % media_name(t)})


def media_name(target):
    """'media/image6.wmf' -> 'image6'。"""
    return os.path.splitext(os.path.basename(target))[0]


def parse_questions(qp):
    """线性解析题目卷 → (questions, materials, warnings)。"""
    questions = {}       # no -> {'segs':[], 'opts':{}, 'section':(lo,hi,name)}
    materials = {}       # (lo,hi) -> [segs]
    warnings = []
    cur_sec = None
    mat_range = None     # 当前材料覆盖的题号范围
    cur_no = None
    cur_opt = None

    for p in qp:
        text, imgs = p['text'], p['imgs']
        m_sec = SECTION_RE.match(text)
        m_mat = MAT_RE.match(text)
        m_q = Q_RE.match(text)
        m_opt = OPT_RE.match(text)

        if m_sec:
            name, declared = m_sec.group(1), int(m_sec.group(2))
            cur_sec = next(((lo, hi, n) for lo, hi, n, _, _ in SECTIONS if n == name), None)
            if cur_sec is None:
                raise SystemExit('未知段名: ' + text)
            declared_expect = {10: 20, 35: 65, 5: 10, 30: 30, 15: 30}[declared] if declared in (10, 35, 5, 30, 15) else None
            mat_range = None
            cur_no = None
            cur_opt = None
            continue
        if cur_sec is None or JUNK_RE.match(text):
            continue  # 卷首标题 / 卷尾推广
        if m_mat:
            lo, hi = int(m_mat.group(1)), int(m_mat.group(2))
            mat_range = (lo, hi)
            materials[(lo, hi)] = []
            cur_no, cur_opt = None, None
            continue
        if m_mat is None and mat_range is not None and cur_no is None and not m_q:
            # 材料正文（含图）：仅在材料头与该组第一题之间累积
            segs_append(materials[mat_range], text, imgs)
            continue
        if m_q:
            no = int(m_q.group(1))
            lo, hi, _ = cur_sec
            if no in questions:
                raise SystemExit('题号重复: %d' % no)
            if not (lo <= no <= hi):
                raise SystemExit('题号 %d 越界（当前段 %s）' % (no, cur_sec))
            cur_no, cur_opt = no, None
            segs = []
            segs_append(segs, m_q.group(2).strip(), imgs)
            questions[no] = {'segs': segs, 'opts': {}, 'section': cur_sec}
            continue
        if m_opt and cur_no is not None:
            cur_opt = m_opt.group(1)
            segs = []
            segs_append(segs, m_opt.group(2).strip(), imgs)
            questions[cur_no]['opts'][cur_opt] = segs
            continue
        # 续行：题干或选项折行
        if cur_no is not None:
            segs = questions[cur_no]['opts'][cur_opt] if cur_opt else questions[cur_no]['segs']
            segs_append(segs, text, imgs)
        elif text or imgs:
            warnings.append('段内游离段落(未入题): ' + (text or '[IMG]')[:50])
    return questions, materials, warnings


def parse_answers(ap):
    answers = {}
    for p in ap:
        m = ANS_RE.match(p['text'])
        if m:
            answers[int(m.group(1))] = m.group(2)
    for no in range(126, 156):
        if no in answers:
            answers[no] = {'A': '对', 'B': '错'}.get(answers[no], answers[no])
    return answers


def run_convert(convert):
    """生成 _convert.ps1 并执行（GDI+ 渲染矢量图，3x 白底 PNG）。"""
    if not convert:
        return
    lines = ["Add-Type -AssemblyName System.Drawing", ""]
    for src, dst in convert:
        s = src.replace("\\", "\\\\")
        d = dst.replace("\\", "\\\\")
        lines.append(
            "$i=[System.Drawing.Image]::FromFile('%s');"
            "$sc=3.0; $w=[int]($i.Width*$sc); $h=[int]($i.Height*$sc);"
            "if($w -gt 1600){$sc=1600.0/$i.Width; $w=1600; $h=[int]($i.Height*$sc)};"
            "$b=New-Object System.Drawing.Bitmap($w,$h);"
            "$g=[System.Drawing.Graphics]::FromImage($b);"
            "$g.Clear([System.Drawing.Color]::White);"
            "$g.InterpolationMode='HighQualityBicubic';"
            "$g.DrawImage($i,0,0,$w,$h);"
            "$b.Save('%s',[System.Drawing.Imaging.ImageFormat]::Png);"
            "$g.Dispose();$b.Dispose();$i.Dispose()" % (s, d))
    ps1 = os.path.join(HERE, '_convert.ps1')
    with open(ps1, 'w', encoding='ascii') as f:
        f.write('\n'.join(lines) + '\n')
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-File', ps1], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('PowerShell 转换失败:\n' + r.stdout + '\n' + r.stderr)


def main():
    qp, qrels = parse_paper(Q_DOCX)
    ap, _ = parse_paper(A_DOCX)
    questions, materials, warnings = parse_questions(qp)
    answers = parse_answers(ap)

    report = []
    # ── 材料附加 ──
    for (lo, hi), buf in materials.items():
        if not buf:
            report.append('!! 材料 %d-%d 为空' % (lo, hi))
        for no in range(lo, hi + 1):
            if no in questions:
                questions[no]['segs'] = list(buf) + questions[no]['segs']
    cover = sorted(n for (lo, hi) in materials for n in range(lo, hi + 1))
    if cover != list(range(156, 166)):
        report.append('!! 材料覆盖异常: %s' % cover)

    # ── 媒体导出（png 直拷；wmf/emf 落盘待渲染） ──
    used_targets = {t for p in qp for t in p['imgs']}
    z = zipfile.ZipFile(Q_DOCX)
    convert = []
    copied = 0
    os.makedirs(EXAM_IMG, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    for target in sorted(used_targets):
        if not target.startswith('media/'):
            continue
        stem, ext = os.path.splitext(os.path.basename(target))
        raw = z.read('word/' + target)
        if ext.lower() in ('.png', '.jpg', '.jpeg', '.gif'):
            with open(os.path.join(EXAM_IMG, stem + '.png'), 'wb') as f:
                f.write(raw)
            copied += 1
        else:
            src = os.path.join(MEDIA_DIR, os.path.basename(target))
            with open(src, 'wb') as f:
                f.write(raw)
            convert.append((src, os.path.join(EXAM_IMG, stem + '.png')))

    # ── 题161（柱状图选择题）：image32 四象限切分为 A-D 选项图 ──
    if 161 in questions and not questions[161]['opts']:
        from PIL import Image
        src = os.path.join(EXAM_IMG, 'image32.png')
        im = Image.open(src)
        w, h = im.size
        boxes = {'A': (0, 0, w // 2, h // 2), 'B': (w // 2, 0, w, h // 2),
                 'C': (0, h // 2, w // 2, h), 'D': (w // 2, h // 2, w, h)}
        for L, box in boxes.items():
            im.crop(box).save(os.path.join(EXAM_IMG, 'image32-%s.png' % L.lower()))
            questions[161]['opts'][L] = [{'img': 'assets/exam/image32-%s.png' % L.lower()}]
        questions[161]['segs'] = [s for s in questions[161]['segs']
                                  if not (isinstance(s, dict) and s.get('img', '').endswith('image32.png'))]
        report.append('题161: image32 (%dx%d) 四象限切分为 A-D 选项图' % (w, h))

    # ── 分值方案 ──
    rng = random.Random(SEED)
    one_point = set(rng.sample(range(21, 86), 5))
    bank = []
    score_sum = 0.0
    for no in range(1, 166):
        q = questions.get(no)
        if q is None:
            raise SystemExit('题号缺失: %d' % no)
        lo, hi, name = q['section']
        _, _, _, sec_score, qtype = next(s for s in SECTIONS if s[0] == lo)
        score = 1.0 if no in one_point else (0.5 if isinstance(sec_score, str) else sec_score)
        ans = answers.get(no)
        if ans is None:
            raise SystemExit('答案缺失: %d' % no)
        if qtype == '判断题':
            if ans not in ('对', '错'):
                raise SystemExit('判断题答案异常 %d: %s' % (no, ans))
            opts = None
        else:
            keys = sorted(q['opts'].keys())
            if len(keys) < 2:
                raise SystemExit('选项不足 %d: %s' % (no, keys))
            if len(keys) > 6 or any(k not in 'ABCDEF' for k in keys):
                raise SystemExit('选项键异常 %d: %s' % (no, keys))
            if qtype == '多选题':
                if len(ans) < 2 or any(c not in keys for c in ans):
                    raise SystemExit('多选答案异常 %d: ans=%s keys=%s' % (no, ans, keys))
                ans = ''.join(sorted(ans))
            else:
                if len(ans) != 1 or ans not in keys:
                    raise SystemExit('单选答案异常 %d: ans=%s keys=%s' % (no, ans, keys))
            opts = {k: q['opts'][k] for k in sorted(q['opts'])}
        if not q['segs']:
            raise SystemExit('题干为空: %d' % no)
        score_sum += score
        bank.append({'id': no, 'type': qtype, 'segs': q['segs'], 'opts': opts,
                     'ans': ans, 'score': score})

    # ── 断言 ──
    assert len(bank) == 165, len(bank)
    assert abs(score_sum - 100.0) < 1e-6, score_sum
    counts = {}
    for lo, hi, name, _, qtype in SECTIONS:
        seg = [q for q in bank if lo <= q['id'] <= hi]
        counts[name] = len(seg)
        exp = {1: 20, 21: 65, 86: 10, 96: 30, 126: 30, 156: 10}[lo]
        assert len(seg) == exp, (name, len(seg), exp)
    assert sum(1 for q in bank if q['score'] == 1.0 and 21 <= q['id'] <= 85) == 5

    # ── 公式图渲染（wmf/emf → PNG，GDI+ 3x） ──
    run_convert(convert)

    # ── 产出 bank-data.js ──
    js = ('/**\n'
          ' * tiku/assets/bank-data.js — 由 tiku/build/build_bank.py 自动生成，勿手改。\n'
          ' * 来源：《1年真题.docx》《1年真题答案.docx》；口径 2026-09-21 教研定稿。\n'
          ' * 165 题 100 分；SEED=%d；1 分题：%s\n'
          ' */\n'
          'window.EXAM_BANK = %s;\n'
          % (SEED, ','.join(str(n) for n in sorted(one_point)),
             json.dumps({'questions': bank}, ensure_ascii=False, separators=(',', ':'))))
    with open(os.path.join(ASSETS, 'bank-data.js'), 'w', encoding='utf-8') as f:
        f.write(js)

    # ── 报告 ──
    report.append('题目卷段落: %d | 答案卷段落: %d' % (len(qp), len(ap)))
    report.append('段题量: ' + json.dumps(counts, ensure_ascii=False))
    report.append('全卷: %d 题 / %.1f 分' % (len(bank), score_sum))
    report.append('1 分题(21-85, SEED=%d): %s' % (SEED, sorted(one_point)))
    report.append('图片: 直拷 %d 张, 公式渲染 %d 张 (wmf/emf → PNG 3x)' % (copied, len(convert)))
    for t in sorted(used_targets):
        report.append('  media: %s → assets/exam/%s.png' % (t, media_name(t)))
    report += warnings
    with open(os.path.join(HERE, '_bank_check.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(report) + '\n')
    print('\n'.join(report))
    print('OK — bank-data.js 已生成')


if __name__ == '__main__':
    main()
