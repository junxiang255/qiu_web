# 小秋的垃圾站（qiu_web）

小秋の垃圾桶（群号 **707983601**）的群站：群推荐首页、本周榜单、作品推荐，外加一个需要登录的管理后台。

Flask 3 + MySQL，线上由 uWSGI 托管、nginx 反向代理；前端是原生 HTML / CSS / JS，没有构建步骤。

- 线上地址：<https://www.xn--rubbish-o27ow52hy3g.xyz>
- 加群链接：<https://qm.qq.com/q/YcYmHiZN2C>
- 技术栈：Flask 3 · Flask-SQLAlchemy · Flask-Migrate · PyMySQL · uWSGI · nginx

---

## 页面

| 文件 | 访问路径 | 说明 |
| --- | --- | --- |
| `index.html` | `/`、`/index.html` | 首页：群推荐 Hero、关于本群 / 展望未来、快捷入口、开发人员 |
| `ew.html` | `/ew.html` | 本周乐色王榜单页，拉 `/api/top_*` 渲染前三名 |
| `RecWorks.html` | `/RecWorks.html` | 作品推荐列表：搜索、置顶、右侧缩略图、展开看正文与大图 |
| `templates/login.html` | `/login` | 登录页（Jinja2 渲染） |
| `templates/manager.html` | `/manager` | 后台：榜单录入 + 作品推荐录入（含图片上传），需登录 |
| `templates/recworks_admin.html` | `/manager/recWorks` | 推荐管理：列表、筛选、勾选批量删除，需登录 |
| `templates/register.html` | `/register` | 注册（首个注册的账号自动成为管理员） |
| `templates/account.html` | `/account` | 个人设置：改昵称、改密码，需登录 |
| `templates/users.html` | `/manager/users` | 用户管理：角色、启用停用、重置密码、删除，需管理员 |

> `index.html`、`ew.html`、`RecWorks.html` 是纯静态页面，由 nginx 的 `try_files` 直接返回；
> 只有 `templates/` 下的两个页面走 Jinja2 服务端渲染。

三个访客页面共享同一条顶部栏：群头像（点开是加群）、群名、GitHub 链接、迷你播放器、「主页」。
顶栏样式与脚本目前是内联在各页 `<style>` / `<script>` 里的，改样式需要同步改三处。

---

## 目录结构

```
qiu_web/
├─ app.py                     # Flask 应用：页面路由、榜单接口、作品推荐、登录/后台、图片上传
├─ config.py                  # 本地配置，含数据库口令与 SECRET_KEY（不入库）
├─ config.example.py          # 配置模板，克隆后复制成 config.py
├─ requirements.txt           # Python 依赖
├─ index.html                 # 首页
├─ ew.html                    # 榜单页
├─ RecWorks.html              # 作品推荐页
├─ templates/
│  ├─ login.html
│  └─ manager.html            # 后台（榜单 + 作品推荐表单）
├─ static/
│  ├─ css/                    # style / phone_style / player / font / ew
│  ├─ js/                     # top_name / top_qqid / ranking / player / song / drag / FE_but
│  ├─ img/                    # 背景图、favicon、礼花、播放器图标、qun_avatar.jpg（群头像兜底）
│  │  └─ developer/           # 开发人员头像
│  ├─ fonts/                  # font.ttf（筑紫A圆体D）
│  ├─ media/                  # 将那花瓣扬起了.mp3 / .lrc / .jpg
│  └─ data/                   # 前端 JSON 快照，由 scripts/export_recworks.py 生成（不入库）
├─ recworksimg/               # 后台传入的作品配图（不入库）
├─ scripts/
│  └─ export_recworks.py      # 把 rec_Works 表导出成 static/data/recworks.json
├─ migrations/                # Flask-Migrate（Alembic）迁移脚本
├─ uwsgi.ini                  # 线上启动配置（宝塔面板调用，勿改名、勿挪位置）
├─ gunicorn_conf.py           # 备选 Gunicorn 配置（同上）
├─ .htaccess                  # Apache 伪静态位（宝塔生成）
└─ _trash/                    # 停用与清理出来的文件（不入库）
```

---

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/`、`/index.html` | 首页 |
| GET | `/background.png` | 兼容旧地址的背景图 |
| POST | `/api/top_name` | 榜单前三昵称（`pymysql` 直连） |
| GET | `/api/top_qqid` | 榜单前三 QQ 号（`pymysql` 直连） |
| GET / POST | `/login` | 登录 |
| POST | `/logout` | 退出 |
| GET | `/manager` | 后台页面，需登录 |
| POST | `/manager/top_name` | 提交榜单，需登录 |
| GET | `/manager/recWorks` | 推荐管理页：列出全部推荐，可勾选批量删除，需登录 |
| POST | `/manager/recWorks/delete` | 删除选中的推荐（连带 `recworksimg/` 里的图片并刷新 JSON），需登录 |
| POST | `/manager/recWorks` | 提交作品推荐（`multipart/form-data`，含图片），需登录 |
| GET / POST | `/register` | 注册，首个账号自动获得管理员权限 |
| GET / POST | `/account` | 个人设置：`action=profile` 改昵称、`action=password` 改密码，需登录 |
| GET | `/manager/users` | 用户列表，需管理员 |
| POST | `/manager/users/<id>/role` | 切换管理员 / 普通用户，需管理员 |
| POST | `/manager/users/<id>/toggle` | 启用 / 停用账号，需管理员 |
| POST | `/manager/users/<id>/reset` | 重置密码，需管理员 |
| POST | `/manager/users/<id>/delete` | 删除账号，需管理员 |

`/api/*`、`/login`、`/manager` 由 nginx 转发到 `127.0.0.1:5000`，其余路径走静态文件。

---

## 账号系统

`user` 表带 `username`（唯一）、`nickname`、`password_hash`、`role`、`is_active`、
`created_at`、`last_login`。密码用 `werkzeug` 的 `generate_password_hash`（scrypt）存储。

- **角色**：`admin` / `user`。注册时如果库里没有任何账号，第一个自动成为 `admin`；
  其余都是 `user`。
- **权限分层**：`@login_required` 挡未登录，`@admin_required` 在其上再挡一层，
  后台所有写接口（榜单、推荐、用户管理）都需要登录。
- **自我保护**：管理员不能改自己的角色、不能停用自己、不能删除自己；
  系统至少保留一个管理员。
- **注册开关**：环境变量 `QIU_ALLOW_REGISTER=0` 时 `/register` 直接返回 403，
  页面提示「本站目前关闭了公开注册」，适合只留自己用的情况。

### 注册白名单：必须是群成员

注册除了用户名密码，还必须填 **QQ 号**，且该 QQ 号得在 `group_member` 表里
（这张表存群主 / 管理员 / 成员的 QQ，由群成员列表同步而来）。不在名单里的 QQ 直接拒绝注册。

- 群主、群管理员的 QQ 注册后自动拿到 `admin`，普通成员是 `user`
- 一个 QQ 号只能绑定一个账号（`user.qq_id` 有唯一索引）
- 昵称留空时自动用群名片

同步群成员的两步：

```bash
# 1. 浏览器打开 https://qun.qq.com/member.html 登录，F12 复制 Cookie 整行
python scripts/fetch_group_members.py --cookie "uin=o0xxxx; skey=@xxxx; p_skey=xxxx" --group 707983601

# 2. 导入数据库（--prune 会顺带删掉已经退群的人）
python scripts/sync_group_members.py members.json --prune
```

`fetch_group_members.py` 走的是群管理网页的 `search_group_members` 接口，
需要 Cookie 里的 `skey` 来算 `bkn`；`sync_group_members.py` 只读 JSON，也可以手写名单导入。

## 作品推荐的图片链路

```
后台表单（multipart）
   └─ POST /manager/recWorks
        ├─ 去重：同一 (rw_qq_id, rw_work_name) 只允许一条（另有数据库唯一索引兜底）
        ├─ 校验：读前 64 字节做 magic 嗅探，只收 jpg / png / gif / webp
        ├─ 限流：单张最大 5MB（app.py 里 MAX_BYTES，前端同步校验）
        ├─ 落盘：recworksimg/<昵称>_<作品名>.<ext>，重名自动追加 _2、_3（O_EXCL 保证并发安全）
        └─ 入库：路径只存文件名，写进 rec_Works.rw_img_Path
                ↓
        scripts/export_recworks.py（cron 每 2 分钟跑一次）
                ↓
        static/data/recworks.json   →   RecWorks.html 用 fetch 拉取后渲染
                ↓
        nginx 按静态文件直接发 /recworksimg/xxx.jpg
```

之所以中间隔一层 JSON，是因为 `RecWorks.html` 是纯静态页（由 nginx `try_files` 直出），
不经过 Flask，拿不到服务端渲染的数据。

---

## 本地运行

```bash
git clone https://github.com/junxiang255/qiu_web.git
cd qiu_web
cp config.example.py config.py       # 填入数据库账号/密码与 SECRET_KEY
pip install -r requirements.txt
flask --app app db upgrade           # 建表（数据库需先建好）
python app.py                        # http://127.0.0.1:5000
```

作品推荐页在本地要手动跑一次导出脚本，否则 `static/data/recworks.json` 不存在：

```bash
python scripts/export_recworks.py
```

---

## 配置

`config.py` 里所有值都能用环境变量覆盖，环境变量优先：

| 环境变量 | 含义 | 缺省 |
| --- | --- | --- |
| `QIU_DB_HOST` | MySQL 地址 | `127.0.0.1` |
| `QIU_DB_PORT` | MySQL 端口 | `3306` |
| `QIU_DB_USER` | 数据库用户 | `qiu_web` |
| `QIU_DB_PASSWORD` | 数据库密码 | 见 `config.py` |
| `QIU_DB_NAME` | 数据库名 | `qiu_web` |
| `QIU_SECRET_KEY` | Flask session 密钥 | 见 `config.py` |
| `QIU_PORT` | 本地调试端口 | `5000` |
| `QIU_ALLOW_REGISTER` | 是否开放公开注册，`0` 关闭 | `1` |

`config.py` 不入库，部署时从 `config.example.py` 复制一份填写。

---

## 部署

线上是宝塔面板的「Python 项目」，用 `uwsgi.ini` 拉起（4 进程 × 2 线程，绑 `0.0.0.0:5000`，以 `www` 用户运行）。

```bash
# 重启
/www/server/pyporject_evn/versions/3.10.21/bin/uwsgi --stop /www/wwwroot/qiu_web/uwsgi.pid
rm -f /www/wwwroot/qiu_web/uwsgi.pid
/www/server/pyporject_evn/versions/3.10.21/bin/uwsgi --ini /www/wwwroot/qiu_web/uwsgi.ini
```

### 非静态路由必须在 nginx 里显式转发

站点主配置的 `location /` 是 `try_files $uri $uri/ /index.html?$args`，
这意味着**任何没有单独 `location` 的路径都会静默回落到首页（返回 200），而不是 404**。
所以每新增一个由 Flask 处理的路由，都要在 nginx 里补一条转发，否则访问到的会是首页。

目前线上放在 `/www/server/panel/vhost/nginx/extension/qiu_web/account.conf`，
靠站点主配置里的 `include .../extension/qiu_web/*.conf;` 生效，不会覆盖宝塔生成的配置：

```nginx
location /account {
    proxy_pass http://127.0.0.1:5000/account;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

同样的规则还需要给 `/register`、`/logout`。已有的 `/api/`、`/login`、`/manager`
（前缀匹配，`/manager/recWorks` 等子路径一并覆盖）写在站点主配置里。

改完记得 `nginx -t` 再 `nginx -s reload`。

数据库同步任务（每 2 分钟刷新一次前端 JSON）：

```cron
*/2 * * * * /www/server/pyporject_evn/versions/3.10.21/bin/python3 /www/wwwroot/qiu_web/scripts/export_recworks.py >> /www/wwwlogs/qiu_recworks_sync.log 2>&1
```

---

## 已知问题

- **`GET /api/top_name` 返回 405**。`app.py` 里注册的是 `methods=["POST"]`，但 `static/js/top_name.js`
  和 `no_cache.js` 都用 GET 请求，所以榜单页的三个昵称一直拉不出来。把该路由的 `methods` 去掉即可。
- **`/background.png` 返回 404**。nginx 里 `location /background.png` 的 `alias` 指向
  `/www/wwwroot/qiu_web/img/`，这个目录并不存在（图实际在 `static/img/`）。Flask 里那条同名路由是好的，
  被 nginx 抢先截胡了。`location /img/` 同样指向了不存在的目录。
- **`POST /manager/top_name` 每次都是 insert 新行**，而 `/api/top_*` 只读最后一行，`ranking` 表会持续膨胀。
  建议改成更新固定 `id=1` 的记录。
- **后台表单没有 CSRF 保护**，需要引入 `Flask-WTF` 或自行签发 token。
- 顶栏的 HTML / CSS / JS 在三个页面里各存一份，改样式要同步改三处；可抽成 `static/css/topbar.css`
  与 `static/js/topbar.js` 外链（各页只保留各自的「主页」链接差异）。
- `static/img/background.png`（12MB）、`static/fonts/font.ttf`（11MB）体积偏大，可考虑转 webp / woff2 并开 gzip。
