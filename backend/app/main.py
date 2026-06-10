"""
城市低空物流运营中心 - 后端 API 服务
FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.api import zones, weather, pathfinding, routes

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"API docs: http://localhost:8000/docs")
    # SHP 数据已在首次启动时导入，跳过重复导入
    yield


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="城市低空物流运营中心后端 API，提供禁飞区/限高区管理、天气查询、路径规划等服务",
    lifespan=lifespan,
)

# 配置 CORS 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(zones.router)
app.include_router(weather.router)
app.include_router(pathfinding.router)
app.include_router(routes.router)


@app.get("/")
def root():
    """API 根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "禁飞区": "/api/zones/no-fly",
            "限高区": "/api/zones/height-limit",
            "天气": "/api/weather/live",
            "路径规划": "/api/pathfinding/plan",
            "航线": "/api/routes/",
        },
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}
