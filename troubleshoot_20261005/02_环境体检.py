# -*- coding: utf-8 -*-
"""
uv / FastAPI 项目环境一键体检脚本

用途：以后再遇到「明明装了包却导入失败」「ImportError: cannot import name xxx」
     「版本对不上」这类问题，先跑这个脚本，30 秒定位是环境跑串了还是包版本不对。

用法：
    cd D:\\python_code\\FastAPI_hello
    uv run python troubleshoot_20261005\\02_环境体检.py

注意：请务必用 `uv run python ...` 启动，否则脚本自己也可能跑在别的解释器上。
"""

import os
import shutil
import sys
import importlib
import asyncio

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OK = "[ OK ]"
WARN = "[WARN]"
BAD = "[ !! ]"

problems = []


def line(title=""):
    print("\n" + "=" * 64)
    if title:
        print(title)
        print("=" * 64)


# ---------------------------------------------------------------- 1. 解释器
line("1. 当前解释器")
print(f"  executable : {sys.executable}")
print(f"  version    : {sys.version.split()[0]}")
print(f"  prefix     : {sys.prefix}")

in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
if in_venv:
    print(f"  {OK} 运行在虚拟环境中")
else:
    print(f"  {BAD} 不在虚拟环境中！这是很多导入错误的根源")
    problems.append("当前不在虚拟环境中，请用 `uv run python 脚本.py` 启动")

exe_low = sys.executable.lower()
for suspect in ("anaconda", "miniconda"):
    if suspect in exe_low:
        print(f"  {BAD} 解释器来自 {suspect}，不是项目 .venv —— 环境跑串了")
        problems.append(f"解释器来自 {suspect}，不是项目 .venv")
if "anaconda" in exe_low or "miniconda" in exe_low:
    print("       报错栈里出现 Anaconda 路径 = 跑串了，不是代码问题")

# ---------------------------------------------------------------- 2. sys.path
line("2. sys.path 前 10 项（看有没有被塞进别的 site-packages）")
for i, p in enumerate(sys.path[:10]):
    tag = ""
    if "anaconda" in p.lower() or "miniconda" in p.lower():
        tag = f"   {BAD} 外来 site-packages！"
    print(f"  [{i}] {p or '(空)'}{tag}")
    if tag:
        problems.append(f"sys.path 被注入外来路径: {p}")

pp = os.environ.get("PYTHONPATH", "")
print(f"\n  PYTHONPATH : {pp or '(未设置)'}")
if "anaconda" in pp.lower():
    print(f"  {BAD} PYTHONPATH 里含 Anaconda 路径，会污染所有 Python 进程")
    problems.append("PYTHONPATH 里含 Anaconda 路径")

# ---------------------------------------------------------------- 3. 关键包
line("3. 关键包版本与来源")
PKGS = {
    "fastapi": "0.100.0",
    "uvicorn": "0.20.0",
    "sqlalchemy": "2.0.0",
    "pydantic": "2.0.0",
    "aiomysql": "0.2.0",
}
for name, min_ver in PKGS.items():
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "?")
        path = getattr(mod, "__file__", "?") or "?"
        bad_path = "anaconda" in path.lower()
        flag = BAD if bad_path else OK
        print(f"  {flag} {name:<12} {ver:<12} {path}")
        if bad_path:
            problems.append(f"{name} 来自 Anaconda，不是项目 .venv")
        if name == "sqlalchemy" and not bad_path:
            try:
                major, minor = (int(x) for x in ver.split(".")[:2])
                if (major, minor) < (2, 0):
                    print(f"        {BAD} SQLAlchemy < 2.0，没有 DeclarativeBase（1.4 用 declarative_base()）")
                    problems.append("SQLAlchemy 版本 < 2.0，无 DeclarativeBase")
            except Exception:
                pass
    except ImportError as e:
        print(f"  {BAD} {name:<12} 未安装 ({e})")
        problems.append(f"{name} 未安装")

# ---------------------------------------------------------------- 4. SQLAlchemy API
line("4. SQLAlchemy 2.0 API 可用性")
try:
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy import DateTime, Float, String, func
    from sqlalchemy.ext.asyncio import create_async_engine
    print(f"  {OK} DeclarativeBase / Mapped / mapped_column 均可导入")
    print(f"  {OK} create_async_engine 可导入")
except ImportError as e:
    print(f"  {BAD} 导入失败: {e}")
    problems.append(f"SQLAlchemy 2.0 API 导入失败: {e}")

# ---------------------------------------------------------------- 5. uvicorn 命令
line("5. uvicorn 命令实际会被哪个可执行文件接管")
uv_in_venv = os.path.join(sys.prefix, "Scripts", "uvicorn.exe")
if os.path.exists(uv_in_venv):
    print(f"  {OK} 项目环境内有: {uv_in_venv}")
else:
    print(f"  {BAD} 项目环境内没有 uvicorn！`uv run uvicorn` 会回退到 PATH，"
          f"用错的解释器")
    problems.append("项目环境内没有 uvicorn，uv run 会静默回退到 PATH")

found = shutil.which("uvicorn")
print(f"  PATH 中首个 uvicorn : {found or '(PATH 里没有)'}")
if found and "anaconda" in found.lower():
    print(f"  {BAD} 命中的是 Anaconda 的 uvicorn —— 会用 Anaconda 的 Python 和旧包")
    problems.append("PATH 里首个 uvicorn 属于 Anaconda")

# ---------------------------------------------------------------- 6. Anaconda 对照
line("6. Anaconda base 环境对照（若是它接管了会怎样）")
for cand in (r"G:\Anaconda3", r"G:\Anaconda"):
    sa = os.path.join(cand, "Lib", "site-packages", "sqlalchemy", "__init__.py")
    if os.path.exists(sa):
        try:
            with open(sa, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            import re
            m = re.search(r'__version__\s*=\s*"([^"]+)"', txt)
            ver = m.group(1) if m else "?"
            has_db = "DeclarativeBase" in open(
                os.path.join(cand, "Lib", "site-packages", "sqlalchemy", "orm", "__init__.py"),
                encoding="utf-8", errors="ignore").read()
            print(f"  {cand}: SQLAlchemy {ver}, 含 DeclarativeBase = {has_db}")
            if not has_db:
                print(f"        -> 一旦被它接管，必然报 cannot import name 'DeclarativeBase'")
        except Exception as e:
            print(f"  {cand}: 读取失败 {e}")

# ---------------------------------------------------------------- 7. 数据库
line("7. 数据库连通性（MySQL）")
try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    url = os.environ.get(
        "DATABASE_URL",
        "mysql+aiomysql://baozi:Bjj13431872864@localhost:3306/fastapi_first?charset=utf8",
    )
    host_part = url.split("@")[-1] if "@" in url else url
    print(f"  目标: ...@{host_part}")

    async def check():
        eng = create_async_engine(url)
        try:
            async with eng.connect() as conn:
                r = await conn.execute(text("select version()"))
                print(f"  {OK} 连接成功，MySQL 版本 {r.scalar()}")
        except Exception as ex:
            print(f"  {WARN} 连接失败: {type(ex).__name__}: {str(ex)[:160]}")
            problems.append(f"数据库连接失败: {type(ex).__name__}")
        finally:
            await eng.dispose()

    asyncio.run(check())
except Exception as e:
    print(f"  {WARN} 跳过: {e}")

# ---------------------------------------------------------------- 8. 结论
line("体检结论")
if problems:
    print(f"发现 {len(problems)} 个问题：")
    for i, p in enumerate(problems, 1):
        print(f"  {i}. {p}")
    print("\n常见处理：")
    print("  uv add \"uvicorn[standard]\"     # 补装服务器")
    print("  uv sync                        # 按 lock 对齐环境")
    print("  uv run python -m uvicorn main:app --reload   # 强制走项目环境")
else:
    print(f"{OK} 全部正常，环境干净，可以直接 `uv run uvicorn main:app --reload`")
print("=" * 64)
