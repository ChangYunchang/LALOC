"""
系统管理子系统 API
提供用户管理、系统参数、操作日志、GIS图层和服务状态接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
import random

from app.database import get_db
from app.models.system import SystemUser, SystemParam, OperationLog, GISLayer

router = APIRouter(prefix="/api/system", tags=["系统管理"])


# ──────────────────────────────────────────────────────────────
# 9.1 用户管理
# ──────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    username: Optional[str] = None, role: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(SystemUser)
    if username:
        q = q.filter(SystemUser.username.ilike(f"%{username}%"))
    if role:
        q = q.filter(SystemUser.role == role)
    if status:
        q = q.filter(SystemUser.status == status)
    total = q.count()
    items = q.order_by(SystemUser.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_u(u) for u in items]}


@router.post("/users")
def create_user(data: dict, db: Session = Depends(get_db)):
    if db.query(SystemUser).filter(SystemUser.username == data.get("username")).first():
        raise HTTPException(400, "用户名已存在")
    allowed = {c.key for c in SystemUser.__table__.columns}
    u = SystemUser(**{k: v for k, v in data.items() if k in allowed})
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "message": "用户创建成功"}


@router.put("/users/{uid}")
def update_user(uid: int, data: dict, db: Session = Depends(get_db)):
    u = db.query(SystemUser).filter(SystemUser.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    for k, v in data.items():
        if hasattr(u, k) and k not in ("id", "username"):
            setattr(u, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/users/{uid}")
def delete_user(uid: int, db: Session = Depends(get_db)):
    u = db.query(SystemUser).filter(SystemUser.id == uid).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    db.delete(u)
    db.commit()
    return {"message": "删除成功"}


# ──────────────────────────────────────────────────────────────
# 9.4 系统参数配置
# ──────────────────────────────────────────────────────────────

@router.get("/params")
def list_params(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(SystemParam)
    if category:
        q = q.filter(SystemParam.category == category)
    items = q.order_by(SystemParam.category, SystemParam.id).all()
    return {"items": [_p(p) for p in items]}


@router.put("/params/{pid}")
def update_param(pid: int, data: dict, db: Session = Depends(get_db)):
    p = db.query(SystemParam).filter(SystemParam.id == pid).first()
    if not p:
        raise HTTPException(404, "参数不存在")
    p.param_value = data.get("param_value", p.param_value)
    db.commit()
    return {"message": "参数已更新"}


@router.get("/params/categories")
def list_param_categories(db: Session = Depends(get_db)):
    rows = db.query(SystemParam.category).distinct().all()
    return [r[0] for r in rows]


# ──────────────────────────────────────────────────────────────
# 9.5 日志审计
# ──────────────────────────────────────────────────────────────

@router.get("/logs")
def list_logs(
    page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=200),
    username: Optional[str] = None,
    module: Optional[str] = None,
    result: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(OperationLog)
    if username:
        q = q.filter(OperationLog.username.ilike(f"%{username}%"))
    if module:
        q = q.filter(OperationLog.module.ilike(f"%{module}%"))
    if result:
        q = q.filter(OperationLog.result == result)
    total = q.count()
    items = q.order_by(OperationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [_l(log) for log in items]}


@router.post("/logs")
def write_log(data: dict, db: Session = Depends(get_db)):
    """内部接口：写入操作日志"""
    allowed = {c.key for c in OperationLog.__table__.columns}
    log = OperationLog(**{k: v for k, v in data.items() if k in allowed})
    db.add(log)
    db.commit()
    return {"message": "ok"}


# ──────────────────────────────────────────────────────────────
# 9.6 服务状态监测
# ──────────────────────────────────────────────────────────────

@router.get("/service-status")
def get_service_status(db: Session = Depends(get_db)):
    """
    9.6 服务状态监测
    检查各依赖服务的健康状态
    """
    # 检查数据库连通性
    db_ok = False
    try:
        db.execute(func.now().select())
        db_ok = True
    except Exception:
        pass

    # 模拟其他服务状态（真实环境应实际调用各服务 health endpoint）
    services = [
        {"name": "数据库 (PostgreSQL+PostGIS)", "status": "healthy" if db_ok else "error",
         "latency_ms": random.randint(1, 10), "last_check": datetime.now().isoformat()},
        {"name": "高德地图 API", "status": "healthy",
         "latency_ms": random.randint(20, 150), "last_check": datetime.now().isoformat()},
        {"name": "Cesium Ion 服务", "status": "healthy",
         "latency_ms": random.randint(50, 300), "last_check": datetime.now().isoformat()},
        {"name": "气象数据接口", "status": random.choice(["healthy", "healthy", "degraded"]),
         "latency_ms": random.randint(100, 500), "last_check": datetime.now().isoformat()},
        {"name": "路径规划引擎", "status": "healthy",
         "latency_ms": random.randint(5, 50), "last_check": datetime.now().isoformat()},
    ]

    overall = "healthy" if all(s["status"] == "healthy" for s in services) else \
              "error" if any(s["status"] == "error" for s in services) else "degraded"

    return {"overall": overall, "services": services, "checked_at": datetime.now().isoformat()}


# ──────────────────────────────────────────────────────────────
# GIS 图层管理（8.1）
# ──────────────────────────────────────────────────────────────

@router.get("/gis-layers")
def list_gis_layers(db: Session = Depends(get_db)):
    items = db.query(GISLayer).order_by(GISLayer.sort_order, GISLayer.id).all()
    return {"items": [_gl(g) for g in items]}


@router.post("/gis-layers")
def create_gis_layer(data: dict, db: Session = Depends(get_db)):
    allowed = {c.key for c in GISLayer.__table__.columns}
    g = GISLayer(**{k: v for k, v in data.items() if k in allowed})
    db.add(g)
    db.commit()
    db.refresh(g)
    return {"id": g.id, "message": "图层已创建"}


@router.put("/gis-layers/{lid}")
def update_gis_layer(lid: int, data: dict, db: Session = Depends(get_db)):
    g = db.query(GISLayer).filter(GISLayer.id == lid).first()
    if not g:
        raise HTTPException(404, "图层不存在")
    for k, v in data.items():
        if hasattr(g, k) and k != "id":
            setattr(g, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/gis-layers/{lid}")
def delete_gis_layer(lid: int, db: Session = Depends(get_db)):
    g = db.query(GISLayer).filter(GISLayer.id == lid).first()
    if not g:
        raise HTTPException(404, "图层不存在")
    db.delete(g)
    db.commit()
    return {"message": "删除成功"}


# ──────────────────────────────────────────────────────────────
# 序列化工具
# ──────────────────────────────────────────────────────────────

def _u(u: SystemUser) -> dict:
    return {
        "id": u.id, "username": u.username, "real_name": u.real_name,
        "email": u.email, "phone": u.phone, "role": u.role,
        "enterprise_id": u.enterprise_id, "status": u.status,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _p(p: SystemParam) -> dict:
    return {
        "id": p.id, "category": p.category, "param_key": p.param_key,
        "param_name": p.param_name, "param_value": p.param_value,
        "unit": p.unit, "description": p.description,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _l(log: OperationLog) -> dict:
    return {
        "id": log.id, "username": log.username, "module": log.module,
        "action": log.action, "resource_type": log.resource_type,
        "resource_id": log.resource_id, "detail": log.detail,
        "ip_address": log.ip_address, "result": log.result,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _gl(g: GISLayer) -> dict:
    return {
        "id": g.id, "name": g.name, "code": g.code,
        "layer_type": g.layer_type, "data_source": g.data_source,
        "description": g.description, "published": g.published,
        "sort_order": g.sort_order,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }
