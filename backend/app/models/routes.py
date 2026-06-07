"""航线数据库模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.database import Base


class Route(Base):
    """航线"""
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True, comment="航线名称")
    route_line = Column(
        Geometry("LINESTRING", srid=4326, spatial_index=True),
        nullable=True,
        comment="航线路径"
    )
    waypoints = Column(JSON, nullable=True, comment="途经点列表")
    total_distance = Column(Float, nullable=True, comment="总距离(米)")
    estimated_time = Column(Float, nullable=True, comment="预计时间(秒)")
    status = Column(String(50), default="planned", comment="状态: planned/active/completed")
    operator_id = Column(Integer, nullable=True, comment="运营方ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<Route(id={self.id}, name='{self.name}')>"
