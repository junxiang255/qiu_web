import os
from functools import wraps

from flask import *
import pymysql
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import MetaData, Integer, String
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

from config import DB_CONFIG, SECRET_KEY, SQLALCHEMY_DATABASE_URI

app = Flask(__name__)
app.json.ensure_ascii = False
CORS(app)
app.secret_key = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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



def login_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if g.user:
            return func(*args,**kwargs)
        else:
            return redirect("/login")
    return inner





@app.route("/api/top_name")
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



    

