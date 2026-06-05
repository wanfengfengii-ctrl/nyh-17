from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class CleaningRecordBase(BaseModel):
    cleaning_date: date
    cleaner: str
    cleaning_method: str
    cleaning_result: str
    notes: Optional[str] = None


class CleaningRecordCreate(CleaningRecordBase):
    pottery_id: int


class CleaningRecord(CleaningRecordBase):
    id: int
    pottery_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StorageRecordBase(BaseModel):
    storage_date: date
    location: str
    registrar: str
    notes: Optional[str] = None
    is_official: bool = False


class StorageRecordCreate(StorageRecordBase):
    pottery_id: int


class StorageRecord(StorageRecordBase):
    id: int
    pottery_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PotteryBase(BaseModel):
    pottery_number: str
    water_area: str
    trench_number: str
    material: str
    decoration_description: str
    damage_level: str
    current_status: str
    recovery_date: date

    @validator('recovery_date')
    def recovery_date_not_future(cls, v):
        if v > date.today():
            raise ValueError('出水日期不能晚于当前日期')
        return v


class PotteryCreate(PotteryBase):
    pass


class PotteryUpdate(BaseModel):
    water_area: Optional[str] = None
    trench_number: Optional[str] = None
    material: Optional[str] = None
    decoration_description: Optional[str] = None
    damage_level: Optional[str] = None
    current_status: Optional[str] = None
    recovery_date: Optional[date] = None

    @validator('recovery_date')
    def recovery_date_not_future(cls, v):
        if v and v > date.today():
            raise ValueError('出水日期不能晚于当前日期')
        return v


class Pottery(PotteryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    cleaning_records: List[CleaningRecord] = []
    storage_record: Optional[StorageRecord] = None

    class Config:
        from_attributes = True


class PotteryGroupMemberBase(BaseModel):
    pottery_id: int


class PotteryGroupMemberCreate(PotteryGroupMemberBase):
    pass


class PotteryGroupMember(PotteryGroupMemberBase):
    id: int
    group_id: int
    pottery: Optional[Pottery] = None

    class Config:
        from_attributes = True


class PotteryGroupBase(BaseModel):
    group_number: str
    confidence: int = Field(..., ge=0, le=100)
    organizer: str
    notes: Optional[str] = None
    is_completed: bool = False


class PotteryGroupCreate(PotteryGroupBase):
    pottery_ids: List[int] = []


class PotteryGroupUpdate(BaseModel):
    confidence: Optional[int] = Field(None, ge=0, le=100)
    organizer: Optional[str] = None
    notes: Optional[str] = None
    is_completed: Optional[bool] = None
    pottery_ids: Optional[List[int]] = None


class PotteryGroup(PotteryGroupBase):
    id: int
    created_at: datetime
    members: List[PotteryGroupMember] = []

    class Config:
        from_attributes = True
