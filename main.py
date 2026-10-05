# uv run uvicorn main:app --reload
from contextlib import asynccontextmanager

from fastapi import FastAPI, Path, Query
import time
import asyncio
from fastapi import Depends


"""
ORM-建表
"""
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Float, String, func, select
from datetime import datetime

# 1、创建异步引擎
ASYNC_DATABASE_URL= "mysql+aiomysql://baozi:Bjj13431872864@localhost:3306/fastapi_first?charset=utf8"
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo = False,  # 可选，输出 SQL 日志
    pool_size = 10,  # 设置连接池活跃的连接数
    max_overflow = 20  # 允许额外的连接数
)

# 2、定义模型类：基类 + 表对应的模型类
# 基类：创建时间、更新时间；书籍表：id、书名、作者、价格、出版社
class Base(DeclarativeBase):
    create_time: Mapped[datetime] = mapped_column(DateTime, default=func.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=func.now, onupdate=func.now(), comment="更新时间")

class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True, comment="书籍id")
    bookname: Mapped[str] = mapped_column(String(255), comment="书名")
    author: Mapped[str] = mapped_column(String(255), comment="作者")
    price: Mapped[float] = mapped_column(Float, comment="价格")
    publisher: Mapped[str] = mapped_column(String(255), comment="出版社")

# 3、建表：定义函数建表 → FastAPI 启动时调用建表的函数
async def create_tables():
    # 获取异步引擎，创建事务 - 建表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Base 模型类的元数据创建

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === 启动时执行（替代原来的 @app.on_event("startup") ===
    await create_tables()

    yield  # 应用运行期间停在这里

    # === 关闭时执行（替代原来的 @app.on_event("shutdown") ===
    await async_engine.dispose()  # 关闭数据库连接池

app = FastAPI(lifespan=lifespan)


"""
ORM - 路由匹配中使用ORM
核心：创建依赖项，使用Depends注入到处理函数
需求：查询功能的接口，查询图书 → 依赖注入：创建依赖项获取数据库会话 + Depends 注入路由处理函数
"""
# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind = async_engine,  # 绑定数据库引擎
    class_ = AsyncSession,  # 指定会话类
    expire_on_commit = False  # 会话对象不过期，不重新查询数据库
)

# 依赖项，用于获取数据库会话
async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session  # 返回数据库会话给路由处理函数
            await session.commit()  # 无异常，提交事务
        except Exception:
            await session.rollback()  # 有异常则回滚
            raise
        finally:
            await session.close()  # 关闭会话

@app.get("/book/books")
async def get_book_list(db: AsyncSession = Depends(get_database)):
    # 查询所有书籍
    result = await db.execute(select(Book))  # Book 模型类
    user = result.scalars().all()
    return user


"""
数据库操作 - 普通查询
"""
@app.get("/book/book_select")
async def select_book_1(db: AsyncSession = Depends(get_database)):
    result = await db.execute(select(Book))
    # book = result.scalars().all()  # 获取所有数据
    # book = result.scalars().first()  # 方法一：获取单条数据
    book = await db.get(Book, 1)  # 方法二：获取单条数据。注：get(模型类，主键值)
    return book


"""
数据库操作 - 条件查询
1、比较判断: ==; >; <等
2、模糊查询: like()
3、与非查询: &; |; ~
4、包含查询: in_()
"""
@app.get("/book/{book_id}")
async def select_book_2(book_id: int, db: AsyncSession = Depends(get_database)):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()  # 有则赋值该数据，没有则赋值null
    return book

"""
异步
"""
@app.get("/async")
async def func_async():
    start = time.time()
    tasks = [asyncio.sleep(1) for i in range(10)]
    await asyncio.gather(*tasks)
    end = time.time()
    return {"time": f'{end - start:.2f}s'}


"""
同步
"""
@app.get("/sync")
def func_sync():
    start = time.time()
    for i in range(10):
        time.sleep(1)
    end = time.time()
    return {"time": f'{end - start:.2f}s'}


"""
路径参数
"""
@app.get("/path_parameter/{num}")
async def test_path(num: int = Path(..., gt=0, lt=101, description="取值范围1-100")):  # 类型注解 Path
    return {f"现在是{num}"}


"""
查询参数
"""
@app.get("/query_parameter")
async def test_query(name: str = Query("baozi", min_length=2, max_length=10), id_1: int = 6):  # 类型注解 Query
    return {"name": name, "id_1": id_1}


"""
请求体参数
"""
# 1、定义类型
from pydantic import BaseModel, Field
class User(BaseModel):
    username: str = Field("baozi", min_length=2)
    password: str

@app.post("/register")
async def register(user: User):
    return user


"""
HTMLResponse
"""
from fastapi.responses import HTMLResponse
@app.get("/html", response_class=HTMLResponse)
async def get_html():
    html_content = """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Look ma! HTML!</h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


"""
FileResponse
"""
from fastapi.responses import FileResponse
@app.get("/file")
async def get_file():
    path = '画.jpg'
    return FileResponse(path)


"""
自定义响应数据格式
"""
class News(BaseModel):
    id: int
    title: str

@app.get("/news/{id}", response_model=News)
async def get_news(id: int):
    return {
        "id": id,
        "title": f"this is num_{id} book"
    }


"""
异常处理
"""
from fastapi import HTTPException
@app.get('/exception/{id}')
async def get_exception(id: int):
    id_list = [1, 2, 3]
    if id not in id_list:
        raise HTTPException(status_code=404, detail="当前id不存在")  # 使用 HTTPException 中断正常处理流程
    return {"id": id}


"""
中间件（控制所有请求）
中间件在请求到达实际的路径操作（路由处理函数）之前运行，并且在响应返回给客户端之前再运行一次
注意：多个中间件时，执行顺序是：按代码顺序，自底向上执行
"""
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

@app.get("/")
async def root():
    return "Hello"


"""
依赖注入（控制谁，程序员说了算）
依赖项：可重用的组件（函数/类），负责提供某种功能或数据
注入：Fast API自动帮你调用依赖项，并将结果“注入”到路径操作函数中
"""
async def common_parameters(  # 创建依赖项
        skip: int = Query(0, ge=0),
        limit: int = Query(10, le=60)
):
    return {
        "skip": skip,
        "limit": limit
    }

@app.get("/test/test_list")
async def get_test_list(commons = Depends(common_parameters)):  # 调用依赖项
    return commons


