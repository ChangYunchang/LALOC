"""禁飞区和限高区 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.zone_service import ZoneService

router = APIRouter(prefix="/api/zones", tags=["区域管理"])


@router.get("/no-fly")
def get_no_fly_zones(db: Session = Depends(get_db)):
    """获取所有禁飞区（GeoJSON 格式）"""
    return ZoneService.get_all_no_fly_zones(db)


@router.get("/height-limit")
def get_height_limit_zones(db: Session = Depends(get_db)):
    """获取所有限高区（GeoJSON 格式）"""
    return ZoneService.get_all_height_limit_zones(db)


@router.get("/stats")
def get_zone_stats(db: Session = Depends(get_db)):
    """获取区域统计信息"""
    return ZoneService.get_zone_stats(db)


@router.get("/check-point")
def check_point(lng: float, lat: float, db: Session = Depends(get_db)):
    """检查一个点的约束信息"""
    in_no_fly = ZoneService.check_point_in_no_fly(db, lng, lat)
    height_limits = ZoneService.check_point_in_height_limit(db, lng, lat)
    return {
        "lng": lng,
        "lat": lat,
        "in_no_fly_zone": in_no_fly,
        "height_limits": height_limits,
    }
