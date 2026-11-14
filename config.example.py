# -*- coding: utf-8 -*-
"""站点配置模板。

用法：复制为 config.py 后填入真实值，config.py 不会提交到仓库。

    cp config.example.py config.py

所有值都可以用环境变量覆盖，环境变量优先。
"""
import os

# ---- 数据库 ----
HOSTNAME = os.environ.get("QIU_DB_HOST", "127.0.0.1")
PORT = int(os.environ.get("QIU_DB_PORT", "3306"))
USERNAME = os.environ.get("QIU_DB_USER", "qiu_web")
PASSWORD = os.environ.get("QIU_DB_PASSWORD", "CHANGE_ME")
DATABASE = os.environ.get("QIU_DB_NAME", "qiu_web")
CHARSET = "utf8mb4"

# pymysql 直连用（/api/top_name、/api/top_qqid）
DB_CONFIG = {
    "host": HOSTNAME,
    "user": USERNAME,
    "password": PASSWORD,
    "database": DATABASE,
    "ssl_disabled": True,
    "charset": CHARSET,
}

# SQLAlchemy / Flask-Migrate 用
SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}?charset={CHARSET}"
)

# ---- 会话密钥 ----
# 生成一个随机值：python -c "import secrets;print(secrets.token_urlsafe(32))"
SECRET_KEY = os.environ.get("QIU_SECRET_KEY", "CHANGE_ME")
