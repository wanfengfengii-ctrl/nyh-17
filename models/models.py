from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "待处理"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"


class ApprovalStatus(str, enum.Enum):
    DRAFT = "草稿"
    SUBMITTED = "待审批"
    APPROVED = "已通过"
    REJECTED = "已驳回"


class OperationType(str, enum.Enum):
    CREATE = "创建"
    UPDATE = "更新"
    DELETE = "删除"
    SUBMIT = "提交审批"
    APPROVE = "审批通过"
    REJECT = "审批驳回"
    ASSIGN = "分派"
    UPLOAD = "上传"
    LOCK = "锁定"
    UNLOCK = "解锁"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="修复员")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assigned_tasks = relationship("RepairTask", foreign_keys="RepairTask.assignee_id", back_populates="assignee")
    created_tasks = relationship("RepairTask", foreign_keys="RepairTask.creator_id", back_populates="creator")
    operation_logs = relationship("OperationLog", back_populates="user")


class Pottery(Base):
    __tablename__ = "potteries"

    id = Column(Integer, primary_key=True, index=True)
    pottery_number = Column(String, unique=True, index=True)
    water_area = Column(String)
    trench_number = Column(String)
    material = Column(String)
    decoration_description = Column(Text)
    damage_level = Column(String)
    current_status = Column(String)
    recovery_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_locked = Column(Boolean, default=False)

    cleaning_records = relationship("CleaningRecord", back_populates="pottery")
    pottery_groups = relationship("PotteryGroupMember", back_populates="pottery")
    storage_record = relationship("StorageRecord", uselist=False, back_populates="pottery")
    images = relationship("PotteryImage", back_populates="pottery", cascade="all, delete-orphan")
    repair_tasks = relationship("RepairTask", back_populates="pottery")


class PotteryImage(Base):
    __tablename__ = "pottery_images"

    id = Column(Integer, primary_key=True, index=True)
    pottery_id = Column(Integer, ForeignKey("potteries.id"))
    image_path = Column(String)
    image_type = Column(String)
    description = Column(Text)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pottery = relationship("Pottery", back_populates="images")


class CleaningRecord(Base):
    __tablename__ = "cleaning_records"

    id = Column(Integer, primary_key=True, index=True)
    pottery_id = Column(Integer, ForeignKey("potteries.id"))
    cleaning_date = Column(Date)
    cleaner = Column(String)
    cleaning_method = Column(String)
    cleaning_result = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pottery = relationship("Pottery", back_populates="cleaning_records")


class RepairTask(Base):
    __tablename__ = "repair_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_number = Column(String, unique=True, index=True)
    pottery_id = Column(Integer, ForeignKey("potteries.id"))
    title = Column(String)
    description = Column(Text)
    priority = Column(String, default="普通")
    status = Column(String, default=TaskStatus.PENDING)
    creator_id = Column(Integer, ForeignKey("users.id"))
    assignee_id = Column(Integer, ForeignKey("users.id"))
    due_date = Column(Date)
    completed_date = Column(Date)
    result = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pottery = relationship("Pottery", back_populates="repair_tasks")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")


class PotteryGroup(Base):
    __tablename__ = "pottery_groups"

    id = Column(Integer, primary_key=True, index=True)
    group_number = Column(String, unique=True, index=True)
    confidence = Column(Integer)
    organizer = Column(String)
    notes = Column(Text)
    is_completed = Column(Boolean, default=False)
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    members = relationship("PotteryGroupMember", back_populates="group", cascade="all, delete-orphan")
    versions = relationship("GroupVersion", back_populates="group", cascade="all, delete-orphan")


class PotteryGroupMember(Base):
    __tablename__ = "pottery_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("pottery_groups.id"))
    pottery_id = Column(Integer, ForeignKey("potteries.id"))

    group = relationship("PotteryGroup", back_populates="members")
    pottery = relationship("Pottery", back_populates="pottery_groups")


class GroupVersion(Base):
    __tablename__ = "group_versions"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("pottery_groups.id"))
    version_number = Column(Integer)
    confidence = Column(Integer)
    organizer = Column(String)
    notes = Column(Text)
    pottery_ids = Column(Text)
    change_description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("PotteryGroup", back_populates="versions")


class StorageRecord(Base):
    __tablename__ = "storage_records"

    id = Column(Integer, primary_key=True, index=True)
    pottery_id = Column(Integer, ForeignKey("potteries.id"), unique=True)
    storage_date = Column(Date)
    location = Column(String)
    registrar = Column(String)
    notes = Column(Text)
    is_official = Column(Boolean, default=False)
    approval_status = Column(String, default=ApprovalStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pottery = relationship("Pottery", back_populates="storage_record")
    approvals = relationship("StorageApproval", back_populates="storage_record", cascade="all, delete-orphan")


class StorageApproval(Base):
    __tablename__ = "storage_approvals"

    id = Column(Integer, primary_key=True, index=True)
    storage_id = Column(Integer, ForeignKey("storage_records.id"))
    approver_id = Column(Integer, ForeignKey("users.id"))
    approval_status = Column(String)
    comments = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    storage_record = relationship("StorageRecord", back_populates="approvals")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    operation_type = Column(String)
    target_type = Column(String)
    target_id = Column(Integer)
    description = Column(Text)
    ip_address = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="operation_logs")


class UnderwaterImage(Base):
    __tablename__ = "underwater_images"

    id = Column(Integer, primary_key=True, index=True)
    pottery_id = Column(Integer, ForeignKey("potteries.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("pottery_groups.id"), nullable=True)
    image_number = Column(String, unique=True, index=True)
    image_type = Column(String, default="现场照片")
    file_path = Column(String)
    file_type = Column(String, default="image")
    description = Column(Text)
    
    coordinate_x = Column(String)
    coordinate_y = Column(String)
    coordinate_z = Column(String)
    depth = Column(String)
    
    shooting_time = Column(DateTime)
    photographer = Column(String)
    trench_number = Column(String)
    water_area = Column(String)
    
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pottery = relationship("Pottery")
    group = relationship("PotteryGroup")
