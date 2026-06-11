"""
系统管理子系统数据库模型
涵盖用户、角色、系统参数、操作日志
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base


class SystemUser(Base):
    """系统用户"""
    __tablename__ = "system_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, comment="用户名")
    real_name = Column(String(100), comment="真实姓名")
    email = Column(String(200), comment="邮箱")
    phone = Column(String(50), comment="手机号")
    role = Column(String(50), default="operator",
                  comment="角色: admin/supervisor/operator/enterprise")
    enterprise_id = Column(Integer, nullable=True, comment="所属企业ID（企业用户）")
    status = Column(String(20), default="active",
                    comment="状态: active/inactive/locked")
    last_login = Column(DateTime, comment="最近登录时间")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SystemParam(Base):
    """系统参数"""
    __tablename__ = "system_params"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False,
                      comment="分类: flight_threshold/planning/external_service/alert")
    param_key = Column(String(100), nullable=False, unique=True, comment="参数键")
    param_name = Column(String(200), nullable=False, comment="参数名称")
    param_value = Column(String(500), nullable=False, comment="参数值")
    unit = Column(String(50), comment="单位")
    description = Column(String(500), comment="参数说明")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class OperationLog(Base):
    """操作日志"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, comment="操作用户ID")
    username = Column(String(100), comment="操作用户名")
    module = Column(String(100), comment="所属模块")
    action = Column(String(100), comment="操作动作")
    resource_type = Column(String(100), comment="操作资源类型")
    resource_id = Column(String(100), comment="操作资源ID")
    detail = Column(Text, comment="操作详情")
    ip_address = Column(String(50), comment="IP地址")
    result = Column(String(20), default="success", comment="结果: success/failure")
    created_at = Column(DateTime, server_default=func.now())


class GISLayer(Base):
    """GIS图层"""
    __tablename__ = "gis_layers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="图层名称")
    code = Column(String(100), unique=True, comment="图层编码")
    layer_type = Column(String(50), comment="图层类型: base/zone/route/poi/custom")
    data_source = Column(String(200), comment="数据来源")
    description = Column(String(500), comment="图层说明")
    published = Column(Boolean, default=True, comment="是否发布")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
