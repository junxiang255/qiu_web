#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新计算用户经验值。

正确算法：
    应得 exp = 推荐作品数 × 50 + 签到经验合计（checkin.exp_gained）

处理原则：
- 当前 < 应得  → 补齐差额（漏发的补上）
- 当前 > 应得  → 不动（可能有别的来源，或历史手工调整）
- 开发者账号   → 跳过（exp 是手工设的封顶值）

用法：
    python3 scripts/recalc_exp.py           # 只看，不写
    python3 scripts/recalc_exp.py --apply   # 真的写库
"""
import argparse
import os
import sys

sys.path.insert(0, "/www/wwwroot/qiu_web")

from sqlalchemy import text

import app as A

# 不参与自动重算的账号（手工设过 exp）
SKIP_QQ = {"2847407092"}   # junxiang255 开发者 25500

WORK_EXP = 50
DEV_CEIL = 25500
NORMAL_CEIL = 10000

SQL = """
SELECT
    u.id,
    u.username,
    u.qq_id,
    u.exp                                              AS cur_exp,
    (SELECT COUNT(*) FROM rec_Works w
      WHERE w.rw_qq_id = u.qq_id)                      AS works,
    (SELECT IFNULL(SUM(c.exp_gained), 0) FROM checkin c
      WHERE c.user_id = u.id)                          AS ck_exp
FROM user u
ORDER BY u.id
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的写库")
    args = ap.parse_args()

    with A.app.app_context():
        rows = A.db.session.execute(text(SQL)).fetchall()

        fixes = []
        skipped = []

        for r in rows:
            uid, uname, qq, cur, works, ck = r
            expect = works * WORK_EXP + ck
            diff = expect - cur

            if str(qq) in SKIP_QQ:
                skipped.append((uname, qq, cur, expect, "开发者账号"))
                continue

            if diff > 0:
                fixes.append((uid, uname, qq, cur, works, ck, expect, diff))

        print("=" * 70)
        print("%-14s %-12s %6s %5s %6s %7s %7s" % (
            "用户名", "QQ", "当前", "作品", "签到", "应得", "要补"))
        print("-" * 70)

        for uid, uname, qq, cur, works, ck, expect, diff in fixes:
            print("%-14s %-12s %6d %5d %6d %7d %+7d" % (
                (uname or "")[:14], qq, cur, works, ck, expect, diff))

        print("-" * 70)
        print("要补的人: %d 个，合计 +%d exp" % (
            len(fixes), sum(f[7] for f in fixes)))

        for uname, qq, cur, expect, why in skipped:
            print("跳过: %-14s %-12s 当前 %d（%s）" % (uname or "", qq, cur, why))

        if not fixes:
            print("\n没有欠账，所有人都是齐的。")
            return

        if not args.apply:
            print("\n这是预演。加 --apply 才会真的写库。")
            return

        print("\n开始写库…")
        for uid, uname, qq, cur, works, ck, expect, diff in fixes:
            new = cur + diff
            # 普通账号封顶 10000
            if new > NORMAL_CEIL:
                new = NORMAL_CEIL
            A.db.session.execute(
                text("UPDATE user SET exp = :e WHERE id = :i"),
                {"e": new, "i": uid},
            )
            print("  %-14s %d -> %d" % ((uname or "")[:14], cur, new))

        A.db.session.commit()
        print("\n完成，共补 %d 人。" % len(fixes))


if __name__ == "__main__":
    main()
