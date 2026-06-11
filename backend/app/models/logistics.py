"""
物流运营管理子系统数据库模型
涵盖企业、配送订单、配送任务、配送站、无人机资源
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.database import Base


class Enterprise(Base):
    """物流运营企业"""
    __tablename__ = "enterprises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, comment="企业代码")
    name = Column(String(200), nullable=False, comment="企业名称")
    contact_person = Column(String(100), comment="联系人")
    contact_phone = Column(String(50), comment="联系电话")
    address = Column(String(500), comment="企业地址")
    license_no = Column(String(100), comment="营业执照号")
    status = Column(String(20), default="active", comment="状态: active/suspended/restricted")
    api_key = Column(String(100), comment="接入凭证 API Key")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    orders = relationship("DeliveryOrder", back_populates="enterprise")
    stations = relationship("DeliveryStation", back_populates="enterprise")
    drones = relationship("DroneResource", back_populates="enterprise")


class DeliveryOrder(Base):
    """配送订单"""
    __tablename__ = "delivery_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False, comment="订单编号")
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    cargo_type = Column(String(100), comment="货物类型")
    cargo_weight = Column(Float, comment="货物重量(kg)")
    sender_name = Column(String(100), comment="寄件人")
    sender_address = Column(String(500), comment="寄件地址")
    sender_lng = Column(Float, comment="寄件点经度")
    sender_lat = Column(Float, comment="寄件点纬度")
    receiver_name = Column(String(100), comment="收件人")
    receiver_address = Column(String(500), comment="收件地址")
    receiver_lng = Column(Float, comment="收件点经度")
    receiver_lat = Column(Float, comment="收件点纬度")
    planned_time = Column(DateTime, comment="计划配送时间")
    status = Column(String(20), default="pending", comment="状态: pending/dispatched/delivering/completed/cancelled/abnormal")
    abnormal_reason = Column(String(500), comment="异常原因")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    enterprise = relationship("Enterprise", back_populates="orders")
    task = relationship("DeliveryTask", back_populates="order", uselist=False)


class DeliveryTask(Base):
    """配送任务"""
    __tablename__ = "delivery_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_no = Column(String(50), unique=True, nullable=False, comment="任务编号")
    order_id = Column(Integer, ForeignKey("delivery_orders.id"), nullable=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("delivery_stations.id"), nullable=True)
    drone_id = Column(Integer, ForeignKey("drone_resources.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    planned_start = Column(DateTime, comment="计划开始时间")
    planned_end = Column(DateTime, comment="计划结束时间")
    actual_start = Column(DateTime, comment="实际开始时间")
    actual_end = Column(DateTime, comment="实际结束时间")
    status = Column(String(20), default="pending",
                    comment="状态: pending/assigned/executing/completed/failed/cancelled")
    priority = Column(Integer, default=5, comment="优先级 1-10")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    order = relationship("DeliveryOrder", back_populates="task")


class DeliveryStation(Base):
    """配送站"""
    __tablename__ = "delivery_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    name = Column(String(200), nullable=False, comment="站点名称")
    code = Column(String(50), comment="站点编码")
    address = Column(String(500), comment="站点地址")
    lng = Column(Float, nullable=False, comment="经度")
    lat = Column(Float, nullable=False, comment="纬度")
    altitude = Column(Float, default=0, comment="海拔高度(米)")
    landing_capacity = Column(Integer, default=2, comment="同时起降能力")
    service_radius = Column(Float, default=5.0, comment="服务半径(km)")
    status = Column(String(20), default="active", comment="状态: active/inactive/maintenance")
    pending_tasks = Column(Integer, default=0, comment="待处理任务数")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    enterprise = relationship("Enterprise", back_populates="stations")


class DroneResource(Base):
    """无人机资源"""
    __tablename__ = "drone_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=False)
    drone_no = Column(String(50), unique=True, nullable=False, comment="无人机编号")
    model = Column(String(100), comment="型号")
    max_payload = Column(Float, comment="最大载重(kg)")
    max_range = Column(Float, comment="最大航程(km)")
    max_endurance = Column(Integer, comment="最大续航(分钟)")
    battery_level = Column(Integer, default=100, comment="当前电量(%)")
    status = Column(String(20), default="idle",
                    comment="状态: idle/executing/charging/maintenance/fault")
    current_task_id = Column(Integer, ForeignKey("delivery_tasks.id"), nullable=True)
    station_id = Column(Integer, ForeignKey("delivery_stations.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    enterprise = relationship("Enterprise", back_populates="drones")
