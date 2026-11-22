#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给群成员发「来注册」的提醒邮件。

数据来源是 group_member 白名单，会自动跳过已经注册过的 QQ。

用法：

    # 发给指定的一批 QQ
    python scripts/remind_register.py 1443894651 3233418514

    # 只发给某个身份的人（owner / admin / member）
    python scripts/remind_register.py --role admin

    # 发给所有还没注册的群成员（391 人的群慎用，注意 SMTP 配额）
    python scripts/remind_register.py --pending --limit 20

    # 只看会发给谁，不真发
    python scripts/remind_register.py --role admin --dry-run

SMTP 配置优先读环境变量 QIU_SMTP_*，读不到就去 uwsgi.ini 里翻，
所以在服务器上直接跑就行，不用手动 export。
"""
import argparse
import json
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from config import DB_CONFIG  # noqa: E402

import pymysql  # noqa: E402

ROLE_LABEL = {"owner": "群主", "admin": "群管理员", "member": "群成员"}

SITE = "https://www.xn--rubbish-o27ow52hy3g.xyz"
REGISTER_URL = SITE + "/register"

# 发过谁、什么时候发的，记在这个文件里
LOG_PATH = os.path.join(BASE, "scripts", ".remind_sent.log")


def load_sent():
    """返回 {qq_id: '2026-11-22 16:20'}。"""
    sent = {}
    if not os.path.exists(LOG_PATH):
        return sent
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    sent[rec["qq"]] = rec.get("at", "")
                except Exception:
                    continue
    except OSError:
        pass
    return sent


def mark_sent(qq_id):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"qq": qq_id, "at": datetime.now().strftime("%Y-%m-%d %H:%M")},
                ensure_ascii=False) + "\n")
    except OSError as exc:
        print("  写发送日志失败: %s" % exc)


def load_smtp():
    """环境变量优先，其次从 uwsgi.ini 的 env= 行里读。"""
    cfg = {
        "host": os.environ.get("QIU_SMTP_HOST"),
        "port": os.environ.get("QIU_SMTP_PORT"),
        "user": os.environ.get("QIU_SMTP_USER"),
        "password": os.environ.get("QIU_SMTP_PASS"),
        "from_name": os.environ.get("QIU_MAIL_FROM_NAME"),
    }

    ini = os.path.join(BASE, "uwsgi.ini")
    if os.path.exists(ini) and not (cfg["user"] and cfg["password"]):
        try:
            with open(ini, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith("env=QIU_"):
                        continue
                    k, _, v = line[4:].partition("=")
                    cfg.setdefault("_ini", {})
                    if k == "QIU_SMTP_HOST" and not cfg["host"]:
                        cfg["host"] = v
                    elif k == "QIU_SMTP_PORT" and not cfg["port"]:
                        cfg["port"] = v
                    elif k == "QIU_SMTP_USER" and not cfg["user"]:
                        cfg["user"] = v
                    elif k == "QIU_SMTP_PASS" and not cfg["password"]:
                        cfg["password"] = v
                    elif k == "QIU_MAIL_FROM_NAME" and not cfg["from_name"]:
                        cfg["from_name"] = v
        except Exception as exc:
            print("读取 uwsgi.ini 失败:", exc)

    cfg["host"] = cfg["host"] or "smtp.qq.com"
    cfg["port"] = int(cfg["port"] or 465)
    cfg["from_name"] = cfg["from_name"] or "小秋的垃圾站"
    return cfg


def build_mail(name, qq, role):
    role_label = ROLE_LABEL.get(role, "群成员")

    if role in ("owner", "admin"):
        tail = ("你是%s，注册之后会自动拿到后台权限，可以录入本周榜单、"
                "管理作品推荐。" % role_label)
    else:
        tail = ("注册之后就能在作品推荐页点赞、写评论，"
                "还能在首页看到群友列表。")

    body = """%s 你好：

小秋的垃圾站上线了，来注册个账号吧。

    注册地址：%s

注册时填 QQ 号 %s，系统会往这个 QQ 号对应的 QQ 邮箱发一个验证码，
填进去就能完成注册。

%s

—— 小秋的垃圾站
""" % (name, REGISTER_URL, qq, tail)

    return "【小秋的垃圾站】来注册个账号吧", body


def send(cfg, to_addr, subject, body):
    msg = EmailMessage()
    msg["From"] = formataddr((cfg["from_name"], cfg["user"]))
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=20) as s:
        s.login(cfg["user"], cfg["password"])
        s.send_message(msg)


def main():
    ap = argparse.ArgumentParser(description="给群成员发注册提醒")
    ap.add_argument("qqs", nargs="*", help="要发的 QQ 号，可以给多个")
    ap.add_argument("--role", choices=["owner", "admin", "member"],
                    help="按群身份筛选")
    ap.add_argument("--pending", action="store_true",
                    help="所有还没注册的群成员")
    ap.add_argument("--limit", type=int, default=0, help="最多发几封")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不真发")
    args = ap.parse_args()

    cfg = load_smtp()
    if not (cfg["user"] and cfg["password"]):
        print("没找到 SMTP 配置（QIU_SMTP_USER / QIU_SMTP_PASS）")
        return 1

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            if args.qqs:
                fmt = ",".join(["%s"] * len(args.qqs))
                cur.execute(
                    "SELECT qq_id, nickname, card, role FROM group_member "
                    "WHERE qq_id IN (%s)" % fmt, args.qqs)
                rows = cur.fetchall()
                missing = set(args.qqs) - {r[0] for r in rows}
                for m in missing:
                    print("  跳过 %s：不在群成员白名单里" % m)
            else:
                sql = "SELECT qq_id, nickname, card, role FROM group_member"
                cond, params = [], []
                if args.role:
                    cond.append("role=%s")
                    params.append(args.role)
                if args.pending:
                    cond.append("qq_id NOT IN (SELECT qq_id FROM user WHERE qq_id IS NOT NULL)")
                if cond:
                    sql += " WHERE " + " AND ".join(cond)
                sql += " ORDER BY FIELD(role,'owner','admin','member'), id"
                cur.execute(sql, params)
                rows = cur.fetchall()

            registered = set()
            cur.execute("SELECT qq_id FROM user WHERE qq_id IS NOT NULL")
            for (q,) in cur.fetchall():
                registered.add(q)
    finally:
        conn.close()

    todo = [r for r in rows if r[0] not in registered]
    skipped = len(rows) - len(todo)
    if args.limit:
        todo = todo[:args.limit]

    if not todo:
        print("没有需要发的对象（已注册/被筛掉的 %d 人）" % skipped)
        return 0

    sent_log = load_sent()

    print("待发送 %d 封（跳过已注册 %d 人）" % (len(todo), skipped))
    if args.dry_run:
        print("--- dry-run，不真发 ---")

    ok = fail = 0
    for qq_id, nickname, card, role in todo:
        name = card or nickname or qq_id
        subject, body = build_mail(name, qq_id, role)
        label = "%s (%s, %s)" % (name, qq_id, ROLE_LABEL.get(role, role))
        if qq_id in sent_log:
            label += "  ← %s 已提醒过" % sent_log[qq_id]

        if args.dry_run:
            print("  [预览] %s" % label)
            continue
        try:
            send(cfg, qq_id + "@qq.com", subject, body)
            ok += 1
            mark_sent(qq_id)
            print("  [成功] %s" % label)
        except Exception as exc:
            fail += 1
            print("  [失败] %s -> %s" % (label, exc))

    if not args.dry_run:
        print("完成：成功 %d，失败 %d" % (ok, fail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
