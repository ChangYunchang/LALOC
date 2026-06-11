"""
种子数据脚本 - 为各子系统生成合理的模拟数据
运行: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
import random
import string

from app.database import SessionLocal, engine, Base
from app.models.logistics import Enterprise, DeliveryOrder, DeliveryTask, DeliveryStation, DroneResource
from app.models.safety import AnomalyEvent, SafetyRecord
from app.models.system import SystemUser, SystemParam, OperationLog, GISLayer

# 导入所有模型以确保表被创建
import app.models.zones
import app.models.routes
import app.models.buildings
import app.models.drones

Base.metadata.create_all(bind=engine)

db = SessionLocal()


def rand_no(prefix: str, n: int = 8) -> str:
    return prefix + "".join(random.choices(string.digits, k=n))


def rand_dt(days_back: int = 30) -> datetime:
    return datetime.now() - timedelta(days=random.randint(0, days_back),
                                      hours=random.randint(0, 23),
                                      minutes=random.randint(0, 59))


# ─── 企业 ───────────────────────────────────────────────────
ENTERPRISE_DATA = [
    {"code": "ENT001", "name": "顺丰低空科技(广州)有限公司", "contact_person": "张伟", "contact_phone": "13800001111",
     "address": "广州市天河区珠江新城", "license_no": "91440101MA1ABX0001", "status": "active", "api_key": "sk-001-abcdef"},
    {"code": "ENT002", "name": "京东物流无人机中心", "contact_person": "李娜", "contact_phone": "13900002222",
     "address": "广州市黄埔区科学城", "license_no": "91440101MA1ABX0002", "status": "active", "api_key": "sk-002-ghijkl"},
    {"code": "ENT003", "name": "菜鸟网络(广州)低空运营", "contact_person": "王芳", "contact_phone": "13700003333",
     "address": "广州市番禺区大学城", "license_no": "91440101MA1ABX0003", "status": "active", "api_key": "sk-003-mnopqr"},
    {"code": "ENT004", "name": "美团无人机配送(粤港澳)", "contact_person": "陈志远", "contact_phone": "13600004444",
     "address": "广州市越秀区北京路", "license_no": "91440101MA1ABX0004", "status": "suspended", "api_key": "sk-004-stuvwx"},
]

if db.query(Enterprise).count() == 0:
    for d in ENTERPRISE_DATA:
        db.add(Enterprise(**d))
    db.commit()
    print(f"✓ 企业: {len(ENTERPRISE_DATA)} 条")

enterprises = db.query(Enterprise).all()

# ─── 配送站 ───────────────────────────────────────────────────
STATION_LOCS = [
    (113.3303, 23.1355, "天河CBD配送站"),
    (113.2609, 23.0849, "海珠广场配送站"),
    (113.2705, 23.1286, "越秀花城配送站"),
    (113.3500, 23.1150, "珠江新城配送站"),
    (113.2732, 23.1977, "白云机场辅配站"),
    (113.4012, 23.0745, "黄埔科学城配送站"),
    (113.3860, 23.2150, "萝岗物流园配送站"),
    (113.1850, 23.0540, "番禺大学城配送站"),
]

if db.query(DeliveryStation).count() == 0:
    for i, (lng, lat, name) in enumerate(STATION_LOCS):
        eid = enterprises[i % len(enterprises)].id
        db.add(DeliveryStation(
            enterprise_id=eid, name=name, code=f"ST{i+1:03d}",
            address=f"广州市{name}", lng=lng, lat=lat, altitude=round(random.uniform(5, 30), 1),
            landing_capacity=random.choice([2, 4, 4, 6]),
            service_radius=round(random.uniform(3, 8), 1),
            status="active", pending_tasks=random.randint(0, 5),
        ))
    db.commit()
    print(f"✓ 配送站: {len(STATION_LOCS)} 条")

stations = db.query(DeliveryStation).all()

# ─── 无人机资源 ───────────────────────────────────────────────
DRONE_MODELS = [
    ("DJI FlyCart 30", 30, 28, 18),
    ("极飞P100", 50, 22, 24),
    ("大疆行业版T50", 40, 32, 26),
    ("亿航 216S", 35, 35, 30),
]

if db.query(DroneResource).count() == 0:
    drone_idx = 1
    for e in enterprises:
        for j in range(random.randint(3, 6)):
            model_info = random.choice(DRONE_MODELS)
            st = random.choice([s for s in stations if s.enterprise_id == e.id] or stations)
            db.add(DroneResource(
                enterprise_id=e.id,
                drone_no=f"UA-{e.code[-3:]}-{drone_idx:04d}",
                model=model_info[0],
                max_payload=model_info[1],
                max_range=model_info[2],
                max_endurance=model_info[3] * 60,  # 转为分钟
                battery_level=random.randint(40, 100),
                status=random.choices(["idle", "executing", "charging", "maintenance"],
                                       weights=[60, 20, 15, 5])[0],
                station_id=st.id,
            ))
            drone_idx += 1
    db.commit()
    print(f"✓ 无人机: {drone_idx - 1} 条")

drones = db.query(DroneResource).all()

# ─── 配送订单 ───────────────────────────────────────────────
ORDER_STATUSES = ["pending", "dispatched", "delivering", "completed", "completed", "completed", "cancelled"]
CARGO_TYPES = ["医疗器械", "食品生鲜", "文件快递", "电子产品", "药品", "日用品"]

if db.query(DeliveryOrder).count() == 0:
    for i in range(80):
        e = random.choice(enterprises)
        status = random.choice(ORDER_STATUSES)
        planned = rand_dt(30)
        base_lng, base_lat = 113.2644, 23.1291  # 广州中心
        db.add(DeliveryOrder(
            order_no=rand_no("ORD"),
            enterprise_id=e.id,
            cargo_type=random.choice(CARGO_TYPES),
            cargo_weight=round(random.uniform(0.5, 25), 1),
            sender_name=f"寄件人{i+1:03d}",
            sender_address=f"广州市寄件地址{i+1}",
            sender_lng=base_lng + random.uniform(-0.15, 0.15),
            sender_lat=base_lat + random.uniform(-0.10, 0.10),
            receiver_name=f"收件人{i+1:03d}",
            receiver_address=f"广州市收件地址{i+1}",
            receiver_lng=base_lng + random.uniform(-0.15, 0.15),
            receiver_lat=base_lat + random.uniform(-0.10, 0.10),
            planned_time=planned,
            status=status,
            abnormal_reason="天气原因延误" if status == "cancelled" else None,
            created_at=planned - timedelta(hours=random.randint(1, 48)),
        ))
    db.commit()
    print(f"✓ 配送订单: 80 条")

orders = db.query(DeliveryOrder).all()

# ─── 配送任务 ───────────────────────────────────────────────
TASK_STATUSES = ["pending", "assigned", "executing", "completed", "completed", "completed", "failed"]

if db.query(DeliveryTask).count() == 0:
    for i, order in enumerate(orders[:60]):
        st = random.choice(stations)
        dr_candidates = [d for d in drones if d.enterprise_id == order.enterprise_id]
        dr = random.choice(dr_candidates) if dr_candidates else None
        status = random.choice(TASK_STATUSES)
        start = order.planned_time
        end = start + timedelta(minutes=random.randint(15, 45)) if start else None
        db.add(DeliveryTask(
            task_no=rand_no("TASK"),
            order_id=order.id,
            enterprise_id=order.enterprise_id,
            station_id=st.id,
            drone_id=dr.id if dr and status in ("assigned", "executing", "completed") else None,
            planned_start=start,
            planned_end=end,
            actual_start=start if status in ("executing", "completed") else None,
            actual_end=end if status == "completed" else None,
            status=status,
            priority=random.randint(3, 8),
        ))
    db.commit()
    print(f"✓ 配送任务: 60 条")

# ─── 异常事件 ───────────────────────────────────────────────
EVENT_TYPES = ["boundary_violation", "route_conflict", "weather_anomaly", "comm_loss", "device_fault", "congestion"]
SEVERITIES = ["low", "medium", "medium", "high", "critical"]

if db.query(AnomalyEvent).count() == 0:
    base_lng, base_lat = 113.2644, 23.1291
    for i in range(40):
        e = random.choice(enterprises)
        dr = random.choice([d for d in drones if d.enterprise_id == e.id] or drones)
        occurred = rand_dt(60)
        status = random.choices(["open", "processing", "closed"], weights=[20, 30, 50])[0]
        severity = random.choice(SEVERITIES)
        db.add(AnomalyEvent(
            event_no=rand_no("EVT"),
            event_type=random.choice(EVENT_TYPES),
            severity=severity,
            enterprise_id=e.id,
            drone_id=dr.id,
            lng=base_lng + random.uniform(-0.15, 0.15),
            lat=base_lat + random.uniform(-0.10, 0.10),
            altitude=random.uniform(50, 300),
            description=f"发现{random.choice(['越界飞行', '通信中断', '设备异常', '气象告警', '拥堵预警'])}，无人机编号 {dr.drone_no}",
            status=status,
            handler="监管员" + str(random.randint(1, 5)) if status != "open" else None,
            handle_notes="已协调企业处置" if status == "closed" else None,
            occurred_at=occurred,
            closed_at=occurred + timedelta(hours=random.randint(1, 24)) if status == "closed" else None,
        ))
    db.commit()
    print(f"✓ 异常事件: 40 条")

# ─── 安全监管台账 ───────────────────────────────────────────
if db.query(SafetyRecord).count() == 0:
    events = db.query(AnomalyEvent).limit(20).all()
    for i, ev in enumerate(events):
        db.add(SafetyRecord(
            record_no=rand_no("REC"),
            record_type=random.choice(["event", "inspection", "violation"]),
            enterprise_id=ev.enterprise_id,
            event_id=ev.id,
            title=f"关于{ev.event_type}的监管记录",
            content=f"针对 {ev.description} 的处置情况记录",
            result="已整改" if ev.status == "closed" else "处置中",
            archived=1 if ev.status == "closed" and random.random() > 0.5 else 0,
            operator="管理员",
            record_time=ev.occurred_at + timedelta(hours=2),
        ))
    db.commit()
    print(f"✓ 安全台账: {len(events)} 条")

# ─── 系统用户 ───────────────────────────────────────────────
if db.query(SystemUser).count() == 0:
    users = [
        {"username": "admin", "real_name": "系统管理员", "email": "admin@laloc.gov.cn",
         "phone": "13800000001", "role": "admin", "status": "active"},
        {"username": "supervisor01", "real_name": "李监管", "email": "li@laloc.gov.cn",
         "phone": "13800000002", "role": "supervisor", "status": "active"},
        {"username": "operator01", "real_name": "张操作", "email": "zhang@laloc.gov.cn",
         "phone": "13800000003", "role": "operator", "status": "active"},
        {"username": "sf_user", "real_name": "顺丰业务员", "email": "user@sf.com",
         "phone": "13800000004", "role": "enterprise", "enterprise_id": 1, "status": "active"},
        {"username": "jd_user", "real_name": "京东业务员", "email": "user@jd.com",
         "phone": "13800000005", "role": "enterprise", "enterprise_id": 2, "status": "active"},
    ]
    for u in users:
        db.add(SystemUser(**u))
    db.commit()
    print(f"✓ 系统用户: {len(users)} 条")

# ─── 系统参数 ───────────────────────────────────────────────
if db.query(SystemParam).count() == 0:
    params = [
        # 适飞阈值
        ("flight_threshold", "max_wind_speed", "最大允许风速", "15", "m/s", "超过此风速不允许飞行"),
        ("flight_threshold", "min_visibility", "最小能见度", "1000", "米", "低于此能见度不允许飞行"),
        ("flight_threshold", "max_temperature", "最高飞行温度", "45", "℃", "高于此温度不允许飞行"),
        ("flight_threshold", "min_temperature", "最低飞行温度", "-10", "℃", "低于此温度不允许飞行"),
        ("flight_threshold", "min_battery", "最低起飞电量", "30", "%", "电量低于此值不允许执行任务"),
        # 规划参数
        ("planning", "default_cruise_altitude", "默认巡航高度", "120", "米", "标准配送巡航高度"),
        ("planning", "safety_margin", "安全余量", "10", "米", "建筑物和障碍物安全距离"),
        ("planning", "default_speed", "默认飞行速度", "15", "m/s", "默认配送飞行速度"),
        ("planning", "grid_resolution", "路径规划网格分辨率", "50", "米", "A*路径规划网格大小"),
        # 告警阈值
        ("alert", "congestion_threshold", "拥堵告警阈值", "5", "任务/km²", "单位面积任务数超过此值触发拥堵告警"),
        ("alert", "conflict_distance", "冲突检测距离", "100", "米", "水平安全间距阈值"),
        ("alert", "conflict_altitude_diff", "冲突高度差阈值", "30", "米", "垂直安全间距阈值"),
        # 外部服务
        ("external_service", "weather_refresh_interval", "气象数据刷新间隔", "300", "秒", "气象缓存刷新周期"),
        ("external_service", "amap_timeout", "高德API超时", "10000", "毫秒", "高德地图API请求超时"),
    ]
    for category, key, name, value, unit, desc in params:
        db.add(SystemParam(category=category, param_key=key, param_name=name,
                           param_value=value, unit=unit, description=desc))
    db.commit()
    print(f"✓ 系统参数: {len(params)} 条")

# ─── GIS 图层 ───────────────────────────────────────────────
if db.query(GISLayer).count() == 0:
    layers = [
        ("底图-街道", "base_street", "base", "高德地图街道底图", True, 1),
        ("底图-卫星", "base_satellite", "base", "高德地图卫星底图", False, 2),
        ("禁飞区图层", "zone_no_fly", "zone", "PostGIS禁飞区数据", True, 10),
        ("限高区图层", "zone_height_limit", "zone", "PostGIS限高区数据", True, 11),
        ("航线图层", "route_all", "route", "系统内所有航线数据", True, 20),
        ("配送站图层", "poi_station", "poi", "配送站位置数据", True, 30),
        ("建筑物三维图层", "building_3d", "custom", "OSM三维建筑数据", True, 40),
        ("无人机实时位置", "drone_realtime", "custom", "无人机实时位置数据", True, 50),
    ]
    for name, code, ltype, source, pub, order in layers:
        db.add(GISLayer(name=name, code=code, layer_type=ltype, data_source=source,
                        published=pub, sort_order=order))
    db.commit()
    print(f"✓ GIS图层: {len(layers)} 条")

# ─── 操作日志示例 ───────────────────────────────────────────
if db.query(OperationLog).count() == 0:
    log_actions = [
        ("admin", "系统管理", "查询用户列表", "SystemUser", None),
        ("supervisor01", "空域管理", "新建禁飞区", "NoFlyZone", "12"),
        ("operator01", "物流运营", "创建配送任务", "DeliveryTask", "101"),
        ("sf_user", "物流运营", "提交配送订单", "DeliveryOrder", "ORD00012345"),
        ("supervisor01", "安全监管", "处置异常事件", "AnomalyEvent", "15"),
        ("admin", "系统管理", "修改系统参数", "SystemParam", "max_wind_speed"),
    ]
    for username, module, action, rtype, rid in log_actions:
        db.add(OperationLog(
            username=username, module=module, action=action,
            resource_type=rtype, resource_id=rid,
            detail=f"{username} 执行了 {action}",
            ip_address=f"192.168.1.{random.randint(10, 100)}",
            result="success",
            created_at=rand_dt(7),
        ))
    db.commit()
    print(f"✓ 操作日志: {len(log_actions)} 条")

db.close()
print("\n✅ 种子数据写入完成！")
