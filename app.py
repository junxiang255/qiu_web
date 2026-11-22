import os
import re
import uuid
from functools import wraps
from pathlib import Path

from flask import *
import pymysql
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import MetaData, Integer, String, UniqueConstraint
from sqlalchemy import Text, Boolean, DateTime, func
from datetime import datetime, timedelta
import random
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import MEDIUMTEXT

from config import DB_CONFIG, SECRET_KEY, SQLALCHEMY_DATABASE_URI
BASE_DIR   = Path("/www/wwwroot/qiu_web")      # 站点根目录
IMAGE_SUB  = "recworksimg"                     # 图片子目录名
UPLOAD_DIR = BASE_DIR / IMAGE_SUB              # 图片落盘位置
URL_PREFIX = "/" + IMAGE_SUB                   # 图片访问前缀,必须与子目录同名
app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)
app.secret_key = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_DIR = Path("/www/wwwroot/qiu_web/recworksimg")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
URL_PREFIX = "/recworksimg"

# 单张图片上限，与 manager.html 前端的 5MB 校验保持一致
MAX_BYTES = 5 * 1024 * 1024

_SAFE_RE = re.compile(r"[^\w-]+")


def build_business_stem(qq_name: str, work_name: str) -> str:
    """昵称 + 作品名 -> 人类可读的文件名主干，顺手去掉路径分隔符之类的危险字符。"""
    parts = []
    for raw in (qq_name, work_name):
        s = _SAFE_RE.sub("_", (raw or "").strip()).strip("_")[:40].strip("_")
        if s:
            parts.append(s)
    return "_".join(parts) or "recworks"


def unique_link(tmp: Path, upload_dir: Path, stem: str, ext: str) -> str:
    """把临时文件落成不重名的最终文件，返回文件名（不含目录）。"""
    n = 1
    while True:
        name = f"{stem}{ext}" if n == 1 else f"{stem}_{n}{ext}"
        target = Path(upload_dir) / name
        try:
            # O_CREAT|O_EXCL：并发同时上传同一个名字时，只有一个能建成
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            n += 1
            continue
        os.close(fd)
        os.replace(tmp, target)
        return name


_MAGIC: list[tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
]
def sniff_image(head: bytes) -> tuple[str, str] | None:
    """返回 (mime, ext);认不出返回 None。"""
    for sig, mime, ext in _MAGIC:
        if head.startswith(sig):
            return mime, ext
    # WebP: RIFF....WEBP
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None
class Bass (DeclarativeBase):
    metadata = MetaData(naming_convention={
        # ix = index，索引
        "ix": "ix_%(column_0_label)s",
        # uq = unique，唯一索引
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        # ck = check，检查约束
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        # fk = foreign key，外键约束
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        # pk = primary key，主键约束
        "pk": "pk_%(table_name)s"
    })


 
db = SQLAlchemy(app=app , model_class=Bass)
migrate = Migrate(app,db)

class Ranking(db.Model):
    __tablename__='ranking'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    top1_qqid:Mapped[str]=mapped_column(String(255),nullable=True)
    top1_name:Mapped[str]=mapped_column(String(255),nullable=True)
    top2_qqid:Mapped[str]=mapped_column(String(255),nullable=True)
    top2_name:Mapped[str]=mapped_column(String(255),nullable=True)
    top3_qqid:Mapped[str]=mapped_column(String(255),nullable=True)
    top3_name:Mapped[str]=mapped_column(String(255),nullable=True)

"""这个是作品推荐MySQL"""
class recWorks(db.Model):

    __tablename__='rec_Works'
    # (QQ号, 作品名) 唯一：同一个人的同一个作品只能推荐一次。
    # 应用层还会先查一遍给出友好提示，这条索引负责并发下的兜底。
    __table_args__ = (
        UniqueConstraint("rw_qq_id", "rw_work_name", name="uq_rec_Works_qq_work"),
    )
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    rw_qq_id:Mapped[str | None]=mapped_column("rw_qq_id",String(255),nullable=True)
    rw_qq_name:Mapped[str | None]=mapped_column("rw_qq_name",String(255),nullable=True)
    rw_work_name:Mapped[str| None]=mapped_column("rw_work_name",String(255),nullable=True)
    rw_recwork:Mapped[str] = mapped_column( "rw_recwork", Text().with_variant(MEDIUMTEXT, "mysql"), nullable=False) 
    rw_img_path:Mapped[str | None]=mapped_column("rw_img_Path",String(500),nullable=True)
    rw_tag:Mapped[str | None]=mapped_column("rw_tag",String(120),nullable=True)
    pinned:Mapped[bool]=mapped_column(Boolean,nullable=False,default=False,server_default="0")
 
    def __init__(self,qq_id: str | None = None, qq_name: str | None = None,
                 work_name: str | None = None, recwork: str = "",
                 img_path: str | None = None, tag: str | None = None):
        self.rw_qq_id = qq_id
        self.rw_qq_name = qq_name
        self.rw_work_name = work_name
        self.rw_recwork = recwork
        self.rw_img_path = img_path
        self.rw_tag = tag

    def __repr__(self) -> str:
        return f"<RecWorks id={self.id} qq={self.rw_qq_id}>"





def login_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if g.user:
            return func(*args, **kwargs)
        return redirect("/login")
    return inner


@app.route("/manager/recWorks", methods=["POST"])
@login_required
def recWorks_get():
    qq_id     = (request.form.get("rw_qq_id") or "").strip()
    qq_name   = (request.form.get("rw_qq_name") or "").strip()
    work_name = (request.form.get("rw_work_name") or "").strip()
    recwork   = (request.form.get("rw_recwork") or "").strip()
    tag       = normalize_tags(request.form.get("rw_tag"))

    # ---- 1. 去重前置 ----
    dup = db.session.query(recWorks.id).filter_by(
        rw_qq_id=qq_id, rw_work_name=work_name
    ).first()
    if dup is not None:
        flash("你已经推荐过这个作品了", "warning")
        return redirect(url_for("manager"))

    # ---- 2. 图片校验 ----
    f = request.files.get("rw_img_path")
    if f is None or not f.filename:
        flash("请选择图片", "error")
        return redirect(url_for("manager"))

    head = f.stream.read(64)
    f.stream.seek(0)
    sniffed = sniff_image(head)
    if sniffed is None:
        flash("不是有效的图片(仅支持 jpg/png/gif/webp)", "error")
        return redirect(url_for("manager"))

    mime, ext = sniffed

    # ---- 3. 大小 ----
    f.stream.seek(0, os.SEEK_END)
    size = f.stream.tell()
    f.stream.seek(0)
    if size <= 0:
        flash("图片是空文件", "error")
        return redirect(url_for("manager"))
    if size > MAX_BYTES:
        flash(f"图片不能超过 {MAX_BYTES // 1048576}MB", "error")
        return redirect(url_for("manager"))

    # ---- 4. 落盘 ----
    stem = build_business_stem(qq_name, work_name)
    tmp = UPLOAD_DIR / f".upload-{uuid.uuid4().hex}.part"
    try:
        f.save(tmp)
        name = unique_link(tmp, UPLOAD_DIR, stem, ext)
    except Exception:
        tmp.unlink(missing_ok=True)
        app.logger.exception("保存图片失败")
        flash("图片保存失败,请稍后重试", "error")
        return redirect(url_for("manager"))

    # ---- 5. 入库 ----
    row = recWorks(
        qq_id=qq_id,
        qq_name=qq_name,
        work_name=work_name,
        recwork=recwork,
        img_path=name,
        tag=tag,
    )
    try:
        db.session.add(row)
        db.session.commit()
        flash("推荐成功", "success")
    except IntegrityError:
        db.session.rollback()
        (UPLOAD_DIR / name).unlink(missing_ok=True)
        flash("你已经推荐过这个作品了", "warning")
    except Exception:
        db.session.rollback()
        (UPLOAD_DIR / name).unlink(missing_ok=True)
        app.logger.exception("插入 recWorks 失败")
        flash("保存失败,请稍后重试", "error")

    return redirect(url_for("manager"))


def sync_recworks_json():
    """删改之后立刻刷新一次前端 JSON。

    失败不影响主流程 —— cron 每 2 分钟还会兜一次。
    """
    try:
        import subprocess
        import sys
        script = os.path.join(str(BASE_DIR), "scripts", "export_recworks.py")
        subprocess.run([sys.executable, script], capture_output=True,
                       timeout=20, check=False)
    except Exception:
        app.logger.warning("刷新 recworks.json 失败", exc_info=True)


@app.route("/manager/recWorks", methods=["GET"])
@login_required
def recworks_admin():
    """推荐管理：列出全部推荐，可勾选批量删除。"""
    items = db.session.scalars(
        db.select(recWorks).order_by(recWorks.id.desc())
    ).all()
    return render_template("recworks_admin.html", items=items)


@app.post("/manager/recWorks/delete")
@login_required
def recworks_delete():
    ids = [int(x) for x in request.form.getlist("ids") if x.isdigit()]
    if not ids:
        flash("没有选中任何推荐", "warning")
        return redirect(url_for("recworks_admin"))

    rows = db.session.scalars(
        db.select(recWorks).where(recWorks.id.in_(ids))
    ).all()

    removed_img = 0
    for row in rows:
        if row.rw_img_path:
            target = UPLOAD_DIR / row.rw_img_path
            try:
                if target.exists():
                    target.unlink()
                    removed_img += 1
            except OSError:
                app.logger.warning("删除图片失败: %s", target)
        db.session.delete(row)
    db.session.commit()

    sync_recworks_json()
    flash("已删除 %d 条推荐（连带 %d 张图片）" % (len(rows), removed_img), "success")
    return redirect(url_for("recworks_admin"))


@app.route("/manager/recWorks/edit/<int:rid>", methods=["GET", "POST"])
@login_required
def recworks_edit(rid):
    """编辑单条推荐：昵称、作品名、正文，图片可选替换。"""
    row = db.session.get(recWorks, rid)
    if row is None:
        flash("这条推荐不存在，可能已被删除", "warning")
        return redirect(url_for("recworks_admin"))

    if request.method == "GET":
        return render_template("recworks_edit.html", item=row)

    qq_id = (request.form.get("rw_qq_id") or "").strip()
    qq_name = (request.form.get("rw_qq_name") or "").strip()
    work_name = (request.form.get("rw_work_name") or "").strip()
    recwork = (request.form.get("rw_recwork") or "").strip()
    tag = normalize_tags(request.form.get("rw_tag"))

    if not (qq_id and qq_name and work_name and recwork):
        flash("QQ 号、昵称、作品标题、推荐内容都不能为空", "error")
        return redirect(url_for("recworks_edit", rid=rid))
    if not qq_id.isdigit():
        flash("QQ 号只能是数字", "error")
        return redirect(url_for("recworks_edit", rid=rid))

    # ---- 可选替换图片 ----
    new_name = None
    f = request.files.get("rw_img_path")
    if f is not None and f.filename:
        head = f.stream.read(64)
        f.stream.seek(0)
        sniffed = sniff_image(head)
        if sniffed is None:
            flash("不是有效的图片(仅支持 jpg/png/gif/webp)", "error")
            return redirect(url_for("recworks_edit", rid=rid))
        mime, ext = sniffed

        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size <= 0:
            flash("图片是空文件", "error")
            return redirect(url_for("recworks_edit", rid=rid))
        if size > MAX_BYTES:
            flash("图片不能超过 %dMB" % (MAX_BYTES // 1048576), "error")
            return redirect(url_for("recworks_edit", rid=rid))

        stem = build_business_stem(qq_name, work_name)
        tmp = UPLOAD_DIR / (".upload-%s.part" % uuid.uuid4().hex)
        try:
            f.save(tmp)
            new_name = unique_link(tmp, UPLOAD_DIR, stem, ext)
        except Exception:
            tmp.unlink(missing_ok=True)
            app.logger.exception("保存图片失败")
            flash("图片保存失败,请稍后重试", "error")
            return redirect(url_for("recworks_edit", rid=rid))

    old_name = row.rw_img_path
    row.rw_qq_id = qq_id
    row.rw_qq_name = qq_name
    row.rw_work_name = work_name
    row.rw_recwork = recwork
    row.rw_tag = tag
    if new_name:
        row.rw_img_path = new_name

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if new_name:
            (UPLOAD_DIR / new_name).unlink(missing_ok=True)
        flash("已经有相同的（QQ 号 + 作品名）推荐了", "warning")
        return redirect(url_for("recworks_edit", rid=rid))
    except Exception:
        db.session.rollback()
        if new_name:
            (UPLOAD_DIR / new_name).unlink(missing_ok=True)
        app.logger.exception("更新 recWorks 失败")
        flash("保存失败,请稍后重试", "error")
        return redirect(url_for("recworks_edit", rid=rid))

    # 换了图就把旧的清掉，不留孤儿文件
    if new_name and old_name and old_name != new_name:
        try:
            (UPLOAD_DIR / old_name).unlink(missing_ok=True)
        except OSError:
            app.logger.warning("删除旧图片失败: %s", old_name)

    sync_recworks_json()
    flash("已保存修改", "success")
    return redirect(url_for("recworks_admin"))


@app.post("/manager/recWorks/<int:rid>/pin")
@login_required
def recworks_pin(rid):
    """置顶 / 取消置顶。"""
    row = db.session.get(recWorks, rid)
    if row is None:
        return jsonify(ok=False, msg="这条推荐不存在"), 404

    row.pinned = not bool(row.pinned)
    db.session.commit()
    sync_recworks_json()

    return jsonify(ok=True, pinned=bool(row.pinned))


# 网站开发者：这些 QQ 在后台会被额外标一个「开发者」标签
DEVELOPER_QQS = {"2847407092"}

# ---- 邮件（注册验证码发到 <QQ号>@qq.com） ----
SMTP_HOST = os.environ.get("QIU_SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("QIU_SMTP_PORT", "465"))
SMTP_USER = os.environ.get("QIU_SMTP_USER", "")
SMTP_PASS = os.environ.get("QIU_SMTP_PASS", "")
MAIL_FROM_NAME = os.environ.get("QIU_MAIL_FROM_NAME", "小秋的垃圾站")
MAIL_ENABLED = bool(SMTP_USER and SMTP_PASS)
CODE_TTL_MINUTES = 10
CODE_COOLDOWN_SECONDS = 60


def send_mail(to_addr, subject, body):
    """发一封纯文本邮件，返回 (是否成功, 错误信息)。"""
    if not MAIL_ENABLED:
        return False, "邮件服务未配置"
    import smtplib
    from email.message import EmailMessage
    from email.utils import formataddr

    msg = EmailMessage()
    msg["From"] = formataddr((MAIL_FROM_NAME, SMTP_USER))
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True, ""
    except Exception as exc:
        app.logger.warning("发送邮件到 %s 失败: %s", to_addr, exc)
        return False, str(exc)


class EmailCode(db.Model):
    """注册邮箱验证码：发给 <QQ号>@qq.com，用来证明这个 QQ 号是他的。"""
    __tablename__ = 'email_code'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    qq_id:Mapped[str]=mapped_column(String(20),nullable=False,index=True)
    email:Mapped[str]=mapped_column(String(120),nullable=False)
    code:Mapped[str]=mapped_column(String(10),nullable=False)
    status:Mapped[str]=mapped_column(String(20),nullable=False,default="pending")
    tries:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    expires_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    created_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True,default=datetime.now)

    def __repr__(self) -> str:
        return f"<EmailCode {self.qq_id} {self.status}>"


class GroupMember(db.Model):
    """群成员白名单：只有在这里面的 QQ 号才能注册。

    由 scripts/sync_group_members.py 从群成员列表同步进来。
    role 取腾讯的群身份：owner（群主）/ admin（管理员）/ member（成员）。
    """
    __tablename__ = 'group_member'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    qq_id:Mapped[str]=mapped_column(String(20),unique=True,nullable=False)
    nickname:Mapped[str|None]=mapped_column(String(100),nullable=True)
    role:Mapped[str]=mapped_column(String(20),nullable=False,default="member")
    card:Mapped[str|None]=mapped_column(String(100),nullable=True)
    synced_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    created_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True,default=datetime.now)

    def __repr__(self) -> str:
        return f"<GroupMember {self.qq_id} {self.role}>"

    @property
    def role_label(self):
        return {"owner": "群主", "admin": "管理员", "member": "成员"}.get(self.role, self.role)

    @property
    def is_developer(self):
        return self.qq_id in DEVELOPER_QQS


class WorkLike(db.Model):
    """作品点赞（已停用，前端入口已移除；表先留着，需要时可恢复）。"""
    __tablename__ = 'work_like'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    work_id:Mapped[int]=mapped_column(Integer,nullable=False,index=True)
    ip:Mapped[str]=mapped_column(String(64),nullable=False)
    user_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
    created_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True,default=datetime.now)

    __table_args__ = (
        UniqueConstraint("work_id", "ip", name="uq_work_like_work_ip"),
    )


class WorkComment(db.Model):
    """作品评论：要登录才能发。"""
    __tablename__ = 'work_comment'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    work_id:Mapped[int]=mapped_column(Integer,nullable=False,index=True)
    user_id:Mapped[int|None]=mapped_column(Integer,nullable=True)
    nickname:Mapped[str|None]=mapped_column(String(50),nullable=True)
    qq_id:Mapped[str|None]=mapped_column(String(20),nullable=True)
    content:Mapped[str]=mapped_column(Text,nullable=False)
    status:Mapped[str]=mapped_column(String(20),nullable=False,default="visible")
    created_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True,default=datetime.now)

    def __repr__(self) -> str:
        return f"<WorkComment {self.id} work={self.work_id}>"


class ChatMessage(db.Model):
    """群友聊天室的消息。"""
    __tablename__ = 'chat_message'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id:Mapped[int|None]=mapped_column(Integer,nullable=True,index=True)
    nickname:Mapped[str|None]=mapped_column(String(50),nullable=True)
    qq_id:Mapped[str|None]=mapped_column(String(20),nullable=True)
    content:Mapped[str]=mapped_column(Text,nullable=False)
    status:Mapped[str]=mapped_column(String(20),nullable=False,default="visible")
    created_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True,default=datetime.now,index=True)

    def __repr__(self) -> str:
        return f"<ChatMessage {self.id} user={self.user_id}>"


class GuestbookEntry(db.Model):
    """留言板的一条留言，管理员可以回复。"""
    __tablename__ = 'guestbook_entry'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id:Mapped[int|None]=mapped_column(Integer,nullable=True,index=True)
    nickname:Mapped[str|None]=mapped_column(String(50),nullable=True)
    qq_id:Mapped[str|None]=mapped_column(String(20),nullable=True)
    content:Mapped[str]=mapped_column(Text,nullable=False)
    reply:Mapped[str|None]=mapped_column(Text,nullable=True)
    reply_by:Mapped[str|None]=mapped_column(String(50),nullable=True)
    replied_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    status:Mapped[str]=mapped_column(String(20),nullable=False,default="visible")
    created_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True,default=datetime.now,index=True)

    def __repr__(self) -> str:
        return f"<GuestbookEntry {self.id} user={self.user_id}>"


class User(db.Model):
    __tablename__='user'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    username:Mapped[str]=mapped_column(String(50),unique=True,nullable=False)
    qq_id:Mapped[str|None]=mapped_column(String(20),unique=True,nullable=True)
    nickname:Mapped[str|None]=mapped_column(String(50),nullable=True)
    password_hash:Mapped[str]=mapped_column(String(200),nullable=False)
    role:Mapped[str]=mapped_column(String(20),nullable=False,default="user")
    status:Mapped[str]=mapped_column(String(20),nullable=False,default="active")
    is_active:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True,default=datetime.now)
    last_login:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

    def __init__(self,*args,**kwargs):
        password = kwargs.pop("password", None)
        super().__init__(*args,**kwargs)
        if password:
            self.password=password

    @property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self,raw_password):
        self.password_hash=generate_password_hash(raw_password)

    def check_password(self,raw_password):
        return check_password_hash(self.password_hash,raw_password)

    @property
    def display_name(self):
        return self.nickname or self.username

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_developer(self):
        return self.qq_id in DEVELOPER_QQS

    @property
    def is_pending(self):
        return self.status == "pending"


def admin_required(func):
    """在 login_required 之上再加一层管理员校验。"""
    @wraps(func)
    def inner(*args,**kwargs):
        if not g.user:
            return redirect(url_for("login"))
        if not g.user.is_admin:
            flash("这个操作需要管理员权限", "error")
            return redirect(url_for("home"))
        return func(*args,**kwargs)
    return inner


# 注册是否开放（环境变量 QIU_ALLOW_REGISTER=0 可关闭）
REGISTER_OPEN = os.environ.get("QIU_ALLOW_REGISTER", "1") != "0"


@app.post("/api/register/send-code")
def send_register_code():
    """给 <QQ号>@qq.com 发验证码，用来证明这个 QQ 号确实是本人的。"""
    qq_id = (request.form.get("qq_id") or request.json and request.json.get("qq_id") or "").strip()
    if not re.fullmatch(r"[1-9]\d{4,11}", qq_id):
        return jsonify(ok=False, msg="QQ 号格式不对")

    member = db.session.scalar(
        db.select(GroupMember).where(GroupMember.qq_id == qq_id)
    )
    if member is None:
        return jsonify(ok=False, msg="QQ %s 不在群里，不能注册" % qq_id)

    dup = db.session.scalar(db.select(User).where(User.qq_id == qq_id))
    if dup is not None:
        return jsonify(ok=False, msg="QQ %s 已经注册过账号了" % qq_id)

    # 冷却：同一 QQ 60 秒内只能发一次
    last = db.session.scalar(
        db.select(EmailCode).where(EmailCode.qq_id == qq_id)
        .order_by(EmailCode.id.desc())
    )
    if last is not None and last.created_at is not None:
        gap = (datetime.now() - last.created_at).total_seconds()
        if gap < CODE_COOLDOWN_SECONDS:
            return jsonify(ok=False, msg="发得太快了，请 %d 秒后再试" % int(CODE_COOLDOWN_SECONDS - gap))

    code = "%06d" % random.randint(0, 999999)
    email = qq_id + "@qq.com"
    row = EmailCode(qq_id=qq_id, email=email, code=code, status="pending",
                    expires_at=datetime.now() + timedelta(minutes=CODE_TTL_MINUTES))
    db.session.add(row)
    db.session.commit()

    if not MAIL_ENABLED:
        app.logger.warning("[MAIL-OFF] %s 的验证码是 %s", qq_id, code)
        return jsonify(ok=False, msg="邮件服务还没配置，请联系管理员")

    ok, err = send_mail(
        email,
        "【小秋的垃圾站】注册验证码",
        "你的注册验证码是：%s\n\n%d 分钟内有效，如果这不是你本人操作，请忽略这封邮件。"
        % (code, CODE_TTL_MINUTES),
    )
    if not ok:
        row.status = "failed"
        db.session.commit()
        return jsonify(ok=False, msg="验证码发送失败，请稍后再试")

    app.logger.info("已向 %s 发送注册验证码", email)
    return jsonify(ok=True, msg="验证码已发到 %s，10 分钟内有效" % email)


@app.route("/register", methods=["GET","POST"])
def register():
    if not REGISTER_OPEN:
        return render_template("register.html", closed=True), 403
    if g.user:
        return redirect(url_for("manager"))

    if request.method == "GET":
        return render_template("register.html", closed=False)

    username = (request.form.get("username") or "").strip()
    qq_id = (request.form.get("qq_id") or "").strip()
    nickname = (request.form.get("nickname") or "").strip()
    password = request.form.get("password") or ""
    password2 = request.form.get("password2") or ""

    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        flash("用户名只能是 3-20 位字母、数字或下划线", "error")
        return redirect(url_for("register"))
    if not re.fullmatch(r"[1-9]\d{4,11}", qq_id):
        flash("请填写正确的 QQ 号", "error")
        return redirect(url_for("register"))
    if len(password) < 6:
        flash("密码至少 6 位", "error")
        return redirect(url_for("register"))
    if password != password2:
        flash("两次输入的密码不一致", "error")
        return redirect(url_for("register"))

    # ---- 邮箱验证码：证明这个 QQ 号是本人的 ----
    verified_code = None
    if MAIL_ENABLED:
        email_code = (request.form.get("email_code") or "").strip()
        if not email_code:
            flash("请先填邮箱验证码（QQ 号对应的 QQ 邮箱会收到）", "error")
            return redirect(url_for("register"))

        verified_code = db.session.scalar(
            db.select(EmailCode).where(
                EmailCode.qq_id == qq_id,
                EmailCode.code == email_code,
                EmailCode.status == "pending",
            ).order_by(EmailCode.id.desc())
        )
        if verified_code is None:
            flash("验证码不对，请重新获取", "error")
            return redirect(url_for("register"))
        if verified_code.expires_at and verified_code.expires_at < datetime.now():
            flash("验证码已过期，请重新获取", "error")
            return redirect(url_for("register"))
        verified_code.status = "verified"

    # ---- 群成员白名单：在名单里直接通过，不在名单的先挂起等管理员审核 ----
    member = db.session.scalar(
        db.select(GroupMember).where(GroupMember.qq_id == qq_id)
    )

    dup_user = db.session.scalar(db.select(User).where(User.username == username))
    if dup_user:
        flash("这个用户名已经被注册了", "error")
        return redirect(url_for("register"))

    dup_qq = db.session.scalar(db.select(User).where(User.qq_id == qq_id))
    if dup_qq:
        if dup_qq.is_pending:
            flash("QQ %s 已经提交过申请了，正在等管理员审核" % qq_id, "warning")
        else:
            flash("QQ %s 已经注册过账号了" % qq_id, "error")
        return redirect(url_for("register"))

    total = db.session.scalar(db.select(func.count()).select_from(User)) or 0

    if member is not None:
        status = "active"
        role = "admin" if total == 0 else ("admin" if member.role in ("owner", "admin") else "user")
        nick = nickname or (member.card or member.nickname) or None
    else:
        # 不在白名单：先建一个待审核账号，管理员在后台点通过后才会生效
        status = "pending"
        role = "admin" if total == 0 else "user"
        nick = nickname or None

    u = User(username=username, nickname=nick, qq_id=qq_id, role=role, status=status)
    u.password = password

    try:
        db.session.add(u)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("用户名或 QQ 号已被占用", "error")
        return redirect(url_for("register"))

    if status == "pending":
        flash("已提交注册申请，等管理员审核通过后就能登录了", "success")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = u.id
    flash("注册成功，欢迎 %s" % u.display_name, "success")
    if u.is_admin:
        return redirect(url_for("manager"))
    return redirect(url_for("home"))


@app.route("/account", methods=["GET","POST"])
@login_required
def account():
    if request.method == "GET":
        return render_template("account.html")

    action = request.form.get("action")

    if action == "profile":
        nickname = (request.form.get("nickname") or "").strip()
        if len(nickname) > 50:
            flash("昵称最多 50 个字", "error")
            return redirect(url_for("account"))
        g.user.nickname = nickname or None
        db.session.commit()
        flash("昵称已更新", "success")
        return redirect(url_for("account"))

    if action == "password":
        old = request.form.get("old_password") or ""
        new = request.form.get("new_password") or ""
        new2 = request.form.get("new_password2") or ""
        if not g.user.check_password(old):
            flash("原密码不对", "error")
            return redirect(url_for("account"))
        if len(new) < 6:
            flash("新密码至少 6 位", "error")
            return redirect(url_for("account"))
        if new != new2:
            flash("两次输入的新密码不一致", "error")
            return redirect(url_for("account"))
        g.user.password = new
        db.session.commit()
        flash("密码已修改", "success")
        return redirect(url_for("account"))

    flash("无效的请求", "error")
    return redirect(url_for("account"))


@app.route("/manager/users")
@admin_required
def users_admin():
    items = db.session.scalars(
        db.select(User).order_by(User.status.desc(), User.id)
    ).all()
    pending = [u for u in items if u.is_pending]
    active = [u for u in items if not u.is_pending]
    return render_template("users.html", items=items, pending=pending, active=active)


@app.post("/manager/users/<int:uid>/role")
@admin_required
def users_role(uid):
    u = db.session.get(User, uid)
    if u is None:
        flash("用户不存在", "warning")
        return redirect(url_for("users_admin"))
    if u.id == g.user.id:
        flash("不能修改自己的角色", "warning")
        return redirect(url_for("users_admin"))
    u.role = "user" if u.is_admin else "admin"
    db.session.commit()
    flash("%s 现在是%s" % (u.display_name, "管理员" if u.is_admin else "普通用户"), "success")
    return redirect(url_for("users_admin"))


@app.post("/manager/users/<int:uid>/toggle")
@admin_required
def users_toggle(uid):
    u = db.session.get(User, uid)
    if u is None:
        flash("用户不存在", "warning")
        return redirect(url_for("users_admin"))
    if u.id == g.user.id:
        flash("不能停用自己的账号", "warning")
        return redirect(url_for("users_admin"))
    u.is_active = not u.is_active
    db.session.commit()
    flash("%s 已%s" % (u.display_name, "启用" if u.is_active else "停用"), "success")
    return redirect(url_for("users_admin"))


@app.post("/manager/users/<int:uid>/reset")
@admin_required
def users_reset(uid):
    u = db.session.get(User, uid)
    if u is None:
        flash("用户不存在", "warning")
        return redirect(url_for("users_admin"))
    new = request.form.get("new_password") or ""
    if len(new) < 6:
        flash("新密码至少 6 位", "error")
        return redirect(url_for("users_admin"))
    u.password = new
    db.session.commit()
    flash("已重置 %s 的密码" % u.display_name, "success")
    return redirect(url_for("users_admin"))


@app.post("/manager/users/<int:uid>/delete")
@admin_required
def users_delete(uid):
    u = db.session.get(User, uid)
    if u is None:
        flash("用户不存在", "warning")
        return redirect(url_for("users_admin"))
    if u.id == g.user.id:
        flash("不能删除自己的账号", "warning")
        return redirect(url_for("users_admin"))

    other_admins = db.session.scalar(
        db.select(func.count()).select_from(User)
        .where(User.role == "admin", User.id != uid)
    ) or 0
    if u.is_admin and other_admins == 0:
        flash("至少要保留一个管理员", "warning")
        return redirect(url_for("users_admin"))

    name = u.username
    db.session.delete(u)
    db.session.commit()
    flash("已删除账号 %s" % name, "success")
    return redirect(url_for("users_admin"))


@app.post("/manager/users/<int:uid>/approve")
@admin_required
def users_approve(uid):
    """通过注册申请：同时写进群成员白名单，之后同 QQ 注册直接放行。"""
    u = db.session.get(User, uid)
    if u is None:
        flash("用户不存在", "warning")
        return redirect(url_for("users_admin"))
    if not u.is_pending:
        flash("这个账号已经审核过了", "warning")
        return redirect(url_for("users_admin"))

    role = request.form.get("role") or "member"
    if role not in ("owner", "admin", "member"):
        role = "member"

    if u.qq_id:
        m = db.session.scalar(
            db.select(GroupMember).where(GroupMember.qq_id == u.qq_id)
        )
        if m is None:
            db.session.add(GroupMember(
                qq_id=u.qq_id, nickname=u.nickname, role=role,
                synced_at=datetime.now()))
        else:
            m.role = role
            m.synced_at = datetime.now()

    u.status = "active"
    u.role = "admin" if role in ("owner", "admin") else "user"
    db.session.commit()

    label = {"owner": "群主", "admin": "管理员", "member": "成员"}[role]
    flash("已通过 %s 的申请，身份记为%s" % (u.display_name, label), "success")
    return redirect(url_for("users_admin"))


@app.post("/manager/users/<int:uid>/reject")
@admin_required
def users_reject(uid):
    u = db.session.get(User, uid)
    if u is None:
        flash("用户不存在", "warning")
        return redirect(url_for("users_admin"))
    if not u.is_pending:
        flash("只能拒绝待审核的申请", "warning")
        return redirect(url_for("users_admin"))
    name = u.username
    db.session.delete(u)
    db.session.commit()
    flash("已拒绝并删除 %s 的申请" % name, "success")
    return redirect(url_for("users_admin"))







# 获取登录的user_id
@app.before_request
def before_request():
    user_id = session.get('user_id')
    if user_id:
        user=db.session.get(User,user_id)
        g.user=user
    else:
        g.user = None


@app.context_processor
def context_processor():
    return{
        'user':g.user

    }





@app.route("/api/top_name",methods=["POST"])
def get_top_name():
    conn = None
    cursor = None
    
    
    top1_name=""
    top2_name=""
    top3_name=""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT top1_name,top2_name,top3_name FROM ranking")
        results = cursor.fetchall()
        for row in results:
            top1_name=row[0]
            top2_name=row[1]
            top3_name=row[2]
        return dict(top1_name=top1_name,top2_name=top2_name,top3_name=top3_name)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route("/api/top_qqid")
def get_top_qqid():
    conn = None
    cursor = None
    
    top1_qqid=""
    top2_qqid=""
    top3_qqid=""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT top1_qqid,top2_qqid,top3_qqid FROM ranking")
        results = cursor.fetchall()
        
        for row in results:
            top1_qqid=row[0]
            top2_qqid=row[1]
            top3_qqid=row[2]
            
        return dict(top1_qqid=top1_qqid,top2_qqid=top2_qqid,top3_qqid=top3_qqid)
    finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


def humanize_time(dt):
    """把时间变成「刚刚 / 8 分钟前 / 3 小时前 / 2 天前」这种。"""
    if not dt:
        return ""
    delta = datetime.now() - dt
    sec = delta.total_seconds()
    if sec < 60:
        return "刚刚"
    if sec < 3600:
        return "%d 分钟前" % int(sec // 60)
    if sec < 86400:
        return "%d 小时前" % int(sec // 3600)
    if sec < 86400 * 7:
        return "%d 天前" % int(sec // 86400)
    return dt.strftime("%Y-%m-%d")


@app.template_filter("humanize")
def _humanize_filter(dt):
    return humanize_time(dt)


def normalize_tags(raw: str | None) -> str:
    """把「妹系,治愈 战斗」统一成「妹系 治愈 战斗」，最多保留 6 个。"""
    parts = [p.strip() for p in re.split(r"[\s,，、/|／｜]+", raw or "") if p.strip()]
    seen = []
    for p in parts:
        if p not in seen:
            seen.append(p)
    return " ".join(seen[:6])[:120]


def client_ip():
    """nginx 反代后 remote_addr 是 127.0.0.1，真实 IP 在 X-Real-IP 里。"""
    return (request.headers.get("X-Real-IP") or request.remote_addr or "").strip()


@app.route("/works/<int:rid>")
def work_detail(rid):
    """作品详情页：正文、配图、评论。"""
    item = db.session.get(recWorks, rid)
    if item is None:
        abort(404)


    comments = db.session.scalars(
        db.select(WorkComment)
        .where(WorkComment.work_id == rid, WorkComment.status == "visible")
        .order_by(WorkComment.id.desc())
    ).all()


    # 推荐人的入站状态
    qq = (item.rw_qq_id or "").strip()
    if qq in ("", "9999999", "99999999"):
        author_state, author_label = "anon", "匿名"
    else:
        au = db.session.scalar(db.select(User).where(User.qq_id == qq))
        if au is None:
            author_state, author_label = "absent", "未入站"
        elif qq in DEVELOPER_QQS:
            author_state, author_label = "dev", "开发者"
        else:
            gm = db.session.scalar(
                db.select(GroupMember).where(GroupMember.qq_id == qq)
            )
            if gm is not None and gm.role == "owner":
                author_state, author_label = "owner", "群主"
            elif au.role == "admin":
                author_state, author_label = "admin", "管理员"
            else:
                author_state, author_label = "member", "成员"

    return render_template("works_detail.html", item=item,
                           comments=comments,
                           author_state=author_state, author_label=author_label)


@app.post("/api/works/<int:rid>/comment")
def work_add_comment(rid):
    """发评论，必须登录。"""
    if not g.user:
        return jsonify(ok=False, msg="请先登录再评论"), 401

    item = db.session.get(recWorks, rid)
    if item is None:
        return jsonify(ok=False, msg="作品不存在"), 404

    content = (request.form.get("content") or "").strip()
    if not content:
        return jsonify(ok=False, msg="评论不能为空")
    if len(content) > 1000:
        return jsonify(ok=False, msg="评论最多 1000 字")

    row = WorkComment(work_id=rid, user_id=g.user.id, nickname=g.user.display_name,
                      qq_id=g.user.qq_id, content=content)
    db.session.add(row)
    db.session.commit()

    return jsonify(ok=True, comment={
        "id": row.id,
        "nickname": row.nickname,
        "qq_id": row.qq_id or "",
        "content": row.content,
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M"),
        "when": humanize_time(row.created_at),
    })


@app.post("/api/comments/<int:cid>/delete")
def delete_comment(cid):
    """删评论：自己的能删，管理员能删所有。"""
    if not g.user:
        return jsonify(ok=False, msg="请先登录"), 401

    row = db.session.get(WorkComment, cid)
    if row is None:
        return jsonify(ok=False, msg="评论不存在，可能已经被删了"), 404

    if row.user_id != g.user.id and not g.user.is_admin:
        return jsonify(ok=False, msg="只能删除自己的评论"), 403

    db.session.delete(row)
    db.session.commit()
    return jsonify(ok=True)


@app.route("/api/users/list")
def api_users_list():
    """给首页的「群友」区块用：列出已激活的账号（不暴露 QQ 号）。"""
    rows = db.session.scalars(
        db.select(User).where(User.status == "active", User.is_active == True)
    ).all()

    # 群主身份只在 group_member 里有
    owners = set()
    for qq_id, role in db.session.execute(
        db.select(GroupMember.qq_id, GroupMember.role)
    ).all():
        if role == "owner":
            owners.add(qq_id)

    rows = sorted(rows, key=lambda u: (
        0 if u.is_developer else 1,
        0 if (u.qq_id in owners) else 1,
        0 if u.is_admin else 1,
        u.id,
    ))

    users = []
    for u in rows:
        is_owner = (u.qq_id in owners)
        if u.is_developer:
            role_label = "开发者"
        elif is_owner:
            role_label = "群主"
        elif u.is_admin:
            role_label = "管理员"
        else:
            role_label = "成员"

        users.append({
            "id": u.id,
            "nickname": u.display_name,
            "qq_id": u.qq_id or "",
            "role": u.role,
            "role_label": role_label,
            "is_owner": is_owner,
            "is_developer": u.is_developer,
            "joined": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
        })
    return jsonify(count=len(users), users=users)


@app.route("/chat")
def chat_page():
    """群友聊天室。"""
    return render_template("chat.html")


def _chat_payload(row):
    return {
        "id": row.id,
        "user_id": row.user_id,
        "nickname": row.nickname or "匿名",
        "qq_id": row.qq_id or "",
        "content": row.content,
        "created_at": row.created_at.strftime("%H:%M") if row.created_at else "",
        "when": humanize_time(row.created_at),
    }


@app.get("/api/chat/messages")
def chat_messages():
    """拉消息，after 传上次拿到的最大 id 就只返回新的。"""
    after = request.args.get("after", type=int) or 0

    stmt = db.select(ChatMessage).where(ChatMessage.status == "visible")
    if after:
        stmt = stmt.where(ChatMessage.id > after)
    else:
        # 首屏只给最近 60 条
        stmt = stmt.order_by(ChatMessage.id.desc()).limit(60)
        rows = db.session.scalars(stmt).all()
        rows.reverse()
        return jsonify(ok=True, messages=[_chat_payload(r) for r in rows],
                       me=(g.user.id if g.user else None))

    rows = db.session.scalars(stmt.order_by(ChatMessage.id).limit(200)).all()
    return jsonify(ok=True, messages=[_chat_payload(r) for r in rows],
                   me=(g.user.id if g.user else None))


@app.post("/api/chat/send")
def chat_send():
    if not g.user:
        return jsonify(ok=False, msg="请先登录再发言"), 401

    content = (request.form.get("content") or "").strip()
    if not content:
        return jsonify(ok=False, msg="说点什么吧")
    if len(content) > 500:
        return jsonify(ok=False, msg="一条最多 500 字")

    # 防刷：同一个人 3 秒内只能发一条
    last = db.session.scalar(
        db.select(ChatMessage)
        .where(ChatMessage.user_id == g.user.id)
        .order_by(ChatMessage.id.desc())
    )
    if last is not None and last.created_at is not None:
        gap = (datetime.now() - last.created_at).total_seconds()
        if gap < 3:
            return jsonify(ok=False, msg="发得有点快，等 %d 秒再发" % max(1, int(3 - gap)))

    row = ChatMessage(user_id=g.user.id, nickname=g.user.display_name,
                      qq_id=g.user.qq_id, content=content)
    db.session.add(row)
    db.session.commit()

    return jsonify(ok=True, message=_chat_payload(row))


@app.post("/api/chat/<int:cid>/delete")
def chat_delete(cid):
    """删自己发的消息，管理员能删所有。"""
    if not g.user:
        return jsonify(ok=False, msg="请先登录"), 401

    row = db.session.get(ChatMessage, cid)
    if row is None:
        return jsonify(ok=False, msg="消息不存在"), 404

    if row.user_id != g.user.id and not g.user.is_admin:
        return jsonify(ok=False, msg="只能删自己的消息"), 403

    db.session.delete(row)
    db.session.commit()
    return jsonify(ok=True)


@app.route("/guestbook")
def guestbook_page():
    """留言板。"""
    rows = db.session.scalars(
        db.select(GuestbookEntry)
        .where(GuestbookEntry.status == "visible")
        .order_by(GuestbookEntry.id.desc())
        .limit(200)
    ).all()
    total = db.session.scalar(
        db.select(func.count()).select_from(GuestbookEntry)
        .where(GuestbookEntry.status == "visible")
    ) or 0
    return render_template("guestbook.html", entries=rows, total=total)


@app.post("/api/guestbook/post")
def guestbook_post():
    if not g.user:
        return jsonify(ok=False, msg="请先登录再留言"), 401

    content = (request.form.get("content") or "").strip()
    if not content:
        return jsonify(ok=False, msg="留言不能为空")
    if len(content) > 1000:
        return jsonify(ok=False, msg="一条留言最多 1000 字")

    # 防刷：同一个人 10 秒内只能留一条
    last = db.session.scalar(
        db.select(GuestbookEntry)
        .where(GuestbookEntry.user_id == g.user.id)
        .order_by(GuestbookEntry.id.desc())
    )
    if last is not None and last.created_at is not None:
        gap = (datetime.now() - last.created_at).total_seconds()
        if gap < 10:
            return jsonify(ok=False, msg="留得有点勤，等 %d 秒再发" % max(1, int(10 - gap)))

    row = GuestbookEntry(user_id=g.user.id, nickname=g.user.display_name,
                         qq_id=g.user.qq_id, content=content)
    db.session.add(row)
    db.session.commit()

    return jsonify(ok=True, entry={
        "id": row.id,
        "nickname": row.nickname,
        "qq_id": row.qq_id or "",
        "content": row.content,
        "when": humanize_time(row.created_at),
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M"),
        "mine": True,
        "reply": "",
        "reply_by": "",
    })


@app.post("/api/guestbook/<int:eid>/delete")
def guestbook_delete(eid):
    if not g.user:
        return jsonify(ok=False, msg="请先登录"), 401

    row = db.session.get(GuestbookEntry, eid)
    if row is None:
        return jsonify(ok=False, msg="这条留言不存在"), 404
    if row.user_id != g.user.id and not g.user.is_admin:
        return jsonify(ok=False, msg="只能删自己的留言"), 403

    db.session.delete(row)
    db.session.commit()
    return jsonify(ok=True)


@app.post("/api/guestbook/<int:eid>/reply")
def guestbook_reply(eid):
    """管理员回复留言。"""
    if not g.user:
        return jsonify(ok=False, msg="请先登录"), 401
    if not g.user.is_admin:
        return jsonify(ok=False, msg="只有管理员能回复"), 403

    row = db.session.get(GuestbookEntry, eid)
    if row is None:
        return jsonify(ok=False, msg="这条留言不存在"), 404

    text = (request.form.get("reply") or "").strip()
    if not text:
        return jsonify(ok=False, msg="回复不能为空")
    if len(text) > 1000:
        return jsonify(ok=False, msg="回复最多 1000 字")

    row.reply = text
    row.reply_by = g.user.display_name
    row.replied_at = datetime.now()
    db.session.commit()

    return jsonify(ok=True, reply=text, reply_by=row.reply_by,
                   when=humanize_time(row.replied_at))


@app.route("/api/me")
def api_me():
    """给静态页顶栏用：告诉前端当前有没有登录、头像用哪个 QQ。"""
    if not g.user:
        return jsonify(logged_in=False)
    u = g.user
    return jsonify(
        logged_in=True,
        username=u.username,
        display_name=u.display_name,
        nickname=u.nickname or "",
        qq_id=u.qq_id or "",
        role=u.role,
        is_admin=u.is_admin,
        is_developer=u.is_developer,
    )


@app.route("/manager/top_name" ,methods=["POST"])
@login_required
def manager_top_name():
   
    top_add=Ranking(top1_name=request.form.get("top1_name"),
                    top2_name=request.form.get("top2_name"),
                    top3_name=request.form.get("top3_name"),
                    top1_qqid=request.form.get("top1_qqid"),
                    top2_qqid=request.form.get("top2_qqid"),
                    top3_qqid=request.form.get("top3_qqid")
                    )
   
    db.session.add(top_add)
    db.session.commit()
    return redirect(url_for('manager'))
@app.route("/manager")
@admin_required
def manager():
    return render_template("manager.html")
@app.route("/")
@app.route("/index.html")
def home():
    """站点首页：直接返回项目根目录的静态页面。"""
    return send_from_directory(app.root_path, "index.html")


@app.route("/background.png")
def background():
    """兼容旧的前端背景图地址。"""
    return send_from_directory(os.path.join(app.static_folder, "img"), "background.png")


@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "GET":
        if g.user:
            return redirect(url_for('manager'))
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    user = db.session.scalar(db.select(User).where(User.username == username))

    if user is None or not user.check_password(password):
        flash("用户名或密码不对", "error")
        return redirect(url_for('login'))
    if user.is_pending:
        flash("这个账号还在等管理员审核，通过后就能登录", "warning")
        return redirect(url_for('login'))
    if not user.is_active:
        flash("这个账号已被停用，请联系管理员", "error")
        return redirect(url_for('login'))

    user.last_login = datetime.now()
    db.session.commit()

    session.clear()
    session['user_id'] = user.id
    # 只有群主 / 群管理员进后台，普通成员回首页
    if user.is_admin:
        return redirect(url_for('manager'))
    return redirect(url_for('home'))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    # 仅本地调试用；线上由 uWSGI / Gunicorn 通过 app 对象启动
    app.run(host="127.0.0.1", port=int(os.environ.get("QIU_PORT", "5000")), debug=False)



    

