#!/usr/bin/env bash
# 备份脚本：数据库 dump +（可选）站点代码打包
#
#   bash scripts/backup.sh            # 只备份数据库
#   bash scripts/backup.sh --full     # 数据库 + 站点代码（不含 .git / recworksimg）
#
# 备份统一放在 /www/backup/qiu_web/ 下，不占项目目录。

set -u

BASE=/www/wwwroot/qiu_web
BK=/www/backup/qiu_web
KEEP_DB=30          # 数据库备份保留份数
TS=$(date +%Y%m%d_%H%M%S)
FULL=0
[ "${1:-}" = "--full" ] && FULL=1

mkdir -p "$BK/db" "$BK/site"

# 从 config.py 取数据库连接信息，避免把口令写死在这儿
read -r DB_USER DB_PASS DB_NAME DB_HOST DB_PORT < <(
    python3 - <<'PY'
import sys
sys.path.insert(0, '/www/wwwroot/qiu_web')
from config import HOSTNAME, PORT, USERNAME, PASSWORD, DATABASE
print(USERNAME, PASSWORD, DATABASE, HOSTNAME, PORT)
PY
)

echo "=== 数据库备份 ==="
OUT="$BK/db/qiu_web_$TS.sql.gz"
mysqldump -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" \
    --single-transaction --quick --default-character-set=utf8mb4 \
    "$DB_NAME" 2>/dev/null | gzip > "$OUT"

if gzip -t "$OUT" 2>/dev/null; then
    echo "  OK  $OUT  ($(du -h "$OUT" | cut -f1))"
else
    echo "  失败：压缩包不完整"
    exit 1
fi

# 清理过老的数据库备份
cd "$BK/db" || exit 1
ls -1t qiu_web_*.sql.gz 2>/dev/null | tail -n +$((KEEP_DB + 1)) | while read -r old; do
    rm -f "$old"
done
echo "  当前保留 $(ls -1 qiu_web_*.sql.gz 2>/dev/null | wc -l) 份（上限 $KEEP_DB）"

if [ "$FULL" = "1" ]; then
    echo
    echo "=== 站点代码打包 ==="
    PKG="$BK/site/qiu_web_$TS.tar.gz"
    tar -czf "$PKG" \
        --exclude='.git' \
        --exclude='recworksimg' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.remind_sent.log' \
        -C /www/wwwroot qiu_web 2>/dev/null
    echo "  OK  $PKG  ($(du -h "$PKG" | cut -f1))"

    cd "$BK/site" || exit 1
    ls -1t qiu_web_*.tar.gz 2>/dev/null | tail -n +11 | while read -r old; do
        rm -f "$old"
    done
    echo "  当前保留 $(ls -1 qiu_web_*.tar.gz 2>/dev/null | wc -l) 份（上限 10）"
fi

echo
echo "=== 备份目录 ==="
du -sh "$BK"/*
df -h / | tail -1
