"""天气查询 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import weather_service

router = APIRouter(prefix="/api/weather", tags=["天气查询"])


@router.get("/live")
async def get_live_weather(city: str = "广州", db: Session = Depends(get_db)):
    """获取实时天气"""
    try:
        return await weather_service.get_live_weather(db, city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取天气失败: {str(e)}")


@router.get("/forecast")
async def get_weather_forecast(city: str = "广州", db: Session = Depends(get_db)):
    """获取天气预报"""
    try:
        return await weather_service.get_weather_forecast(db, city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取天气预报失败: {str(e)}")


@router.get("/flyable")
async def check_flyable(city: str = "广州", db: Session = Depends(get_db)):
    """检查当前天气是否适合飞行"""
    try:
        weather = await weather_service.get_live_weather(db, city)
        is_flyable, warnings = weather_service.is_weather_flyable(weather)
        return {
            "is_flyable": is_flyable,
            "warnings": warnings,
            "weather": weather,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查飞行条件失败: {str(e)}")
