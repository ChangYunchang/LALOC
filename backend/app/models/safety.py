"""
安全监管子系统数据库模型
涵盖异常事件、安全监管台账
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class AnomalyEvent(Base):
    """异常事件"""
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_no = Column(String(50), unique=True, nullable=False, comment="事件编号")
    event_type = Column(String(50), nullable=False,
                        comment="类型: boundary_violation/route_conflict/weather_anomaly/comm_loss/device_fault/congestion")
    severity = Column(String(20), default="medium",
                      comment="严重程度: low/medium/high/critical")
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    drone_id = Column(Integer, ForeignKey("drone_resources.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("delivery_tasks.id"), nullable=True)
    lng = Column(Float, comment="事件位置经度")
    lat = Column(Float, comment="事件位置纬度")
    altitude = Column(Float, comment="事件位置高度(米)")
    description = Column(Text, comment="事件描述")
    status = Column(String(20), default="open",
                    comment="状态: open/processing/closed")
    handler = Column(String(100), comment="处置人")
    handle_notes = Column(Text, comment="处置说明")
    occurred_at = Column(DateTime, nullable=False, comment="发生时间")
    closed_at = Column(DateTime, comment="关闭时间")
    created_at = Column(DateTime, server_default=func.now())


class SafetyRecord(Base):
    """安全监管台账"""
    __tablename__ = "safety_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_no = Column(String(50), unique=True, nullable=False, comment="记录编号")
    record_type = Column(String(50), comment="记录类型: inspection/event/violation/alert")
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("anomaly_events.id"), nullable=True)
    title = Column(String(200), comment="记录标题")
    content = Column(Text, comment="记录内容")
    result = Column(String(100), comment="处理结果")
    archived = Column(Integer, default=0, comment="是否归档 0/1")
    operator = Column(String(100), comment="操作人")
    record_time = Column(DateTime, nullable=False, comment="记录时间")
    created_at = Column(DateTime, server_default=func.now())
