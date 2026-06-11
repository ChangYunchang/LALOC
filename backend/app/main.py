"""
城市低空物流运营中心 - 后端 API 服务
FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.api import zones, weather, pathfinding, routes
from app.api import airspace, logistics, safety, statistics, system_mgmt

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"{settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"API docs: http://localhost:8001/docs")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="城市低空物流运营中心后端 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 原有路由
app.include_router(zones.router)
app.include_router(weather.router)
app.include_router(pathfinding.router)
app.include_router(routes.router)

# 新增子系统路由
app.include_router(airspace.router)
app.include_router(logistics.router)
app.include_router(safety.router)
app.include_router(statistics.router)
app.include_router(system_mgmt.router)


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
