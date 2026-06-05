from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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

    cleaning_records = relationship("CleaningRecord", back_populates="pottery")
    pottery_groups = relationship("PotteryGroupMember", back_populates="pottery")
    storage_record = relationship("StorageRecord", uselist=False, back_populates="pottery")


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


class PotteryGroup(Base):
    __tablename__ = "pottery_groups"

    id = Column(Integer, primary_key=True, index=True)
    group_number = Column(String, unique=True, index=True)
    confidence = Column(Integer)
    organizer = Column(String)
    notes = Column(Text)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("PotteryGroupMember", back_populates="group", cascade="all, delete-orphan")


class PotteryGroupMember(Base):
    __tablename__ = "pottery_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("pottery_groups.id"))
    pottery_id = Column(Integer, ForeignKey("potteries.id"))

    group = relationship("PotteryGroup", back_populates="members")
    pottery = relationship("Pottery", back_populates="pottery_groups")


class StorageRecord(Base):
    __tablename__ = "storage_records"

    id = Column(Integer, primary_key=True, index=True)
    pottery_id = Column(Integer, ForeignKey("potteries.id"), unique=True)
    storage_date = Column(Date)
    location = Column(String)
    registrar = Column(String)
    notes = Column(Text)
    is_official = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pottery = relationship("Pottery", back_populates="storage_record")
