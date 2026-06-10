"""航线管理 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models.routes import Route as RouteModel
from app.schemas.routes import RouteCreate, RouteResponse
from app.services.astar import compute_altitude_profile
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/routes", tags=["航线管理"])


@router.get("/")
def get_all_routes(db: Session = Depends(get_db)):
    """获取所有航线"""
    routes = db.query(RouteModel).all()
    result = []
    for route in routes:
        # 获取 GeoJSON
        if route.route_line:
            geo_result = db.execute(
                text("SELECT ST_AsGeoJSON(route_line) FROM routes WHERE id = :id"),
                {"id": route.id}
            ).fetchone()
            line_json = json.loads(geo_result[0]) if geo_result else None
        else:
            line_json = None

        # 高度剖面（跳过建筑物查询以加速列表接口，详情接口才计算）
        altitude_profile = None

        result.append({
            "id": route.id,
            "name": route.name,
            "route_line": line_json,
            "waypoints": route.waypoints,
            "total_distance": route.total_distance,
            "estimated_time": route.estimated_time,
            "status": route.status,
            "altitude_profile": altitude_profile,
            "created_at": route.created_at.isoformat() if route.created_at else None,
        })
    return result


@router.get("/{route_id}")
def get_route(route_id: int, db: Session = Depends(get_db)):
    """获取单条航线详情"""
    route = db.query(RouteModel).filter(RouteModel.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="航线不存在")

    if route.route_line:
        geo_result = db.execute(
            text("SELECT ST_AsGeoJSON(route_line) FROM routes WHERE id = :id"),
            {"id": route.id}
        ).fetchone()
        line_json = json.loads(geo_result[0]) if geo_result else None
    else:
        line_json = None

    # 高度剖面
    altitude_profile = None

    return {
        "id": route.id,
        "name": route.name,
        "route_line": line_json,
        "waypoints": route.waypoints,
        "total_distance": route.total_distance,
        "estimated_time": route.estimated_time,
        "status": route.status,
        "altitude_profile": altitude_profile,
        "created_at": route.created_at.isoformat() if route.created_at else None,
    }


@router.post("/")
def create_route(route_data: RouteCreate, db: Session = Depends(get_db)):
    """创建新航线"""
    if not route_data.waypoints or len(route_data.waypoints) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个途经点")

    # 构建航线几何（LineString）
    coords = [f"{w.lng} {w.lat}" for w in route_data.waypoints]
    wkt = f"LINESTRING({', '.join(coords)})"

    waypoints_json = [
        {"lng": w.lng, "lat": w.lat, "alt": w.alt or 100, "name": w.name}
        for w in route_data.waypoints
    ]

    # 计算总距离（简单累加）
    total_distance = 0
    for i in range(len(route_data.waypoints) - 1):
        w1 = route_data.waypoints[i]
        w2 = route_data.waypoints[i + 1]
        import math
        R = 6371000
        lat1, lat2 = math.radians(w1.lat), math.radians(w2.lat)
        dlat = math.radians(w2.lat - w1.lat)
        dlng = math.radians(w2.lng - w1.lng)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        total_distance += R * c

    estimated_time = total_distance / 15.0  # 默认15m/s

    # 插入数据库
    db.execute(
        text("""
            INSERT INTO routes (name, route_line, waypoints, total_distance, estimated_time, status)
            VALUES (:name, ST_SetSRID(ST_GeomFromText(:wkt), 4326), :waypoints, :distance, :time, 'planned')
        """),
        {
            "name": route_data.name or f"航线-{db.query(RouteModel).count() + 1}",
            "wkt": wkt,
            "waypoints": json.dumps(waypoints_json),
            "distance": round(total_distance, 2),
            "time": round(estimated_time, 2),
        }
    )
    db.commit()

    return {"message": "航线创建成功", "total_distance": round(total_distance, 2)}
