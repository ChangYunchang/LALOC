"""建筑物数据模型 — OSM 建筑数据，供路径规划使用"""
from sqlalchemy import Column, Integer, BigInteger, String, Float
from geoalchemy2 import Geometry
from app.database import Base


class Building(Base):
    """建筑物（OSM 数据源）

    存储建筑轮廓（2D Polygon）和高度信息，用于 A* 路径规划的障碍物避让。
    """
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    osm_id = Column(BigInteger, nullable=True, index=True, comment="OSM 原始 ID")
    name = Column(String(255), nullable=True, comment="建筑名称")
    geometry = Column(
        Geometry("POLYGON", srid=4326, spatial_index=True),
        nullable=False,
        comment="建筑底面轮廓 (WGS84)"
    )
    height = Column(Float, nullable=True, comment="建筑高度(米)，优先使用 OSM height 标签")
    levels = Column(Integer, nullable=True, comment="楼层数，用于估算高度 (levels * 3m)")

    @property
    def effective_height(self) -> float:
        """获取有效高度：height 标签优先，否则用 levels*3 估算，默认 10m"""
        if self.height is not None:
            return self.height
        if self.levels is not None:
            return self.levels * 3.0
        return 10.0

    def __repr__(self):
        h = self.effective_height
        return f"<Building(osm_id={self.osm_id}, name='{self.name}', height={h}m)>"
