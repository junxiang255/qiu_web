#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把群成员名单导入 group_member 表（注册白名单）。

输入一个 JSON 文件，两种格式都认：

    {"members": [{"qq_id": "123", "nickname": "昵称", "card": "群名片", "role": "member"}]}

    或直接是数组 [{"qq_id": "123", ...}]

role 取值：owner / admin / member（群主 / 管理员 / 成员）。
注册时 owner 和 admin 会自动拿到后台管理员权限。

用法：
    python scripts/sync_group_members.py members.json
    python scripts/sync_group_members.py members.json --prune   # 顺带清掉不在名单里的人
"""
import datetime
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from config import DB_CONFIG  # noqa: E402

import pymysql  # noqa: E402

ROLE_MAP = {
    'owner': 'owner', '群主': 'owner', '1': 'owner',
    'admin': 'admin', '管理员': 'admin', '2': 'admin',
    'member': 'member', '成员': 'member', '3': 'member',
}


def norm_role(v):
    return ROLE_MAP.get(str(v or '').strip().lower(), 'member')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    prune = '--prune' in sys.argv
    if not args:
        print('用法: python scripts/sync_group_members.py members.json [--prune]')
        return 1

    path = args[0]
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    members = data.get('members') if isinstance(data, dict) else data
    if not isinstance(members, list):
        print('JSON 格式不对：需要成员数组')
        return 1

    now = datetime.datetime.now()
    added = updated = skipped = 0
    keep = []

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            for m in members:
                qq = str(m.get('qq_id') or m.get('uin') or m.get('qq') or '').strip()
                if not qq.isdigit():
                    skipped += 1
                    continue
                keep.append(qq)
                nickname = (m.get('nickname') or m.get('nick') or '')[:100]
                card = (m.get('card') or m.get('cardName') or '')[:100]
                role = norm_role(m.get('role'))

                cur.execute("SELECT id FROM group_member WHERE qq_id=%s", (qq,))
                if cur.fetchone():
                    cur.execute(
                        "UPDATE group_member SET nickname=%s, card=%s, role=%s, synced_at=%s "
                        "WHERE qq_id=%s",
                        (nickname, card, role, now, qq))
                    updated += 1
                else:
                    cur.execute(
                        "INSERT INTO group_member (qq_id, nickname, card, role, synced_at, created_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s)",
                        (qq, nickname, card, role, now, now))
                    added += 1

            pruned = 0
            if prune and keep:
                fmt = ','.join(['%s'] * len(keep))
                cur.execute("DELETE FROM group_member WHERE qq_id NOT IN (%s)" % fmt, keep)
                pruned = cur.rowcount

        conn.commit()
    finally:
        conn.close()

    print('导入完成：新增 %d，更新 %d，跳过 %d（QQ 号无效）' % (added, updated, skipped))
    if prune:
        print('已移除不在名单里的人：%d' % pruned)

    # 统计一下各身份人数
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role, COUNT(*) FROM group_member GROUP BY role")
            print('当前白名单：', ', '.join('%s=%d' % (r or '?', c) for r, c in cur.fetchall()))
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
