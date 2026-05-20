from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行：建表
    await init_db()
    yield
    # 关闭时执行（暂不需要）


app = FastAPI(title="Knowledge Agent", version="0.1.0", lifespan=lifespan)

# 允许前端跨域访问（Next.js 默认端口 3000）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "knowledge-agent"}
