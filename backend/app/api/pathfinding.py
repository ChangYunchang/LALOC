"""路径规划 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.pathfinding import PathPlanRequest, PathPlanResponse
from app.services import astar

router = APIRouter(prefix="/api/pathfinding", tags=["路径规划"])


@router.post("/plan")
def plan_path(request: PathPlanRequest, db: Session = Depends(get_db)):
    """
    智能路径规划

    考虑禁飞区、限高区约束，返回最优路径
    """
    try:
        waypoints = []
        if request.waypoints:
            waypoints = [(w.lng, w.lat) for w in request.waypoints]

        result = astar.plan_path(
            db=db,
            start_lng=request.start.lng,
            start_lat=request.start.lat,
            end_lng=request.end.lng,
            end_lat=request.end.lat,
            waypoints=waypoints if waypoints else None,
            cell_size_meters=100,
            drone_speed=request.drone_speed or 15.0,
            cruise_alt=request.cruise_alt or 100.0,
            safety_margin=request.safety_margin or 50.0,
            avoid_buildings=request.avoid_buildings if request.avoid_buildings is not None else True,
            avoid_no_fly=request.avoid_no_fly if request.avoid_no_fly is not None else True,
            avoid_height_limit=request.avoid_height_limit if request.avoid_height_limit is not None else True,
            consider_weather=request.consider_weather,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"路径规划失败: {str(e)}")
