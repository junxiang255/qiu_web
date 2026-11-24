#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把站点 URL 推送给百度站长平台（普通收录 - API 推送）。

用法：

    # 先看会推哪些，不真推
    python scripts/push_baidu.py --token YOUR_TOKEN --dry-run

    # 正式推送
    python scripts/push_baidu.py --token YOUR_TOKEN

    # 只推一部分（百度每天有配额）
    python scripts/push_baidu.py --token YOUR_TOKEN --limit 50

token 在 https://ziyuan.baidu.com → 普通收录 → API 提交 里拿。
站点必须先在百度站长平台验证通过，否则会返回 not_same_site。
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

SITEMAP = "https://www.xn--rubbish-o27ow52hy3g.xyz/sitemap.xml"
SITE = "https://www.xn--rubbish-o27ow52hy3g.xyz"
API = "http://data.zz.baidu.com/urls"


def fetch_urls(sitemap_url):
    """从 sitemap.xml 里抠出所有 <loc>。"""
    req = urllib.request.Request(sitemap_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        xml = r.read().decode("utf-8", "ignore")

    urls = []
    pos = 0
    while True:
        a = xml.find("<loc>", pos)
        if a < 0:
            break
        b = xml.find("</loc>", a)
        if b < 0:
            break
        urls.append(xml[a + 5:b].strip())
        pos = b + 6
    return urls


def push(token, urls, dry_run=False):
    qs = urllib.parse.urlencode({"site": SITE, "token": token})
    body = "\n".join(urls).encode("utf-8")
    req = urllib.request.Request(
        API + "?" + qs,
        data=body,
        headers={
            "Content-Type": "text/plain",
            "User-Agent": "Mozilla/5.0",
            "Host": "data.zz.baidu.com",
        },
        method="POST",
    )

    if dry_run:
        print("  [dry-run] 会 POST %d 条到 %s" % (len(urls), API))
        for u in urls[:5]:
            print("    " + u)
        if len(urls) > 5:
            print("    ...还有 %d 条" % (len(urls) - 5))
        return None

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8", "ignore") or "{}")
    except Exception as exc:
        return {"error": str(exc)}


def main():
    ap = argparse.ArgumentParser(description="百度普通收录 API 推送")
    ap.add_argument("--token", required=True, help="百度站长平台的推送 token")
    ap.add_argument("--sitemap", default=SITEMAP, help="sitemap 地址")
    ap.add_argument("--limit", type=int, default=0, help="最多推几条（0 = 全部）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不真推")
    args = ap.parse_args()

    print("读取 sitemap:", args.sitemap)
    urls = fetch_urls(args.sitemap)
    print("  拿到 %d 条 URL" % len(urls))

    if args.limit:
        urls = urls[:args.limit]
        print("  限制为前 %d 条" % len(urls))

    if not urls:
        print("sitemap 里没有 URL，退出")
        return 1

    print()
    print("推送到百度（site=%s）" % SITE)
    res = push(args.token, urls, args.dry_run)

    if res is None:
        return 0

    print()
    if "error" in res:
        print("  请求失败:", res["error"])
        return 1

    print("  返回:", json.dumps(res, ensure_ascii=False))

    if res.get("success"):
        print()
        print("  ✅ 成功推送 %s 条，今日剩余配额 %s" % (res["success"], res.get("remain", "?")))
    else:
        print()
        print("  ❌ 没推成功，看上面的返回")

    for key in ("not_same_site", "not_valid"):
        if res.get(key):
            print("  %s: %d 条" % (key, len(res[key])))
            for u in res[key][:3]:
                print("    " + u)

    return 0


if __name__ == "__main__":
    sys.exit(main())