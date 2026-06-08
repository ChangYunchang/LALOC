"""
模拟航线种子数据
运行方式: cd backend && python seed_routes.py
"""
import sys
import os
import math

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models.routes import Route

# 确保表存在
Route.__table__.create(bind=engine, checkfirst=True)

db = SessionLocal()

# 如果已有数据则清空
existing = db.query(Route).count()
if existing > 0:
    db.execute(text("DELETE FROM routes"))
    db.commit()
    print(f"已清空 {existing} 条旧航线数据")

# ── 广州市模拟航线 ──────────────────────────────────────────

ROUTES = [
    {
        "name": "天河-海珠 急速配送线",
        "status": "active",
        "waypoints": [
            {"lng": 113.3280, "lat": 23.1290, "alt": 120, "name": "天河体育中心"},
            {"lng": 113.3190, "lat": 23.1180, "alt": 100, "name": "珠江新城"},
            {"lng": 113.3050, "lat": 23.1050, "alt": 80,  "name": "广州塔"},
            {"lng": 113.2800, "lat": 23.0850, "alt": 100, "name": "海珠客运站"},
        ],
    },
    {
        "name": "越秀-番禺 干线物流",
        "status": "active",
        "waypoints": [
            {"lng": 113.2650, "lat": 23.1380, "alt": 100, "name": "越秀公园"},
            {"lng": 113.2750, "lat": 23.1200, "alt": 120, "name": "海珠广场"},
            {"lng": 113.2900, "lat": 23.0900, "alt": 100, "name": "沥滘"},
            {"lng": 113.3200, "lat": 23.0500, "alt": 80,  "name": "番禺广场"},
            {"lng": 113.3500, "lat": 23.0200, "alt": 100, "name": "番禺市桥"},
        ],
    },
    {
        "name": "白云-黄埔 长距运输线",
        "status": "planned",
        "waypoints": [
            {"lng": 113.2680, "lat": 23.1650, "alt": 120, "name": "白云国际机场南"},
            {"lng": 113.2900, "lat": 23.1550, "alt": 100, "name": "白云新城"},
            {"lng": 113.3300, "lat": 23.1400, "alt": 100, "name": "天河智慧城"},
            {"lng": 113.3800, "lat": 23.1200, "alt": 120, "name": "大沙地"},
            {"lng": 113.4300, "lat": 23.1050, "alt": 100, "name": "黄埔开发区"},
            {"lng": 113.4600, "lat": 23.0900, "alt": 80,  "name": "黄埔新港"},
        ],
    },
    {
        "name": "珠江新城 环城巡检线",
        "status": "active",
        "waypoints": [
            {"lng": 113.3200, "lat": 23.1200, "alt": 80,  "name": "花城广场"},
            {"lng": 113.3300, "lat": 23.1250, "alt": 80,  "name": "广州大剧院"},
            {"lng": 113.3350, "lat": 23.1320, "alt": 80,  "name": "天河城"},
            {"lng": 113.3300, "lat": 23.1380, "alt": 80,  "name": "天河南"},
            {"lng": 113.3200, "lat": 23.1400, "alt": 80,  "name": "体育西路"},
            {"lng": 113.3120, "lat": 23.1350, "alt": 80,  "name": "珠江新城西"},
            {"lng": 113.3100, "lat": 23.1250, "alt": 80,  "name": "猎德"},
            {"lng": 113.3200, "lat": 23.1200, "alt": 80,  "name": "花城广场"},
        ],
    },
]


def haversine(lat1, lon1, lat2, lon2):
    """两点间距离(米)"""
    R = 6371000
    la1, la2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


import json
from geoalchemy2 import WKTElement

for route_data in ROUTES:
    wps = route_data["waypoints"]

    # 构建 LINESTRING WKT
    coord_strs = [f"{w['lng']} {w['lat']}" for w in wps]
    wkt = f"LINESTRING({', '.join(coord_strs)})"

    # 计算距离和时间
    total_dist = sum(
        haversine(wps[i]["lat"], wps[i]["lng"], wps[i + 1]["lat"], wps[i + 1]["lng"])
        for i in range(len(wps) - 1)
    )
    est_time = total_dist / 15.0  # 15 m/s

    # 使用 ORM 方式插入，避免 Windows GBK 编码问题
    route = Route(
        name=route_data["name"],
        route_line=WKTElement(wkt, srid=4326),
        waypoints=wps,
        total_distance=round(total_dist, 2),
        estimated_time=round(est_time, 2),
        status=route_data["status"],
    )
    db.add(route)

db.commit()

# 打印结果（用 ASCII 安全方式）
print(f"\n成功插入 {len(ROUTES)} 条模拟航线:")
for r in ROUTES:
    wps = r["waypoints"]
    dist = sum(
        haversine(wps[i]["lat"], wps[i]["lng"], wps[i + 1]["lat"], wps[i + 1]["lng"])
        for i in range(len(wps) - 1)
    )
    print(f"  - {r['name']}  ({dist / 1000:.1f} km, {r['status']})")

db.close()
