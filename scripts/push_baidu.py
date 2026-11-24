#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度普通收录 API 推送（带去重）。

百度对未达标的站点有每日配额限制（本站目前每天 10 条），
所以脚本会记录推过的 URL，下次自动跳过。

用法：
    python scripts/push_baidu.py --token TOKEN              # 推配额内能推的
    python scripts/push_baidu.py --token TOKEN --dry-run    # 只看不推
    python scripts/push_baidu.py --token TOKEN --limit 9    # 指定条数
    python scripts/push_baidu.py --token TOKEN --reset      # 清空推送记录重来
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

SITEMAP = "https://www.xn--rubbish-o27ow52hy3g.xyz/sitemap.xml"
SITE = "https://www.xn--rubbish-o27ow52hy3g.xyz"
API = "http://data.zz.baidu.com/urls"
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".baidu_pushed.log")


def fetch_urls(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        xml = r.read().decode("utf-8", "ignore")
    out, pos = [], 0
    while True:
        a = xml.find("<loc>", pos)
        if a < 0:
            break
        b = xml.find("</loc>", a)
        if b < 0:
            break
        out.append(xml[a + 5:b].strip())
        pos = b + 6
    return out


def load_pushed():
    if not os.path.exists(LOG):
        return set()
    with open(LOG, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_pushed(urls):
    with open(LOG, "a", encoding="utf-8") as f:
        for u in urls:
            f.write(u + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--sitemap", default=SITEMAP)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset", action="store_true", help="清空已推记录")
    args = ap.parse_args()

    if args.reset and os.path.exists(LOG):
        os.remove(LOG)
        print("已清空推送记录")

    all_urls = fetch_urls(args.sitemap)
    pushed = load_pushed()
    todo = [u for u in all_urls if u not in pushed]

    print("sitemap 共 %d 条，已推过 %d 条，待推 %d 条" % (len(all_urls), len(pushed), len(todo)))

    if args.limit:
        todo = todo[:args.limit]
        print("本次限制 %d 条" % len(todo))

    if not todo:
        print("没有待推的 URL 了")
        return 0

    if args.dry_run:
        print("\n[dry-run] 会推这些：")
        for u in todo[:20]:
            print("  " + u)
        if len(todo) > 20:
            print("  ...还有 %d 条" % (len(todo) - 20))
        return 0

    # 关键：site 直接拼进 query，不做 urlencode
    # （urlencode 会把 https:// 变成 https%3A%2F%2F，百度报 site init fail）
    url = "%s?site=%s&token=%s" % (API, SITE, args.token)
    body = "\n".join(todo).encode("utf-8")

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "text/plain", "User-Agent": "curl/8.0"},
        method="POST",
    )

    print("\n推送到百度...")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        print("  HTTP %s: %s" % (e.code, raw))
        return 1
    except Exception as exc:
        print("  请求异常:", exc)
        return 1

    print("  返回:", json.dumps(res, ensure_ascii=False))

    ok = res.get("success", 0)
    remain = res.get("remain", "?")
    if ok:
        # 前 ok 条算推成功（百度按顺序处理）
        save_pushed(todo[:ok])
        print("\n  ✅ 成功 %s 条，今日剩余配额 %s" % (ok, remain))
    else:
        print("\n  ❌ 一条都没推成功")

    for key in ("not_same_site", "not_valid"):
        if res.get(key):
            print("  %s: %d 条" % (key, len(res[key])))
            for u in res[key][:3]:
                print("    " + u)

    if isinstance(remain, int) and remain > 0:
        left = [u for u in all_urls if u not in load_pushed()]
        if left:
            print("\n  还有 %d 条没推，明天配额恢复后再跑一次即可" % len(left))

    return 0


if __name__ == "__main__":
    sys.exit(main())