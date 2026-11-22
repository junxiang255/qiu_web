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
from datetime import datetime
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
 
    def __init__(self,qq_id: str | None = None, qq_name: str | None = None,
                 work_name: str | None = None, recwork: str = "",
                 img_path: str | None = None):
        self.rw_qq_id = qq_id
        self.rw_qq_name = qq_name
        self.rw_work_name = work_name
        self.rw_recwork = recwork
        self.rw_img_path = img_path

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


class User(db.Model):
    __tablename__='user'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    username:Mapped[str]=mapped_column(String(50),unique=True,nullable=False)
    nickname:Mapped[str|None]=mapped_column(String(50),nullable=True)
    password_hash:Mapped[str]=mapped_column(String(200),nullable=False)
    role:Mapped[str]=mapped_column(String(20),nullable=False,default="user")
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


def admin_required(func):
    """在 login_required 之上再加一层管理员校验。"""
    @wraps(func)
    def inner(*args,**kwargs):
        if not g.user:
            return redirect(url_for("login"))
        if not g.user.is_admin:
            flash("这个操作需要管理员权限", "error")
            return redirect(url_for("manager"))
        return func(*args,**kwargs)
    return inner


# 注册是否开放（环境变量 QIU_ALLOW_REGISTER=0 可关闭）
REGISTER_OPEN = os.environ.get("QIU_ALLOW_REGISTER", "1") != "0"


@app.route("/register", methods=["GET","POST"])
def register():
    if not REGISTER_OPEN:
        return render_template("register.html", closed=True), 403
    if g.user:
        return redirect(url_for("manager"))

    if request.method == "GET":
        return render_template("register.html", closed=False)

    username = (request.form.get("username") or "").strip()
    nickname = (request.form.get("nickname") or "").strip()
    password = request.form.get("password") or ""
    password2 = request.form.get("password2") or ""

    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        flash("用户名只能是 3-20 位字母、数字或下划线", "error")
        return redirect(url_for("register"))
    if len(password) < 6:
        flash("密码至少 6 位", "error")
        return redirect(url_for("register"))
    if password != password2:
        flash("两次输入的密码不一致", "error")
        return redirect(url_for("register"))

    dup = db.session.scalar(db.select(User).where(User.username == username))
    if dup:
        flash("这个用户名已经被注册了", "error")
        return redirect(url_for("register"))

    total = db.session.scalar(db.select(func.count()).select_from(User)) or 0
    u = User(username=username, nickname=nickname or None,
             role="admin" if total == 0 else "user")
    u.password = password

    try:
        db.session.add(u)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("这个用户名已经被注册了", "error")
        return redirect(url_for("register"))

    session.clear()
    session["user_id"] = u.id
    flash("注册成功，欢迎 %s" % u.display_name, "success")
    return redirect(url_for("manager"))


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
    items = db.session.scalars(db.select(User).order_by(User.id)).all()
    return render_template("users.html", items=items)


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
@login_required
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
    if not user.is_active:
        flash("这个账号已被停用，请联系管理员", "error")
        return redirect(url_for('login'))

    user.last_login = datetime.now()
    db.session.commit()

    session.clear()
    session['user_id'] = user.id
    return redirect(url_for('manager'))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    # 仅本地调试用；线上由 uWSGI / Gunicorn 通过 app 对象启动
    app.run(host="127.0.0.1", port=int(os.environ.get("QIU_PORT", "5000")), debug=False)



    

