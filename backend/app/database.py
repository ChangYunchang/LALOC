"""数据库连接配置"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# 使用 psycopg (v3) 驱动，避免 Windows 中文系统的编码问题
db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

# 创建数据库引擎
engine = create_engine(
    db_url,
    echo=settings.DEBUG,  # 打印 SQL 语句（调试用）
    pool_pre_ping=True,   # 连接前检测可用性
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_db():
    """获取数据库会话（FastAPI 依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
