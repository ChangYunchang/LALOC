"""禁飞区和限高区数据库模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.database import Base


class NoFlyZone(Base):
    """禁飞区"""
    __tablename__ = "no_fly_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True, comment="区域名称")
    geometry = Column(
        Geometry("POLYGON", srid=4326, spatial_index=True),
        nullable=False,
        comment="多边形几何（WGS84）"
    )
    altitude_min = Column(Float, default=0, comment="最低限制高度(米)")
    altitude_max = Column(Float, default=9999, comment="最高限制高度(米)")
    reason = Column(String(500), nullable=True, comment="禁飞原因")
    effective_start = Column(DateTime, nullable=True, comment="生效开始时间")
    effective_end = Column(DateTime, nullable=True, comment="生效结束时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<NoFlyZone(id={self.id}, name='{self.name}')>"


class HeightLimitZone(Base):
    """限高区"""
    __tablename__ = "height_limit_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True, comment="区域名称")
    geometry = Column(
        Geometry("POLYGON", srid=4326, spatial_index=True),
        nullable=False,
        comment="多边形几何（WGS84）"
    )
    max_altitude = Column(Float, nullable=False, comment="最大允许飞行高度(米)")
    min_altitude = Column(Float, default=0, comment="最低飞行高度(米)")
    reason = Column(String(500), nullable=True, comment="限高原因")
    effective_start = Column(DateTime, nullable=True, comment="生效开始时间")
    effective_end = Column(DateTime, nullable=True, comment="生效结束时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<HeightLimitZone(id={self.id}, name='{self.name}')>"
