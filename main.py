from fastapi import FastAPI
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