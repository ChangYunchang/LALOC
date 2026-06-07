"""禁飞区和限高区的数据校验模型"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ZoneBase(BaseModel):
    """区域基础模型"""
    name: Optional[str] = None
    reason: Optional[str] = None
    effective_start: Optional[datetime] = None
    effective_end: Optional[datetime] = None


class NoFlyZoneResponse(ZoneBase):
    """禁飞区响应模型"""
    id: int
    altitude_min: float
    altitude_max: float
    geometry: dict  # GeoJSON 格式

    class Config:
        from_attributes = True


class HeightLimitZoneResponse(ZoneBase):
    """限高区响应模型"""
    id: int
    max_altitude: float
    min_altitude: float
    geometry: dict  # GeoJSON 格式

    class Config:
        from_attributes = True


class ZoneListResponse(BaseModel):
    """区域列表响应"""
    type: str = "FeatureCollection"
    features: list[dict]
