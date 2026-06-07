"""航线的数据校验模型"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Waypoint(BaseModel):
    """途经点"""
    lng: float  # 经度
    lat: float  # 纬度
    alt: Optional[float] = 100  # 高度(米)，默认100米
    name: Optional[str] = None  # 点名称


class RouteCreate(BaseModel):
    """创建航线请求"""
    name: Optional[str] = None
    waypoints: list[Waypoint]
    operator_id: Optional[int] = None


class RouteResponse(BaseModel):
    """航线响应"""
    id: int
    name: Optional[str]
    route_line: Optional[dict]  # GeoJSON
    waypoints: Optional[list]
    total_distance: Optional[float]
    estimated_time: Optional[float]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
