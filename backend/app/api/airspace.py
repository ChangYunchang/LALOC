"""
空域管理子系统 API
提供空域规则 CRUD、空间约束查询、航线合规审查和统计接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional
from datetime import datetime
import json

from app.database import get_db
from app.models.zones import NoFlyZone, HeightLimitZone

router = APIRouter(prefix="/api/airspace", tags=["空域管理"])


# ──────────────────────────────────────────────────────────────
# 2.1 空域规则管理（禁飞区 / 限高区 CRUD）
# ──────────────────────────────────────────────────────────────

@router.get("/no-fly-zones")
def list_no_fly_zones(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """列出禁飞区（分页）"""
    query = db.query(NoFlyZone)
    if name:
        query = query.filter(NoFlyZone.name.ilike(f"%{name}%"))
    total = query.count()
    items = query.order_by(NoFlyZone.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_zone(z) for z in items],
    }


@router.post("/no-fly-zones")
def create_no_fly_zone(data: dict, db: Session = Depends(get_db)):
    """新建禁飞区"""
    geom_wkt = _coords_to_wkt(data.get("coordinates", []))
    zone = NoFlyZone(
        name=data.get("name"),
        geometry=f"SRID=4326;{geom_wkt}",
        altitude_min=data.get("altitude_min", 0),
        altitude_max=data.get("altitude_max", 9999),
        reason=data.get("reason"),
        effective_start=_parse_dt(data.get("effective_start")),
        effective_end=_parse_dt(data.get("effective_end")),
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return {"id": zone.id, "message": "创建成功"}


@router.put("/no-fly-zones/{zone_id}")
def update_no_fly_zone(zone_id: int, data: dict, db: Session = Depends(get_db)):
    """更新禁飞区"""
    zone = db.query(NoFlyZone).filter(NoFlyZone.id == zone_id).first()
    if not zone:
        raise HTTPException(404, "禁飞区不存在")
    for field in ("name", "altitude_min", "altitude_max", "reason"):
        if field in data:
            setattr(zone, field, data[field])
    if "effective_start" in data:
        zone.effective_start = _parse_dt(data["effective_start"])
    if "effective_end" in data:
        zone.effective_end = _parse_dt(data["effective_end"])
    if "coordinates" in data:
        zone.geometry = f"SRID=4326;{_coords_to_wkt(data['coordinates'])}"
    db.commit()
    return {"message": "更新成功"}


@router.delete("/no-fly-zones/{zone_id}")
def delete_no_fly_zone(zone_id: int, db: Session = Depends(get_db)):
    """删除禁飞区"""
    zone = db.query(NoFlyZone).filter(NoFlyZone.id == zone_id).first()
    if not zone:
        raise HTTPException(404, "禁飞区不存在")
    db.delete(zone)
    db.commit()
    return {"message": "删除成功"}


@router.get("/height-limit-zones")
def list_height_limit_zones(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """列出限高区（分页）"""
    query = db.query(HeightLimitZone)
    if name:
        query = query.filter(HeightLimitZone.name.ilike(f"%{name}%"))
    total = query.count()
    items = query.order_by(HeightLimitZone.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_hlzone(z) for z in items],
    }


@router.post("/height-limit-zones")
def create_height_limit_zone(data: dict, db: Session = Depends(get_db)):
    """新建限高区"""
    geom_wkt = _coords_to_wkt(data.get("coordinates", []))
    zone = HeightLimitZone(
        name=data.get("name"),
        geometry=f"SRID=4326;{geom_wkt}",
        max_altitude=data.get("max_altitude", 100),
        min_altitude=data.get("min_altitude", 0),
        reason=data.get("reason"),
        effective_start=_parse_dt(data.get("effective_start")),
        effective_end=_parse_dt(data.get("effective_end")),
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return {"id": zone.id, "message": "创建成功"}


@router.put("/height-limit-zones/{zone_id}")
def update_height_limit_zone(zone_id: int, data: dict, db: Session = Depends(get_db)):
    """更新限高区"""
    zone = db.query(HeightLimitZone).filter(HeightLimitZone.id == zone_id).first()
    if not zone:
        raise HTTPException(404, "限高区不存在")
    for field in ("name", "max_altitude", "min_altitude", "reason"):
        if field in data:
            setattr(zone, field, data[field])
    if "effective_start" in data:
        zone.effective_start = _parse_dt(data["effective_start"])
    if "effective_end" in data:
        zone.effective_end = _parse_dt(data["effective_end"])
    if "coordinates" in data:
        zone.geometry = f"SRID=4326;{_coords_to_wkt(data['coordinates'])}"
    db.commit()
    return {"message": "更新成功"}


@router.delete("/height-limit-zones/{zone_id}")
def delete_height_limit_zone(zone_id: int, db: Session = Depends(get_db)):
    """删除限高区"""
    zone = db.query(HeightLimitZone).filter(HeightLimitZone.id == zone_id).first()
    if not zone:
        raise HTTPException(404, "限高区不存在")
    db.delete(zone)
    db.commit()
    return {"message": "删除成功"}


# ──────────────────────────────────────────────────────────────
# 2.2 空域空间查询
# ──────────────────────────────────────────────────────────────

@router.get("/query/point")
def query_point_constraints(
    lng: float = Query(..., description="经度"),
    lat: float = Query(..., description="纬度"),
    db: Session = Depends(get_db)
):
    """
    2.2.1 点位约束查询
    判断指定坐标是否处于禁飞区或限高区，返回相关规则
    """
    point_wkt = f"SRID=4326;POINT({lng} {lat})"

    no_fly = db.query(NoFlyZone).filter(
        func.ST_Within(func.ST_GeomFromEWKT(point_wkt), NoFlyZone.geometry)
    ).all()

    height_limit = db.query(HeightLimitZone).filter(
        func.ST_Within(func.ST_GeomFromEWKT(point_wkt), HeightLimitZone.geometry)
    ).all()

    return {
        "lng": lng, "lat": lat,
        "in_no_fly_zone": len(no_fly) > 0,
        "no_fly_zones": [_serialize_zone(z) for z in no_fly],
        "in_height_limit_zone": len(height_limit) > 0,
        "height_limit_zones": [_serialize_hlzone(z) for z in height_limit],
        "flyable": len(no_fly) == 0,
        "max_altitude": min((z.max_altitude for z in height_limit), default=None),
    }


@router.get("/query/range")
def query_range_constraints(
    min_lng: float = Query(...), max_lng: float = Query(...),
    min_lat: float = Query(...), max_lat: float = Query(...),
    db: Session = Depends(get_db)
):
    """
    2.2.2 范围约束查询
    查询指定矩形范围内存在的限制区域
    """
    bbox_wkt = (
        f"SRID=4326;POLYGON(({min_lng} {min_lat},{max_lng} {min_lat},"
        f"{max_lng} {max_lat},{min_lng} {max_lat},{min_lng} {min_lat}))"
    )
    bbox_geom = func.ST_GeomFromEWKT(bbox_wkt)

    no_fly = db.query(NoFlyZone).filter(
        func.ST_Intersects(NoFlyZone.geometry, bbox_geom)
    ).all()
    height_limit = db.query(HeightLimitZone).filter(
        func.ST_Intersects(HeightLimitZone.geometry, bbox_geom)
    ).all()

    return {
        "no_fly_zones": [_serialize_zone(z) for z in no_fly],
        "height_limit_zones": [_serialize_hlzone(z) for z in height_limit],
        "total_constraints": len(no_fly) + len(height_limit),
    }


# ──────────────────────────────────────────────────────────────
# 2.3 航线合规审查
# ──────────────────────────────────────────────────────────────

@router.post("/compliance/check")
def check_route_compliance(data: dict, db: Session = Depends(get_db)):
    """
    2.3 航线合规审查
    检查航线是否穿越禁飞区、是否满足高度要求
    输入: { waypoints: [[lng,lat,alt], ...], task_time: "ISO datetime" }
    """
    waypoints = data.get("waypoints", [])
    task_time_str = data.get("task_time")
    task_time = _parse_dt(task_time_str)

    if len(waypoints) < 2:
        raise HTTPException(400, "至少需要2个航路点")

    violations = []
    warnings = []

    # 构造航线 LineString
    coords_str = ",".join(f"{p[0]} {p[1]}" for p in waypoints)
    line_wkt = f"SRID=4326;LINESTRING({coords_str})"
    line_geom = func.ST_GeomFromEWKT(line_wkt)

    # 2.3.1 区域穿越审查
    no_fly_zones = db.query(NoFlyZone).filter(
        func.ST_Intersects(NoFlyZone.geometry, line_geom)
    ).all()
    for zone in no_fly_zones:
        # 检查时间有效性
        if task_time and zone.effective_start and zone.effective_end:
            if zone.effective_start <= task_time <= zone.effective_end:
                violations.append({
                    "type": "no_fly_violation",
                    "zone_id": zone.id,
                    "zone_name": zone.name,
                    "description": f"航线穿越禁飞区「{zone.name}」",
                })
        else:
            violations.append({
                "type": "no_fly_violation",
                "zone_id": zone.id,
                "zone_name": zone.name,
                "description": f"航线穿越禁飞区「{zone.name}」",
            })

    # 2.3.2 飞行高度审查
    height_limit_zones = db.query(HeightLimitZone).filter(
        func.ST_Intersects(HeightLimitZone.geometry, line_geom)
    ).all()
    for zone in height_limit_zones:
        for wp in waypoints:
            wp_alt = wp[2] if len(wp) > 2 else 0
            if wp_alt > zone.max_altitude:
                warnings.append({
                    "type": "height_violation",
                    "zone_id": zone.id,
                    "zone_name": zone.name,
                    "description": f"航路点高度 {wp_alt}m 超过限高区「{zone.name}」限制 {zone.max_altitude}m",
                })

    compliant = len(violations) == 0
    return {
        "compliant": compliant,
        "violations": violations,
        "warnings": warnings,
        "summary": "合规" if compliant else f"存在 {len(violations)} 项违规",
    }


# ──────────────────────────────────────────────────────────────
# 2.4 空域资源统计
# ──────────────────────────────────────────────────────────────

@router.get("/stats")
def get_airspace_stats(db: Session = Depends(get_db)):
    """
    2.4 空域资源统计
    返回各类限制区域数量、总面积和类型占比
    """
    no_fly_count = db.query(func.count(NoFlyZone.id)).scalar()
    hl_count = db.query(func.count(HeightLimitZone.id)).scalar()

    # 计算面积（单位：平方公里）
    no_fly_area = db.execute(
        text("SELECT COALESCE(SUM(ST_Area(geometry::geography)/1e6), 0) FROM no_fly_zones")
    ).scalar() or 0
    hl_area = db.execute(
        text("SELECT COALESCE(SUM(ST_Area(geometry::geography)/1e6), 0) FROM height_limit_zones")
    ).scalar() or 0

    total_area = no_fly_area + hl_area

    return {
        "no_fly_zones": {
            "count": no_fly_count,
            "area_km2": round(no_fly_area, 3),
            "percent": round(no_fly_area / total_area * 100, 1) if total_area > 0 else 0,
        },
        "height_limit_zones": {
            "count": hl_count,
            "area_km2": round(hl_area, 3),
            "percent": round(hl_area / total_area * 100, 1) if total_area > 0 else 0,
        },
        "total": {
            "count": no_fly_count + hl_count,
            "area_km2": round(total_area, 3),
        },
    }


# ──────────────────────────────────────────────────────────────
# 内部工具函数
# ──────────────────────────────────────────────────────────────

def _serialize_zone(z: NoFlyZone) -> dict:
    return {
        "id": z.id,
        "name": z.name,
        "altitude_min": z.altitude_min,
        "altitude_max": z.altitude_max,
        "reason": z.reason,
        "effective_start": z.effective_start.isoformat() if z.effective_start else None,
        "effective_end": z.effective_end.isoformat() if z.effective_end else None,
        "created_at": z.created_at.isoformat() if z.created_at else None,
    }


def _serialize_hlzone(z: HeightLimitZone) -> dict:
    return {
        "id": z.id,
        "name": z.name,
        "max_altitude": z.max_altitude,
        "min_altitude": z.min_altitude,
        "reason": z.reason,
        "effective_start": z.effective_start.isoformat() if z.effective_start else None,
        "effective_end": z.effective_end.isoformat() if z.effective_end else None,
        "created_at": z.created_at.isoformat() if z.created_at else None,
    }


def _coords_to_wkt(coords: list) -> str:
    """将坐标列表转为 WKT POLYGON"""
    if not coords:
        return "POLYGON EMPTY"
    # 确保多边形闭合
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    pts = ",".join(f"{c[0]} {c[1]}" for c in coords)
    return f"POLYGON(({pts}))"


def _parse_dt(s) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None
