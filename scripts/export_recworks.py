#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 rec_Works 表导出成 RecWorks.html 用的 JSON 快照。

RecWorks.html 是纯静态页（由 nginx 的 try_files 直出），拿不到服务端渲染的数据，
所以这里把数据库里的推荐导成 static/data/recworks.json，页面再 fetch 它。

线上由 cron 每 2 分钟跑一次：

    */2 * * * * <python> /www/wwwroot/qiu_web/scripts/export_recworks.py \
                    >> /www/wwwlogs/qiu_recworks_sync.log 2>&1

手动跑一次：

    python scripts/export_recworks.py
"""
import datetime
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from config import DB_CONFIG  # noqa: E402  复用项目配置，不重复写数据库口令

import pymysql  # noqa: E402

OUT = os.path.join(BASE, 'static', 'data', 'recworks.json')


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    # 这些 QQ 号是后台填的占位，算匿名
    ANON_QQS = {'', '9999999', '99999999'}

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, rw_qq_id, rw_qq_name, rw_work_name, rw_recwork, rw_img_Path, rw_tag "
                "FROM rec_Works ORDER BY id DESC"
            )
            rows = cur.fetchall()

            # 已经注册过账号的 QQ
            cur.execute("SELECT qq_id FROM user WHERE qq_id IS NOT NULL AND qq_id <> ''")
            joined = {str(q) for (q,) in cur.fetchall()}
    finally:
        conn.close()

    items = []
    for r in rows:
        img = (r[5] or '').strip()
        qq = str(r[1] or '').strip()

        if qq in ANON_QQS:
            author_state, author_label = 'anon', '匿名'
        elif qq in joined:
            author_state, author_label = 'joined', '已入站'
        else:
            author_state, author_label = 'absent', '未入站'

        items.append({
            'id': r[0],
            'qq_id': qq,
            'qq_name': r[2] or '',
            'work_name': r[3] or '',
            'recwork': r[4] or '',
            # 后台传的图落在项目根目录的 recworksimg/，nginx 按静态文件直接发
            'images': ['/recworksimg/' + img] if img else [],
            'tag': (r[6] or '').strip(),
            'author_state': author_state,
            'author_label': author_label,
        })

    payload = {
        'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'items': items,
    }

    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    os.chmod(OUT, 0o644)

    print('exported %d item(s) -> %s' % (len(items), OUT))


if __name__ == '__main__':
    main()
