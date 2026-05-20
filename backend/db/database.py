from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,       # 设 True 会打印所有 SQL，开发调试用
    pool_size=10,     # 连接池大小
    max_overflow=5,   # 连接池满了最多再开 5 个
)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """所有数据表模型继承这个 Base"""
    pass


async def init_db():
    """创建所有表，main.py 启动时调用一次"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：每个请求拿一个数据库会话"""
    async with async_session() as session:
        yield session
