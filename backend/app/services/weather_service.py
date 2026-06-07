"""天气查询服务 - 代理高德天气 API"""
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.drones import WeatherRecord
from app.config import get_settings

settings = get_settings()

# 高德天气 API 地址
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# 广州市编码
GUANGZHOU_AD_CODE = "440100"


async def fetch_weather_from_amap(city: str = GUANGZHOU_AD_CODE, extensions: str = "all") -> dict:
    """从高德 API 获取天气数据"""
    params = {
        "city": city,
        "key": settings.AMAP_WEB_SERVICE_KEY,
        "extensions": extensions,  # base=实况, all=预报
        "output": "JSON",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(AMAP_WEATHER_URL, params=params, timeout=10.0)
        data = response.json()

    if data.get("status") != "1":
        raise Exception(f"高德天气 API 调用失败: {data.get('info', '未知错误')}")

    return data


async def get_live_weather(db: Session, city: str = "广州") -> dict:
    """获取实时天气（优先从缓存获取，超过30分钟重新请求）"""
    # 查找最近的缓存记录
    latest = (
        db.query(WeatherRecord)
        .filter(WeatherRecord.city == city)
        .order_by(WeatherRecord.created_at.desc())
        .first()
    )

    # 如果缓存不超过30分钟，直接返回
    if latest:
        age = (datetime.now() - latest.created_at).total_seconds()
        if age < 1800:  # 30分钟
            return {
                "city": latest.city,
                "temperature": latest.temperature,
                "humidity": latest.humidity,
                "wind_direction": latest.wind_direction,
                "wind_power": latest.wind_power,
                "weather": latest.weather_desc,
                "report_time": latest.report_time.isoformat() if latest.report_time else None,
                "cached": True,
            }

    # 从高德 API 获取实时天气
    try:
        data = await fetch_weather_from_amap(city=GUANGZHOU_AD_CODE, extensions="base")
        lives = data.get("live", [])
        if not lives:
            raise Exception("无实时天气数据")

        live = lives[0]

        # 保存到数据库缓存
        record = WeatherRecord(
            city=city,
            temperature=float(live.get("temperature", 0)),
            humidity=float(live.get("humidity", 0)),
            wind_direction=live.get("winddirection", ""),
            wind_power=live.get("windpower", ""),
            weather_desc=live.get("weather", ""),
            report_time=datetime.now(),
        )
        db.add(record)
        db.commit()

        return {
            "city": city,
            "temperature": float(live.get("temperature", 0)),
            "humidity": float(live.get("humidity", 0)),
            "wind_direction": live.get("winddirection", ""),
            "wind_power": live.get("windpower", ""),
            "weather": live.get("weather", ""),
            "report_time": datetime.now().isoformat(),
            "cached": False,
        }
    except Exception as e:
        # 如果 API 调用失败，返回缓存数据（如果有的话）
        if latest:
            return {
                "city": latest.city,
                "temperature": latest.temperature,
                "humidity": latest.humidity,
                "wind_direction": latest.wind_direction,
                "wind_power": latest.wind_power,
                "weather": latest.weather_desc,
                "report_time": latest.report_time.isoformat() if latest.report_time else None,
                "cached": True,
                "warning": f"API调用失败，使用缓存数据: {str(e)}",
            }
        raise


async def get_weather_forecast(db: Session, city: str = "广州") -> dict:
    """获取天气预报"""
    try:
        data = await fetch_weather_from_amap(city=GUANGZHOU_AD_CODE, extensions="all")
        forecasts = data.get("forecasts", [])
        if not forecasts:
            raise Exception("无天气预报数据")

        forecast = forecasts[0]
        return {
            "city": forecast.get("city", city),
            "province": forecast.get("province", ""),
            "report_time": forecast.get("reporttime", ""),
            "casts": [
                {
                    "date": cast.get("date", ""),
                    "day_weather": cast.get("dayweather", ""),
                    "night_weather": cast.get("nightweather", ""),
                    "day_temp": cast.get("daytemp", ""),
                    "night_temp": cast.get("nighttemp", ""),
                    "day_wind": cast.get("daywind", ""),
                    "night_wind": cast.get("nightwind", ""),
                    "day_power": cast.get("daypower", ""),
                    "night_power": cast.get("nightpower", ""),
                }
                for cast in forecast.get("casts", [])
            ],
        }
    except Exception as e:
        raise


def is_weather_flyable(weather: dict) -> tuple[bool, list[str]]:
    """判断天气是否适合飞行，返回 (是否可飞, 警告列表)"""
    warnings = []
    is_flyable = True

    temp = weather.get("temperature", 20)
    wind_power = weather.get("wind_power", "0")
    weather_desc = weather.get("weather", "")

    # 温度检查
    if temp < -10:
        warnings.append(f"温度过低({temp}℃)，不建议飞行")
        is_flyable = False
    elif temp > 45:
        warnings.append(f"温度过高({temp}℃)，不建议飞行")
        is_flyable = False

    # 风力检查（高德返回的是风力等级字符串如"3"）
    try:
        wind_level = int(wind_power.replace("级", ""))
        if wind_level >= 6:
            warnings.append(f"风力{wind_power}级，不建议飞行")
            is_flyable = False
        elif wind_level >= 4:
            warnings.append(f"风力{wind_power}级，请注意飞行安全")
    except (ValueError, AttributeError):
        pass

    # 天气状况检查
    bad_weather = ["暴雨", "大雨", "雷阵雨", "冰雹", "暴雪", "大雪", "台风", "沙尘暴", "雾", "霾"]
    for bw in bad_weather:
        if bw in weather_desc:
            warnings.append(f"当前天气'{weather_desc}'，不建议飞行")
            is_flyable = False
            break

    return is_flyable, warnings
