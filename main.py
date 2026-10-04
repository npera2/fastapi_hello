# uv run uvicorn main:app --reload
from fastapi import FastAPI, Path, Query
import time
import asyncio

app = FastAPI()

# 异步
@app.get("/async")
async def func_async():
    start = time.time()
    tasks = [asyncio.sleep(1) for i in range(10)]
    await asyncio.gather(*tasks)
    end = time.time()
    return {"time": f'{end - start:.2f}s'}

# 同步
@app.get("/sync")
def func_sync():
    start = time.time()
    for i in range(10):
        time.sleep(1)
    end = time.time()
    return {"time": f'{end - start:.2f}s'}

# 路径参数
@app.get("/path_parameter/{num}")
async def test_path(num: int = Path(..., gt=0, lt=101, description="取值范围1-100")):  # 类型注解 Path
    return {f"现在是{num}"}

# 查询参数
@app.get("/query_parameter")
async def test_query(name: str = Query("baozi", min_length=2, max_length=10), id_1: int = 6):  # 类型注解 Query
    return {"name": name, "id_1": id_1}

# 请求体参数
# 1、定义类型
from pydantic import BaseModel, Field
class User(BaseModel):
    username: str = Field("baozi", min_length=2)
    password: str

@app.post("/register")
async def register(user: User):
    return user

# HTMLResponse
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

# FileResponse
from fastapi.responses import FileResponse
@app.get("/file")
async def get_file():
    path = '画.jpg'
    return FileResponse(path)

# 自定义响应数据格式
class News(BaseModel):
    id: int
    title: str

@app.get("/news/{id}", response_model=News)
async def get_news(id: int):
    return {
        "id": id,
        "title": f"this is num_{id} book"
    }

# 异常处理
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
from fastapi import Depends
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