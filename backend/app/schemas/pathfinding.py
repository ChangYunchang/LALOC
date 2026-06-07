"""路径规划的数据校验模型"""
from pydantic import BaseModel, Field
from typing import Optional


class Coordinate(BaseModel):
    """坐标点"""
    lng: float = Field(..., description="经度")
    lat: float = Field(..., description="纬度")
    alt: Optional[float] = Field(100, description="飞行高度(米)")


class PathPlanRequest(BaseModel):
    """路径规划请求"""
    start: Coordinate = Field(..., description="起点")
    end: Coordinate = Field(..., description="终点")
    waypoints: Optional[list[Coordinate]] = Field(default=[], description="途经点列表")
    drone_speed: Optional[float] = Field(15.0, description="无人机速度(m/s)")
    safety_margin: Optional[float] = Field(50.0, description="安全距离(米)")
    avoid_no_fly: Optional[bool] = Field(True, description="避开禁飞区")
    avoid_height_limit: Optional[bool] = Field(True, description="避开限高区")
    consider_weather: Optional[bool] = Field(True, description="考虑天气因素")


class PathSegment(BaseModel):
    """路径段"""
    from_point: Coordinate
    to_point: Coordinate
    distance: float  # 米
    estimated_time: float  # 秒
    altitude: float  # 飞行高度
    warnings: list[str] = []  # 警告信息


class PathPlanResponse(BaseModel):
    """路径规划响应"""
    path: list[Coordinate] = Field(..., description="路径点列表")
    total_distance: float = Field(..., description="总距离(米)")
    estimated_time: float = Field(..., description="预计时间(秒)")
    segments: list[PathSegment] = Field(..., description="路径段详情")
    warnings: list[str] = Field(default=[], description="全局警告")
    is_feasible: bool = Field(True, description="是否可行")
