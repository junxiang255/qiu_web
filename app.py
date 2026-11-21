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

class User(db.Model):
    __tablename__='user'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    username:Mapped[str]=mapped_column(String(50))
    password_hash:Mapped[str]=mapped_column(String(200))

    def __init__(self,*args,**kwargs):
        password = kwargs.get("password")
        if password:
            kwargs.pop("password")
        super().__init__(*args,**kwargs)
        self.password=password

    @property
    def password(self):
        return self.password_hash
            



    @password.setter
    def password(self,raw_password):
        self.password_hash=generate_password_hash(raw_password)


    def check_password(self,raw_password):
        return check_password_hash(self.password,raw_password)







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
        return render_template("login.html")

    username=request.form.get("username")
    password=request.form.get("password")
    user=db.session.scalar(db.select(User).where(User.username==username))
    if user and user.check_password(password):
        session['user_id']=user.id
        return redirect(url_for('manager'))
    return redirect(url_for('login'))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    # 仅本地调试用；线上由 uWSGI / Gunicorn 通过 app 对象启动
    app.run(host="127.0.0.1", port=int(os.environ.get("QIU_PORT", "5000")), debug=False)



    

