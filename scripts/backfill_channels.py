"""存量线索渠道回刷脚本（v2 渠道分类，2026-10-31）。

功能：
1. 来源别名归一：线上—新媒体平台/线上—活动/线上—短视频平台 等 → 标准一级渠道。
2. 细分渠道回填：按备注自动分类到白名单（sub_source 列，为空才回填，幂等）。
3. 输出人工补录清单：抖音/视频号/公众号/本地生活中识别为"未标注"的行，
   写入 /tmp/leads_manual_review.csv，由运营翻原始记录补账号后回填。

用法（服务器）：
    cd /opt/ops-workbench && python3 scripts/backfill_channels.py --dry-run   # 只看分布不写库
    cd /opt/ops-workbench && python3 scripts/backfill_channels.py             # 正式回刷
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
    manual = []
    rows = []
    try:
        rows = db.query(Lead).all()
        for r in rows:
            note = r.note or ""
            std = normalize_source(r.source, note)
            changed = False
            if std != (r.source or ""):
                if not dry:
                    r.source = std
                src_fixed += 1
                changed = True
            if not (r.sub_source or "").strip():
                sub = classify_sub_source(std, note)
                if not dry:
                    r.sub_source = sub
                sub_filled += 1
                changed = True
                if std in NEED_SUB_SOURCES and sub == "未标注":
                    manual.append({
                        "ID": r.id, "日期": str(r.date or ""), "姓名": r.name or "",
                        "电话": r.phone or "", "来源": std, "备注": note,
                    })
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

    if manual:
        with open("/tmp/leads_manual_review.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["ID", "日期", "姓名", "电话", "来源", "备注"])
            w.writeheader()
            w.writerows(manual)

    print(f"total={len(rows)} source_fixed={src_fixed} sub_filled={sub_filled} manual_review={len(manual)}" + ("  [DRY-RUN 未写库]" if dry else ""))
    if manual and not dry:
        with open("/tmp/leads_manual_review.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["ID", "日期", "姓名", "电话", "来源", "备注"])
            w.writeheader()
            w.writerows(manual)
        print("人工补录清单 → /tmp/leads_manual_review.csv")
    by_src = {}
    for r in rows:
        note = r.note or ""
        std = normalize_source(r.source, note)
        sub = (r.sub_source or "").strip() or classify_sub_source(std, note)
        by_src[(std, sub)] = by_src.get((std, sub), 0) + 1
    for (src, sub), cnt in sorted(by_src.items(), key=lambda x: (-x[1])):
        print(f"{cnt:>5}  {src}  /  {sub or '-'}")


if __name__ == "__main__":
    main()
