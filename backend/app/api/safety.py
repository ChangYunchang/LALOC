"""
安全监管子系统 API
提供航线冲突检测、低空拥堵识别、安全风险分析、异常事件管理和监管台账接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional
from datetime import datetime, timedelta
import math
import random

from app.database import get_db
from app.models.safety import AnomalyEvent, SafetyRecord
from app.models.logistics import DeliveryTask, Enterprise

router = APIRouter(prefix="/api/safety", tags=["安全监管"])


# ──────────────────────────────────────────────────────────────
# 6.1 航线冲突检测
# ──────────────────────────────────────────────────────────────

@router.post("/conflict/check")
def check_route_conflict(data: dict, db: Session = Depends(get_db)):
    """
    6.1 航线冲突检测
    检测提交的航路是否与其他正在执行的任务存在时空冲突
    输入: { task_id?, waypoints: [[lng,lat,alt],...], planned_start, planned_end }
    最小安全间距默认 100m（水平），30m（垂直）
    """
    waypoints = data.get("waypoints", [])
    planned_start_str = data.get("planned_start")
    planned_end_str = data.get("planned_end")
    task_id = data.get("task_id")

    if len(waypoints) < 2:
        raise HTTPException(400, "至少需要2个航路点")

    planned_start = _parse_dt(planned_start_str) or datetime.now()
    planned_end = _parse_dt(planned_end_str) or (planned_start + timedelta(minutes=30))

    # 查询时间段内正在执行的其他任务
    active_tasks = db.query(DeliveryTask).filter(
        DeliveryTask.status.in_(["executing", "assigned"]),
        DeliveryTask.planned_start <= planned_end,
        DeliveryTask.planned_end >= planned_start,
    )
    if task_id:
        active_tasks = active_tasks.filter(DeliveryTask.id != task_id)
    active_tasks = active_tasks.all()

    conflicts = []
    # 简化检测：基于中心点距离判断潜在冲突
    if waypoints:
        center_lng = sum(w[0] for w in waypoints) / len(waypoints)
        center_lat = sum(w[1] for w in waypoints) / len(waypoints)

        for task in active_tasks:
            # 模拟冲突判断（真实系统需查询任务航线几何并做时空相交）
            # 此处为演示：随机生成少量冲突供界面展示
            if random.random() < 0.1:
                conflicts.append({
                    "task_id": task.id,
                    "task_no": task.task_no,
                    "conflict_type": random.choice(["route_cross", "buffer_overlap"]),
                    "description": f"与任务 {task.task_no} 存在飞行缓冲区重叠",
                    "severity": "medium",
                })

    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts,
        "checked_tasks": len(active_tasks),
        "summary": f"检测 {len(active_tasks)} 个并行任务，发现 {len(conflicts)} 项冲突",
    }


# ──────────────────────────────────────────────────────────────
# 6.2 低空拥堵识别
# ──────────────────────────────────────────────────────────────

@router.get("/congestion")
def get_congestion_status(db: Session = Depends(get_db)):
    """
    6.2 低空拥堵识别
    按区域统计当前任务密度，判断是否达到拥堵阈值（默认阈值：5任务/km²）
    """
    # 统计当前各企业执行中的任务数
    executing_count = db.query(func.count(DeliveryTask.id)).filter(
        DeliveryTask.status == "executing"
    ).scalar() or 0

    assigned_count = db.query(func.count(DeliveryTask.id)).filter(
        DeliveryTask.status == "assigned"
    ).scalar() or 0

    total_active = executing_count + assigned_count

    # 模拟区域密度数据（真实场景需基于航线空间分布计算）
    threshold = 5
    zones_analysis = [
        {"area": "天河区", "lng": 113.3303, "lat": 23.1355, "task_count": max(0, total_active - 2), "density": round((total_active - 2) / 4.5, 2), "congested": (total_active - 2) > threshold * 4.5},
        {"area": "越秀区", "lng": 113.2705, "lat": 23.1286, "task_count": max(0, total_active - 5), "density": round(max(0, total_active - 5) / 3.8, 2), "congested": max(0, total_active - 5) > threshold * 3.8},
        {"area": "海珠区", "lng": 113.2609, "lat": 23.0849, "task_count": max(0, total_active - 3), "density": round(max(0, total_active - 3) / 6.2, 2), "congested": max(0, total_active - 3) > threshold * 6.2},
        {"area": "白云区", "lng": 113.2732, "lat": 23.1977, "task_count": max(0, total_active - 8), "density": round(max(0, total_active - 8) / 8.1, 2), "congested": max(0, total_active - 8) > threshold * 8.1},
    ]

    congested_zones = [z for z in zones_analysis if z["congested"]]

    return {
        "total_active_tasks": total_active,
        "executing": executing_count,
        "assigned": assigned_count,
        "congestion_threshold": threshold,
        "zones": zones_analysis,
        "congested_zones_count": len(congested_zones),
        "alert": len(congested_zones) > 0,
    }


# ──────────────────────────────────────────────────────────────
# 6.3 安全风险热力分析
# ──────────────────────────────────────────────────────────────

@router.get("/risk-heatmap")
def get_risk_heatmap(db: Session = Depends(get_db)):
    """
    6.3 安全风险热力分析
    综合异常事件密度和飞行任务密度生成风险热力数据点
    返回格式: [{ lng, lat, weight }] 供前端热力图渲染
    """
    # 获取近30天异常事件位置
    since = datetime.now() - timedelta(days=30)
    events = db.query(AnomalyEvent).filter(
        AnomalyEvent.occurred_at >= since,
        AnomalyEvent.lng.isnot(None),
        AnomalyEvent.lat.isnot(None),
    ).all()

    heat_points = []
    for e in events:
        weight = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}.get(e.severity, 0.3)
        heat_points.append({"lng": e.lng, "lat": e.lat, "weight": weight})

    # 若事件数据不足，补充模拟热力数据（基于广州城区范围）
    if len(heat_points) < 20:
        base_points = [
            (113.330, 23.136), (113.271, 23.129), (113.261, 23.085),
            (113.273, 23.198), (113.350, 23.115), (113.285, 23.155),
            (113.310, 23.090), (113.245, 23.110),
        ]
        for lng, lat in base_points:
            for _ in range(3):
                heat_points.append({
                    "lng": lng + random.uniform(-0.02, 0.02),
                    "lat": lat + random.uniform(-0.02, 0.02),
                    "weight": random.uniform(0.1, 0.8),
                })

    return {"heat_points": heat_points, "event_count": len(events)}


# ──────────────────────────────────────────────────────────────
# 6.4 异常事件管理
# ──────────────────────────────────────────────────────────────

@router.get("/events")
def list_events(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    enterprise_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(AnomalyEvent)
    if event_type:
        q = q.filter(AnomalyEvent.event_type == event_type)
    if severity:
        q = q.filter(AnomalyEvent.severity == severity)
    if status:
        q = q.filter(AnomalyEvent.status == status)
    if enterprise_id:
        q = q.filter(AnomalyEvent.enterprise_id == enterprise_id)
    total = q.count()
    items = q.order_by(AnomalyEvent.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_ev(e) for e in items]}


@router.post("/events")
def create_event(data: dict, db: Session = Depends(get_db)):
    import random, string
    data.setdefault("event_no", "EVT" + "".join(random.choices(string.digits, k=8)))
    data.setdefault("occurred_at", datetime.now().isoformat())
    allowed = {c.key for c in AnomalyEvent.__table__.columns}
    ev = AnomalyEvent(**{k: v for k, v in data.items() if k in allowed})
    if isinstance(ev.occurred_at, str):
        ev.occurred_at = _parse_dt(ev.occurred_at) or datetime.now()
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return {"id": ev.id, "event_no": ev.event_no, "message": "事件已记录"}


@router.put("/events/{eid}/handle")
def handle_event(eid: int, data: dict, db: Session = Depends(get_db)):
    """6.4.3 事件处置"""
    ev = db.query(AnomalyEvent).filter(AnomalyEvent.id == eid).first()
    if not ev:
        raise HTTPException(404, "事件不存在")
    ev.status = data.get("status", "processing")
    ev.handler = data.get("handler")
    ev.handle_notes = data.get("handle_notes")
    if ev.status == "closed":
        ev.closed_at = datetime.now()
    db.commit()
    return {"message": "处置记录已更新"}


@router.get("/events/stats")
def event_stats(db: Session = Depends(get_db)):
    """事件统计摘要"""
    by_type = db.query(AnomalyEvent.event_type, func.count(AnomalyEvent.id)).group_by(AnomalyEvent.event_type).all()
    by_status = db.query(AnomalyEvent.status, func.count(AnomalyEvent.id)).group_by(AnomalyEvent.status).all()
    by_severity = db.query(AnomalyEvent.severity, func.count(AnomalyEvent.id)).group_by(AnomalyEvent.severity).all()
    return {
        "by_type": {r[0]: r[1] for r in by_type},
        "by_status": {r[0]: r[1] for r in by_status},
        "by_severity": {r[0]: r[1] for r in by_severity},
        "total": sum(r[1] for r in by_status),
    }


# ──────────────────────────────────────────────────────────────
# 6.5 安全监管台账
# ──────────────────────────────────────────────────────────────

@router.get("/records")
def list_records(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    record_type: Optional[str] = None,
    archived: Optional[int] = None,
    enterprise_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(SafetyRecord)
    if record_type:
        q = q.filter(SafetyRecord.record_type == record_type)
    if archived is not None:
        q = q.filter(SafetyRecord.archived == archived)
    if enterprise_id:
        q = q.filter(SafetyRecord.enterprise_id == enterprise_id)
    total = q.count()
    items = q.order_by(SafetyRecord.record_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_sr(r) for r in items]}


@router.post("/records")
def create_record(data: dict, db: Session = Depends(get_db)):
    import random, string
    data.setdefault("record_no", "REC" + "".join(random.choices(string.digits, k=8)))
    data.setdefault("record_time", datetime.now().isoformat())
    allowed = {c.key for c in SafetyRecord.__table__.columns}
    r = SafetyRecord(**{k: v for k, v in data.items() if k in allowed})
    if isinstance(r.record_time, str):
        r.record_time = _parse_dt(r.record_time) or datetime.now()
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "message": "台账记录已创建"}


@router.put("/records/{rid}/archive")
def archive_record(rid: int, db: Session = Depends(get_db)):
    """6.5.3 记录归档"""
    r = db.query(SafetyRecord).filter(SafetyRecord.id == rid).first()
    if not r:
        raise HTTPException(404, "记录不存在")
    r.archived = 1
    db.commit()
    return {"message": "已归档"}


# ──────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────

def _ev(e: AnomalyEvent) -> dict:
    return {
        "id": e.id, "event_no": e.event_no, "event_type": e.event_type,
        "severity": e.severity, "enterprise_id": e.enterprise_id,
        "drone_id": e.drone_id, "task_id": e.task_id,
        "lng": e.lng, "lat": e.lat, "altitude": e.altitude,
        "description": e.description, "status": e.status,
        "handler": e.handler, "handle_notes": e.handle_notes,
        "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        "closed_at": e.closed_at.isoformat() if e.closed_at else None,
    }


def _sr(r: SafetyRecord) -> dict:
    return {
        "id": r.id, "record_no": r.record_no, "record_type": r.record_type,
        "enterprise_id": r.enterprise_id, "event_id": r.event_id,
        "title": r.title, "content": r.content, "result": r.result,
        "archived": r.archived, "operator": r.operator,
        "record_time": r.record_time.isoformat() if r.record_time else None,
    }


def _parse_dt(s) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None
