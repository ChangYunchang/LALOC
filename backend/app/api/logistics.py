"""
物流运营管理子系统 API
提供企业、订单、任务、配送站、无人机资源的 CRUD 和调度接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.logistics import Enterprise, DeliveryOrder, DeliveryTask, DeliveryStation, DroneResource

router = APIRouter(prefix="/api/logistics", tags=["物流运营管理"])


# ──────────────── 企业管理 ────────────────

@router.get("/enterprises")
def list_enterprises(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    name: Optional[str] = None, status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Enterprise)
    if name:
        q = q.filter(Enterprise.name.ilike(f"%{name}%"))
    if status:
        q = q.filter(Enterprise.status == status)
    total = q.count()
    items = q.order_by(Enterprise.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_e(e) for e in items]}


@router.get("/enterprises/{eid}")
def get_enterprise(eid: int, db: Session = Depends(get_db)):
    e = db.query(Enterprise).filter(Enterprise.id == eid).first()
    if not e:
        raise HTTPException(404, "企业不存在")
    return _e(e)


@router.post("/enterprises")
def create_enterprise(data: dict, db: Session = Depends(get_db)):
    e = Enterprise(**{k: v for k, v in data.items() if k in Enterprise.__table__.columns.keys()})
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"id": e.id, "message": "创建成功"}


@router.put("/enterprises/{eid}")
def update_enterprise(eid: int, data: dict, db: Session = Depends(get_db)):
    e = db.query(Enterprise).filter(Enterprise.id == eid).first()
    if not e:
        raise HTTPException(404, "企业不存在")
    for k, v in data.items():
        if hasattr(e, k):
            setattr(e, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/enterprises/{eid}")
def delete_enterprise(eid: int, db: Session = Depends(get_db)):
    e = db.query(Enterprise).filter(Enterprise.id == eid).first()
    if not e:
        raise HTTPException(404, "企业不存在")
    db.delete(e)
    db.commit()
    return {"message": "删除成功"}


# ──────────────── 配送订单管理 ────────────────

@router.get("/orders")
def list_orders(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    order_no: Optional[str] = None,
    enterprise_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(DeliveryOrder)
    if order_no:
        q = q.filter(DeliveryOrder.order_no.ilike(f"%{order_no}%"))
    if enterprise_id:
        q = q.filter(DeliveryOrder.enterprise_id == enterprise_id)
    if status:
        q = q.filter(DeliveryOrder.status == status)
    total = q.count()
    items = q.order_by(DeliveryOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_o(o) for o in items]}


@router.get("/orders/stats")
def order_stats(db: Session = Depends(get_db)):
    """订单状态统计"""
    rows = db.query(DeliveryOrder.status, func.count(DeliveryOrder.id)).group_by(DeliveryOrder.status).all()
    return {r[0]: r[1] for r in rows}


@router.post("/orders")
def create_order(data: dict, db: Session = Depends(get_db)):
    import random, string
    data.setdefault("order_no", "ORD" + "".join(random.choices(string.digits, k=10)))
    allowed = {c.key for c in DeliveryOrder.__table__.columns}
    o = DeliveryOrder(**{k: v for k, v in data.items() if k in allowed})
    db.add(o)
    db.commit()
    db.refresh(o)
    return {"id": o.id, "order_no": o.order_no, "message": "创建成功"}


@router.put("/orders/{oid}")
def update_order(oid: int, data: dict, db: Session = Depends(get_db)):
    o = db.query(DeliveryOrder).filter(DeliveryOrder.id == oid).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    for k, v in data.items():
        if hasattr(o, k) and k not in ("id", "order_no"):
            setattr(o, k, v)
    db.commit()
    return {"message": "更新成功"}


# ──────────────── 配送任务管理 ────────────────

@router.get("/tasks")
def list_tasks(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    enterprise_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(DeliveryTask)
    if enterprise_id:
        q = q.filter(DeliveryTask.enterprise_id == enterprise_id)
    if status:
        q = q.filter(DeliveryTask.status == status)
    total = q.count()
    items = q.order_by(DeliveryTask.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_t(t) for t in items]}


@router.post("/tasks")
def create_task(data: dict, db: Session = Depends(get_db)):
    import random, string
    data.setdefault("task_no", "TASK" + "".join(random.choices(string.digits, k=8)))
    allowed = {c.key for c in DeliveryTask.__table__.columns}
    t = DeliveryTask(**{k: v for k, v in data.items() if k in allowed})
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "task_no": t.task_no, "message": "创建成功"}


@router.put("/tasks/{tid}")
def update_task(tid: int, data: dict, db: Session = Depends(get_db)):
    t = db.query(DeliveryTask).filter(DeliveryTask.id == tid).first()
    if not t:
        raise HTTPException(404, "任务不存在")
    for k, v in data.items():
        if hasattr(t, k) and k not in ("id",):
            setattr(t, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/tasks/{tid}")
def delete_task(tid: int, db: Session = Depends(get_db)):
    t = db.query(DeliveryTask).filter(DeliveryTask.id == tid).first()
    if not t:
        raise HTTPException(404, "任务不存在")
    db.delete(t)
    db.commit()
    return {"message": "删除成功"}


# ──────────────── 配送站管理 ────────────────

@router.get("/stations")
def list_stations(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    name: Optional[str] = None,
    enterprise_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(DeliveryStation)
    if name:
        q = q.filter(DeliveryStation.name.ilike(f"%{name}%"))
    if enterprise_id:
        q = q.filter(DeliveryStation.enterprise_id == enterprise_id)
    if status:
        q = q.filter(DeliveryStation.status == status)
    total = q.count()
    items = q.order_by(DeliveryStation.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_s(s) for s in items]}


@router.post("/stations")
def create_station(data: dict, db: Session = Depends(get_db)):
    allowed = {c.key for c in DeliveryStation.__table__.columns}
    s = DeliveryStation(**{k: v for k, v in data.items() if k in allowed})
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "message": "创建成功"}


@router.put("/stations/{sid}")
def update_station(sid: int, data: dict, db: Session = Depends(get_db)):
    s = db.query(DeliveryStation).filter(DeliveryStation.id == sid).first()
    if not s:
        raise HTTPException(404, "配送站不存在")
    for k, v in data.items():
        if hasattr(s, k) and k != "id":
            setattr(s, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/stations/{sid}")
def delete_station(sid: int, db: Session = Depends(get_db)):
    s = db.query(DeliveryStation).filter(DeliveryStation.id == sid).first()
    if not s:
        raise HTTPException(404, "配送站不存在")
    db.delete(s)
    db.commit()
    return {"message": "删除成功"}


# ──────────────── 无人机资源管理 ────────────────

@router.get("/drones")
def list_drones(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    enterprise_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(DroneResource)
    if enterprise_id:
        q = q.filter(DroneResource.enterprise_id == enterprise_id)
    if status:
        q = q.filter(DroneResource.status == status)
    total = q.count()
    items = q.order_by(DroneResource.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_d(dr) for dr in items]}


@router.post("/drones")
def create_drone(data: dict, db: Session = Depends(get_db)):
    allowed = {c.key for c in DroneResource.__table__.columns}
    dr = DroneResource(**{k: v for k, v in data.items() if k in allowed})
    db.add(dr)
    db.commit()
    db.refresh(dr)
    return {"id": dr.id, "message": "创建成功"}


@router.put("/drones/{did}")
def update_drone(did: int, data: dict, db: Session = Depends(get_db)):
    dr = db.query(DroneResource).filter(DroneResource.id == did).first()
    if not dr:
        raise HTTPException(404, "无人机不存在")
    for k, v in data.items():
        if hasattr(dr, k) and k != "id":
            setattr(dr, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/drones/{did}")
def delete_drone(did: int, db: Session = Depends(get_db)):
    dr = db.query(DroneResource).filter(DroneResource.id == did).first()
    if not dr:
        raise HTTPException(404, "无人机不存在")
    db.delete(dr)
    db.commit()
    return {"message": "删除成功"}


# ──────────────── 5.7 无人机任务调度 ────────────────

@router.post("/scheduling/match")
def match_drones_for_task(data: dict, db: Session = Depends(get_db)):
    """
    5.7.1 任务匹配：根据任务需求（载重、企业）筛选适合的空闲无人机
    输入: { enterprise_id, cargo_weight, station_id? }
    """
    enterprise_id = data.get("enterprise_id")
    cargo_weight = data.get("cargo_weight", 0)

    q = db.query(DroneResource).filter(
        DroneResource.status == "idle",
        DroneResource.enterprise_id == enterprise_id,
        DroneResource.max_payload >= cargo_weight,
        DroneResource.battery_level >= 30,
    )
    drones = q.all()
    return {"matched_drones": [_d(dr) for dr in drones]}


@router.post("/scheduling/assign")
def assign_drone_to_task(data: dict, db: Session = Depends(get_db)):
    """5.7.2 无人机分配：为配送任务分配指定无人机"""
    task_id = data.get("task_id")
    drone_id = data.get("drone_id")

    task = db.query(DeliveryTask).filter(DeliveryTask.id == task_id).first()
    drone = db.query(DroneResource).filter(DroneResource.id == drone_id).first()

    if not task:
        raise HTTPException(404, "任务不存在")
    if not drone:
        raise HTTPException(404, "无人机不存在")
    if drone.status != "idle":
        raise HTTPException(400, f"无人机状态为 {drone.status}，不可分配")

    task.drone_id = drone_id
    task.status = "assigned"
    drone.status = "executing"
    drone.current_task_id = task_id
    db.commit()
    return {"message": "分配成功"}


@router.post("/scheduling/control")
def control_task_execution(data: dict, db: Session = Depends(get_db)):
    """5.7.3 执行控制：开始/暂停/继续/结束任务"""
    task_id = data.get("task_id")
    action = data.get("action")  # start/pause/resume/complete/cancel

    task = db.query(DeliveryTask).filter(DeliveryTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    status_map = {
        "start": "executing",
        "pause": "assigned",
        "resume": "executing",
        "complete": "completed",
        "cancel": "cancelled",
    }
    if action not in status_map:
        raise HTTPException(400, "无效操作")

    task.status = status_map[action]
    if action == "start":
        task.actual_start = datetime.now()
    elif action in ("complete", "cancel"):
        task.actual_end = datetime.now()
        if task.drone_id:
            drone = db.query(DroneResource).filter(DroneResource.id == task.drone_id).first()
            if drone:
                drone.status = "idle"
                drone.current_task_id = None
    db.commit()
    return {"message": f"操作 {action} 执行成功", "new_status": task.status}


# ──────────────── 序列化工具 ────────────────

def _e(e: Enterprise) -> dict:
    return {
        "id": e.id, "code": e.code, "name": e.name,
        "contact_person": e.contact_person, "contact_phone": e.contact_phone,
        "address": e.address, "license_no": e.license_no,
        "status": e.status, "api_key": e.api_key,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _o(o: DeliveryOrder) -> dict:
    return {
        "id": o.id, "order_no": o.order_no, "enterprise_id": o.enterprise_id,
        "cargo_type": o.cargo_type, "cargo_weight": o.cargo_weight,
        "sender_name": o.sender_name, "sender_address": o.sender_address,
        "sender_lng": o.sender_lng, "sender_lat": o.sender_lat,
        "receiver_name": o.receiver_name, "receiver_address": o.receiver_address,
        "receiver_lng": o.receiver_lng, "receiver_lat": o.receiver_lat,
        "planned_time": o.planned_time.isoformat() if o.planned_time else None,
        "status": o.status, "abnormal_reason": o.abnormal_reason,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def _t(t: DeliveryTask) -> dict:
    return {
        "id": t.id, "task_no": t.task_no, "order_id": t.order_id,
        "enterprise_id": t.enterprise_id, "station_id": t.station_id,
        "drone_id": t.drone_id, "route_id": t.route_id,
        "planned_start": t.planned_start.isoformat() if t.planned_start else None,
        "planned_end": t.planned_end.isoformat() if t.planned_end else None,
        "actual_start": t.actual_start.isoformat() if t.actual_start else None,
        "actual_end": t.actual_end.isoformat() if t.actual_end else None,
        "status": t.status, "priority": t.priority, "notes": t.notes,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _s(s: DeliveryStation) -> dict:
    return {
        "id": s.id, "enterprise_id": s.enterprise_id,
        "name": s.name, "code": s.code, "address": s.address,
        "lng": s.lng, "lat": s.lat, "altitude": s.altitude,
        "landing_capacity": s.landing_capacity, "service_radius": s.service_radius,
        "status": s.status, "pending_tasks": s.pending_tasks,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _d(dr: DroneResource) -> dict:
    return {
        "id": dr.id, "enterprise_id": dr.enterprise_id,
        "drone_no": dr.drone_no, "model": dr.model,
        "max_payload": dr.max_payload, "max_range": dr.max_range,
        "max_endurance": dr.max_endurance, "battery_level": dr.battery_level,
        "status": dr.status, "current_task_id": dr.current_task_id,
        "station_id": dr.station_id,
        "created_at": dr.created_at.isoformat() if dr.created_at else None,
    }
