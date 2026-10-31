"""存量线索渠道回刷脚本（v2 渠道分类，2026-10-31）。

功能：
1. 来源别名归一：线上—新媒体平台/线上—活动/线上—短视频平台 等 → 标准一级渠道。
2. 细分渠道回填：按备注自动分类到白名单（sub_source 列，为空才回填，幂等）；
   规则升级后对历史"未标注"行自动重判（自愈）。
3. 输出人工补录清单：每次运行按当前库重算——抖音/视频号/公众号/本地生活
   中 sub_source 仍为"未标注"的行，写入 /tmp/leads_manual_review.csv。

用法（服务器，必须带 .env 环境）：
    cd /opt/ops-workbench && set -a && . ./.env && set +a
    ./venv/bin/python scripts/backfill_channels.py --dry-run   # 只看分布不写库
    ./venv/bin/python scripts/backfill_channels.py             # 正式回刷
幂等：可重复执行，第二次运行 changed=0。
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Lead, SessionLocal  # noqa: E402
from app.channel_config import normalize_source, classify_sub_source  # noqa: E402

NEED_SUB_SOURCES = {"抖音", "微信视频号", "微信公众号", "本地生活平台"}


def main():
    dry = "--dry-run" in sys.argv
    db = SessionLocal()
    src_fixed = 0
    sub_filled = 0
    sub_healed = 0
    manual = []
    total = 0
    by_src = {}
    try:
        rows = db.query(Lead).all()
        total = len(rows)
        for r in rows:
            note = r.note or ""
            std = normalize_source(r.source, note)
            changed = False
            if std != (r.source or ""):
                if not dry:
                    r.source = std
                src_fixed += 1
                changed = True
            cur_sub = (r.sub_source or "").strip()
            if not cur_sub:
                sub = classify_sub_source(std, note)
                if not dry:
                    r.sub_source = sub
                changed = True
                if sub:  # 无二级渠道（AI搜索/小程序等）保持空串，不计入回填数
                    sub_filled += 1
            elif cur_sub == "未标注" and std in NEED_SUB_SOURCES:
                # 自愈：规则升级后重判历史未标注行，仍判不出才保留
                better = classify_sub_source(std, note)
                if better != "未标注":
                    if not dry:
                        r.sub_source = better
                    sub_healed += 1
                    changed = True
            # 人工清单按当前库最终状态重算（含历史未标注行）
            final_sub = (r.sub_source or "").strip() or ""
            if std in NEED_SUB_SOURCES and final_sub == "未标注":
                manual.append({
                    "ID": r.id, "日期": str(r.date or ""), "姓名": r.name or "",
                    "电话": r.phone or "", "来源": std, "备注": note,
                })
            # 分布统计（commit 会过期属性，必须在会话内完成快照）
            note2 = r.note or ""
            std2 = normalize_source(r.source, note2)
            sub2 = (r.sub_source or "").strip() or classify_sub_source(std2, note2)
            by_src[(std2, sub2)] = by_src.get((std2, sub2), 0) + 1
            if changed and dry:
                db.expunge(r)
        if not dry:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"total={total} source_fixed={src_fixed} sub_filled={sub_filled} healed={sub_healed} manual_review={len(manual)}" + ("  [DRY-RUN 未写库]" if dry else ""))
    with open("/tmp/leads_manual_review.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["ID", "日期", "姓名", "电话", "来源", "备注"])
        w.writeheader()
        w.writerows(manual)
    if not dry:
        print("人工补录清单 → /tmp/leads_manual_review.csv")
    for (src, sub), cnt in sorted(by_src.items(), key=lambda x: (-x[1])):
        print(f"{cnt:>5}  {src}  /  {sub or '-'}")


if __name__ == "__main__":
    main()
