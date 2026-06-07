"""应用配置文件"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用设置"""
    # 应用
    APP_NAME: str = "城市低空物流运营中心"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "postgresql://admin:lowaltitude2024@localhost:5433/lowaltitude_logistics"

    # 高德地图
    AMAP_WEB_SERVICE_KEY: str = ""
    AMAP_SECURITY_CODE: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
