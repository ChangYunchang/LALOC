"""禁飞区和限高区业务服务"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.zones import NoFlyZone, HeightLimitZone
import json


class ZoneService:
    """区域服务"""

    @staticmethod
    def get_all_no_fly_zones(db: Session) -> list[dict]:
        """获取所有禁飞区，返回 GeoJSON 格式"""
        zones = db.query(NoFlyZone).all()
        features = []
        for zone in zones:
            # 使用 PostGIS 的 ST_AsGeoJSON 函数将几何转为 GeoJSON
            result = db.execute(
                text("SELECT ST_AsGeoJSON(geometry) FROM no_fly_zones WHERE id = :id"),
                {"id": zone.id}
            ).fetchone()
            geom_json = json.loads(result[0]) if result else None

            features.append({
                "type": "Feature",
                "geometry": geom_json,
                "properties": {
                    "id": zone.id,
                    "name": zone.name or f"禁飞区-{zone.id}",
                    "altitude_min": zone.altitude_min,
                    "altitude_max": zone.altitude_max,
                    "reason": zone.reason,
                    "effective_start": zone.effective_start.isoformat() if zone.effective_start else None,
                    "effective_end": zone.effective_end.isoformat() if zone.effective_end else None,
                }
            })
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def get_all_height_limit_zones(db: Session) -> list[dict]:
        """获取所有限高区，返回 GeoJSON 格式"""
        zones = db.query(HeightLimitZone).all()
        features = []
        for zone in zones:
            result = db.execute(
                text("SELECT ST_AsGeoJSON(geometry) FROM height_limit_zones WHERE id = :id"),
                {"id": zone.id}
            ).fetchone()
            geom_json = json.loads(result[0]) if result else None

            features.append({
                "type": "Feature",
                "geometry": geom_json,
                "properties": {
                    "id": zone.id,
                    "name": zone.name or f"限高区-{zone.id}",
                    "max_altitude": zone.max_altitude,
                    "min_altitude": zone.min_altitude,
                    "reason": zone.reason,
                    "effective_start": zone.effective_start.isoformat() if zone.effective_start else None,
                    "effective_end": zone.effective_end.isoformat() if zone.effective_end else None,
                }
            })
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def check_point_in_no_fly(db: Session, lng: float, lat: float) -> bool:
        """检查一个点是否在禁飞区内"""
        result = db.execute(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM no_fly_zones
                    WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                )
            """),
            {"lng": lng, "lat": lat}
        ).fetchone()
        return result[0] if result else False

    @staticmethod
    def check_point_in_height_limit(db: Session, lng: float, lat: float) -> list[dict]:
        """检查一个点所在的限高区，返回限高信息"""
        result = db.execute(
            text("""
                SELECT id, name, max_altitude, min_altitude
                FROM height_limit_zones
                WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
            """),
            {"lng": lng, "lat": lat}
        ).fetchall()
        return [
            {"id": r[0], "name": r[1], "max_altitude": r[2], "min_altitude": r[3]}
            for r in result
        ]

    @staticmethod
    def get_zone_stats(db: Session) -> dict:
        """获取区域统计信息"""
        no_fly_count = db.query(NoFlyZone).count()
        height_limit_count = db.query(HeightLimitZone).count()
        return {
            "no_fly_zones_count": no_fly_count,
            "height_limit_zones_count": height_limit_count,
        }
