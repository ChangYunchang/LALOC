"""无人机飞行记录数据库模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.database import Base


class DroneFlight(Base):
    """无人机飞行记录"""
    __tablename__ = "drone_flights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(Integer, nullable=True, comment="关联航线ID")
    drone_id = Column(String(100), nullable=False, comment="无人机编号")
    current_position = Column(
        Geometry("POINTZ", srid=4326, spatial_index=True),
        nullable=True,
        comment="当前位置（含高度）"
    )
    trajectory = Column(
        Geometry("LINESTRINGZ", srid=4326, spatial_index=True),
        nullable=True,
        comment="飞行轨迹"
    )
    status = Column(String(50), default="idle", comment="状态: idle/flying/completed/error")
    speed = Column(Float, nullable=True, comment="当前速度(m/s)")
    altitude = Column(Float, nullable=True, comment="当前高度(米)")
    start_time = Column(DateTime, nullable=True, comment="起飞时间")
    end_time = Column(DateTime, nullable=True, comment="降落时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<DroneFlight(id={self.id}, drone_id='{self.drone_id}')>"


class WeatherRecord(Base):
    """天气记录（缓存）"""
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(100), nullable=True, comment="城市")
    temperature = Column(Float, nullable=True, comment="温度(℃)")
    humidity = Column(Float, nullable=True, comment="湿度(%)")
    wind_direction = Column(String(50), nullable=True, comment="风向")
    wind_power = Column(String(50), nullable=True, comment="风力")
    weather_desc = Column(String(100), nullable=True, comment="天气描述")
    report_time = Column(DateTime, nullable=True, comment="报告时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<WeatherRecord(city='{self.city}', weather='{self.weather_desc}')>"
