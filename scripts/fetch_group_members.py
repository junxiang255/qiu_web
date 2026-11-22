#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用浏览器里的 qun.qq.com 登录态抓群成员，输出 members.json。

用法：
    1. 浏览器打开 https://qun.qq.com/member.html 并用要用的 QQ 登录
    2. F12 -> Network 随便点一个请求，把 Request Headers 里的 Cookie 整行复制下来
    3. 运行：
         python scripts/fetch_group_members.py --cookie "uin=o028479xxxx; skey=@xxxxxx; p_skey=xxxxx" --group 707983601

只要 Cookie 里有 uin / skey（p_skey 可选）就够。
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

API_LIST = 'https://qun.qq.com/cgi-bin/qun_mgr/get_group_list'
API_MEMBERS = 'https://qun.qq.com/cgi-bin/qun_mgr/search_group_members'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def parse_cookie(raw):
    out = {}
    for part in raw.replace('\n', ';').split(';'):
        part = part.strip()
        if not part or '=' not in part:
            continue
        k, v = part.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def calc_bkn(skey):
    e = 0
    for c in skey:
        e += (e << 5) + ord(c)
    return e & 0x7fffffff


def post(url, cookie, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('User-Agent', UA)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.add_header('Referer', 'https://qun.qq.com/member.html')
    req.add_header('Cookie', '; '.join('%s=%s' % (k, v) for k, v in cookie.items()))
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cookie', required=True, help='qun.qq.com 的 Cookie 整行')
    ap.add_argument('--group', default='707983601', help='群号，默认小秋の垃圾桶')
    ap.add_argument('--out', default='members.json')
    ap.add_argument('--page-size', type=int, default=200)
    args = ap.parse_args()

    cookie = parse_cookie(args.cookie)
    skey = cookie.get('skey') or cookie.get('p_skey')
    if not skey:
        print('Cookie 里没找到 skey，无法计算 bkn')
        return 1
    bkn = calc_bkn(skey)

    # 先确认这个群在不在账号的群列表里
    try:
        gl = post(API_LIST, cookie, {'bkn': bkn})
    except Exception as e:
        print('拉群列表失败:', e)
        return 1

    if gl.get('ec') != 0:
        print('接口返回错误:', gl)
        return 1

    groups = []
    for key in ('create', 'manage', 'join'):
        groups.extend(gl.get(key) or [])
    hit = [g for g in groups if str(g.get('gc')) == str(args.group)]

    if hit:
        print('已确认群：%s（%s 人）' % (hit[0].get('gn'), hit[0].get('member_num')))
    else:
        print('警告：这个账号的群列表里没看到 %s，仍然尝试拉取' % args.group)

    members = []
    start = 0
    while True:
        resp = post(API_MEMBERS, cookie, {
            'gc': args.group, 'st': start, 'end': start + args.page_size - 1,
            'sort': 0, 'bkn': bkn,
        })
        if resp.get('ec') != 0:
            print('拉成员失败:', resp)
            break
        chunk = resp.get('mems') or []
        for m in chunk:
            members.append({
                'qq_id': str(m.get('uin')),
                'nickname': m.get('nick') or '',
                'card': m.get('card') or '',
                'role': {0: 'owner', 1: 'admin'}.get(m.get('role'), 'member'),
            })
        total = resp.get('count') or 0
        print('  已取 %d / %d' % (len(members), total))
        if len(members) >= total or not chunk:
            break
        start += args.page_size
        time.sleep(0.4)

    payload = {'group_id': args.group, 'count': len(members), 'members': members}
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print('已写入 %s，共 %d 人' % (args.out, len(members)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
