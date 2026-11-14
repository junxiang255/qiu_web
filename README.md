# 小秋的垃圾站（qiu_web）

一个 Flask 单页站点：首页展示、手机版、垃圾桶之夜名单页，外加一个需要登录的管理后台。
数据走 MySQL（`ranking`、`user` 两张表），后台密码用 `werkzeug` 的哈希存储。

- 域名：`小秋的垃圾站.xyz`（**暂未启用**，服务器当前在跑机器人）
- 技术栈：Flask 3 + Flask-SQLAlchemy + Flask-Migrate + PyMySQL，部署在宝塔面板的 Python 项目里

---

## 目录结构

```
qiu_web/
├─ app.py                 # Flask 应用：页面路由 + 榜单接口 + 登录/后台
├─ config.py              # 本地配置（含密钥，不入库）
├─ config.example.py      # 配置模板，克隆后复制成 config.py
├─ requirements.txt       # Python 依赖
├─ index.html             # PC 首页（静态页面，含播放器、樱花特效）
├─ Phone_index.html       # 手机版首页
├─ ew.html                # 垃圾桶之夜名单页
├─ templates/             # 需要服务端渲染的页面
│  ├─ login.html
│  └─ manager.html        # 后台（榜单录入）
├─ static/
│  ├─ css/                # style / phone_style / player / font / ew
│  ├─ js/                 # drag / FE_but / player / song / top_name / top_qqid / no_cache / ranking
│  ├─ img/                # 背景图、favicon、榜单礼花、播放器图标、developer/ 成员头像
│  ├─ fonts/              # font.ttf（筑紫A圆体D）
│  └─ media/              # 将那花瓣扬起了.mp3 / .lrc / .jpg
├─ migrations/            # Flask-Migrate（Alembic）迁移脚本
├─ uwsgi.ini              # 线上启动配置（宝塔面板调用，勿改名/挪位置）
├─ gunicorn_conf.py       # 备选 Gunicorn 配置（同上，勿挪）
├─ .htaccess              # Apache 伪静态位（宝塔生成）
└─ _trash/                # 整理时清出的垃圾文件（不入库），确认无用后可整体删掉
```

> `index.html` / `Phone_index.html` / `ew.html` 是纯静态页面，直接由 Web 服务器或
> Flask 的 `send_from_directory` 返回；只有 `templates/` 里的两个页面走 Jinja2。

---

## 本地运行

```bash
git clone <repo>
cd qiu_web
cp config.example.py config.py      # 填入数据库账号/密码和 SECRET_KEY
pip install -r requirements.txt
flask --app app db upgrade          # 建表（数据库需先建好）
python app.py                       # 默认 http://127.0.0.1:5000
```

线上仍用原来的方式启动（uWSGI / Gunicorn 都通过 `app` 对象拉起），
`uwsgi.ini`、`gunicorn_conf.py` 里的路径保持原样即可。
仓库里不含 `config.py`，服务器上这份需要单独维护。

---

## 配置项

`config.py` 里所有值都能用环境变量覆盖，不设置时沿用原服务器上的取值：

| 环境变量 | 含义 | 缺省 |
| --- | --- | --- |
| `QIU_DB_HOST` | MySQL 地址 | `127.0.0.1` |
| `QIU_DB_PORT` | MySQL 端口 | `3306` |
| `QIU_DB_USER` | 数据库用户 | `qiu_web` |
| `QIU_DB_PASSWORD` | 数据库密码 | 见 config.py |
| `QIU_DB_NAME` | 数据库名 | `qiu_web` |
| `QIU_SECRET_KEY` | Flask session 密钥 | 见 config.py |
| `QIU_PORT` | 本地调试端口 | `5000` |

改线上密码时，直接设置环境变量即可，不用再动代码。

---

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/`、`/index.html` | PC 首页 |
| GET | `/background.png` | 兼容旧地址的背景图（实际指向 `static/img/background.png`） |
| GET | `/api/top_name` | 榜单前三昵称 |
| GET | `/api/top_qqid` | 榜单前三 QQ 号 |
| GET/POST | `/login` | 登录 |
| POST | `/logout` | 退出 |
| GET | `/manager` | 后台页面（需登录） |
| POST | `/manager/top_name` | 提交榜单 |

---

## 这次整理了哪些东西

1. **资源归位**：根目录散落的 5 个 css、8 个 js、图片、字体、音频全部收进
   `static/{css,js,img,fonts,media}`，按类型分目录。
2. **引用重写**：三个页面的 `src` / `href`、css 里的 `url(...)` 一并改成新路径，
   全部 60 处本地引用都做过存在性校验。
3. **接口地址改成站内相对路径**：`top_name.js`、`top_qqid.js` 原来写死
   `http://www.xn--rubbish-vk1r49unxc.xyz/api/...`，在 https 下会被浏览器拦成混合内容，
   现改为 `/api/top_name`、`/api/top_qqid`；模板里的背景图改用
   `url_for('static', ...)`。
4. **配置外置**：`app.py` 里写死的库账号、密码、session 密钥抽到 `config.py`，
   支持环境变量覆盖（取值不变，线上无需额外配置）。
5. **代码瘦身**：删掉 `from ast import Tuple`、`from re import U`、
   `from huggingface_hub import logout` 等无用/危险导入（`huggingface_hub` 根本没装，
   这行会让服务起不来），清掉调试 `print` 和空行堆积。
6. **补路由**：新增 `/`、`/index.html` 路由（原来根路径没有对应视图），
   `/background.png` 改用 `send_from_directory`，不再用裸 `open()`（工作目录变了就 500）。
7. **清垃圾**：`[91`、`[94`、`uWSGI`、`uwsgi.pid` 移入 `_trash/`，
   三处 `__pycache__` 删除，补 `.gitignore`。
8. **补文档**：新增 `README.md`、`requirements.txt`。

### 顺手修掉的 bug

- `index.html` 里 `location.href("./Phone_index.html")` 是在调用字符串，等于没跳转，
  改成赋值写法，手机访问现在会正常跳手机版。
- `ew.html` 里内联的一段 `$.ajax` 依赖 jQuery，但页面从没引过 jQuery，每次加载都报
  `$ is not defined`，且这段和 `no_cache.js` 重复，已删除。
- `index.html` 引用的 `yinghua.js` 文件不存在（樱花特效其实已内联在页面里），
  去掉这条死引用，浏览器不再 404。
- `ranking.js` 是空文件但 `ew.html` 在引它，补了注释占位，避免空响应被误判。

---

## 遗留待办（没动逻辑，只是记下来）

- `POST /manager/top_name` 每次提交都是 `insert` 新行，`/api/top_*` 又只取最后一行，
  数据会一直膨胀；建议改成 `update` 固定 id=1 的记录。
- 榜单接口用 `pymysql` 直连、后台用 SQLAlchemy，两套并存；可统一到 ORM。
- `static/img/background.png`（12MB）、`static/fonts/font.ttf`（11MB）、
  `static/media/*.mp3`（7.4MB）体积偏大，建议压成 webp/woff2 并开 gzip。
- `static/media/将那花瓣扬起了.lrc` 目前没被引用（歌词内联在 `song.js`），留作素材。
- 后台 `login.html` 的密码走明文表单，线上务必确认站点已上 HTTPS。
