# 修正版参考代码（不改动你的原 main.py，仅供对照/替换）
# 启动：uv run uvicorn main:app --reload
#
# 与原 main.py 的 5 处差异，详见同目录《01_排查报告.md》：
#   ① 依赖 uvicorn 未装（这是 ImportError 的真凶）→ 已用 uv add 修复
#   ② mapped_column 同时传 default + insert_default → SQLAlchemy 2.1 报错，已去掉 insert_default
#   ③ app = FastAPI() 被文件末尾重新赋值 → 路由全丢，改为只创建一次
#   ④ mapped_column(float) → 换成 Float
#   ⑤ 数据库密码硬编码 → 改走环境变量（可保留默认值）

from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import os
import time

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ============================================================
# 一、ORM：引擎 + 模型（必须在 app 之前定义，lifespan 要用到）
# ============================================================

# 1、创建异步引擎（密码不要写死在源码里，用环境变量）
ASYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://baozi:Bjj13431872864@localhost:3306/fastapi_first?charset=utf8",
)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,           # 可选，输出 SQL 日志
    pool_size=10,        # 连接池活跃连接数
    max_overflow=20,     # 允许的额外连接数
)


# 2、定义模型类：基类 + 表对应的模型类
class Base(DeclarativeBase):
    # 注意：default 与 insert_default 互斥，二者只能留一个。
    # default=func.now() 在 INSERT 时生效，效果等同原来的 insert_default。
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True, comment="书籍id")
    bookname: Mapped[str] = mapped_column(String(255), comment="书名")
    author: Mapped[str] = mapped_column(String(255), comment="作者")
    price: Mapped[float] = mapped_column(Float, comment="价格")   # 用 Float，不要用内置 float
    publisher: Mapped[str] = mapped_column(String(255), comment="出版社")


# 3、建表函数
async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ============================================================
# 二、应用生命周期（lifespan 必须在 FastAPI() 之前定义）
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === 启动时 ===
    await create_tables()
    yield
    # === 关闭时 ===
    await async_engine.dispose()


# 只创建一次 app，并挂上 lifespan。
# 原代码在此处再次赋值 app，会把上面注册的所有路由全部丢掉。
app = FastAPI(lifespan=lifespan)


# ============================================================
# 三、路由
# ============================================================

@app.get("/")
async def root():
    return "Hello"


"""异步"""
@app.get("/async")
async def func_async():
    start = time.time()
    tasks = [asyncio.sleep(1) for _ in range(10)]
    await asyncio.gather(*tasks)
    end = time.time()
    return {"time": f"{end - start:.2f}s"}


"""同步"""
@app.get("/sync")
def func_sync():
    start = time.time()
    for _ in range(10):
        time.sleep(1)
    end = time.time()
    return {"time": f"{end - start:.2f}s"}


"""路径参数"""
@app.get("/path_parameter/{num}")
async def test_path(num: int = Path(..., gt=0, lt=101, description="取值范围1-100")):
    return {f"现在是{num}"}


"""查询参数"""
@app.get("/query_parameter")
async def test_query(
    name: str = Query("baozi", min_length=2, max_length=10), id_1: int = 6
):
    return {"name": name, "id_1": id_1}


"""请求体参数"""
class User(BaseModel):
    username: str = Field("baozi", min_length=2)
    password: str


@app.post("/register")
async def register(user: User):
    return user


"""HTMLResponse"""
@app.get("/html", response_class=HTMLResponse)
async def get_html():
    html_content = """
    <html>
        <head><title>Some HTML in here</title></head>
        <body><h1>Look ma! HTML!</h1></body>
    </html>
    """
    return HTMLResponse(content=html_content)


"""FileResponse"""
@app.get("/file")
async def get_file():
    return FileResponse("画.jpg")


"""自定义响应数据格式"""
class News(BaseModel):
    id: int
    title: str


@app.get("/news/{id}", response_model=News)
async def get_news(id: int):
    return {"id": id, "title": f"this is num_{id} book"}


"""异常处理"""
@app.get("/exception/{id}")
async def get_exception(id: int):
    id_list = [1, 2, 3]
    if id not in id_list:
        raise HTTPException(status_code=404, detail="当前id不存在")
    return {"id": id}


"""中间件：执行顺序自底向上（middleware2 先执行）"""
@app.middleware("http")
async def middleware1(request, call_next):
    print("中间件1执行")
    response = await call_next(request)
    print("中间件1结束")
    return response


@app.middleware("http")
async def middleware2(request, call_next):
    print("中间件2执行")
    response = await call_next(request)
    print("中间件2结束")
    return response


"""依赖注入"""
async def common_parameters(skip: int = Query(0, ge=0), limit: int = Query(10, le=60)):
    return {"skip": skip, "limit": limit}


@app.get("/test/test_list")
async def get_test_list(commons=Depends(common_parameters)):
    return commons
