from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: Optional[str] = "修复员"


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


class PotteryImageBase(BaseModel):
    pottery_id: int
    image_path: str
    image_type: str
    description: Optional[str] = None


class PotteryImageCreate(PotteryImageBase):
    uploaded_by: int


class PotteryImage(PotteryImageBase):
    id: int
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True


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


class RepairTaskBase(BaseModel):
    pottery_id: int
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "普通"
    status: Optional[str] = "待处理"
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None


class RepairTaskCreate(RepairTaskBase):
    pass


class RepairTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    result: Optional[str] = None


class RepairTask(RepairTaskBase):
    id: int
    task_number: str
    creator_id: int
    completed_date: Optional[date] = None
    result: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    creator: Optional[User] = None
    assignee: Optional[User] = None

    class Config:
        from_attributes = True


class StorageRecordBase(BaseModel):
    storage_date: date
    location: str
    registrar: str
    notes: Optional[str] = None
    is_official: bool = False
    approval_status: Optional[str] = "草稿"


class StorageRecordCreate(StorageRecordBase):
    pottery_id: int


class StorageRecordUpdate(BaseModel):
    storage_date: Optional[date] = None
    location: Optional[str] = None
    registrar: Optional[str] = None
    notes: Optional[str] = None
    is_official: Optional[bool] = None
    approval_status: Optional[str] = None


class StorageRecord(StorageRecordBase):
    id: int
    pottery_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StorageApprovalBase(BaseModel):
    storage_id: int
    approval_status: str
    comments: Optional[str] = None


class StorageApprovalCreate(StorageApprovalBase):
    approver_id: int


class StorageApproval(StorageApprovalBase):
    id: int
    approver_id: int
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
    is_locked: Optional[bool] = False

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
    is_locked: Optional[bool] = None

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
    images: List[PotteryImage] = []
    repair_tasks: List[RepairTask] = []

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


class GroupVersionBase(BaseModel):
    group_id: int
    version_number: int
    confidence: int
    organizer: str
    notes: Optional[str] = None
    pottery_ids: str
    change_description: Optional[str] = None


class GroupVersionCreate(GroupVersionBase):
    created_by: int


class GroupVersion(GroupVersionBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class PotteryGroupBase(BaseModel):
    group_number: str
    confidence: int = Field(..., ge=0, le=100)
    organizer: str
    notes: Optional[str] = None
    is_completed: bool = False
    current_version: Optional[int] = 1


class PotteryGroupCreate(PotteryGroupBase):
    pottery_ids: List[int] = []


class PotteryGroupUpdate(BaseModel):
    confidence: Optional[int] = Field(None, ge=0, le=100)
    organizer: Optional[str] = None
    notes: Optional[str] = None
    is_completed: Optional[bool] = None
    pottery_ids: Optional[List[int]] = None
    change_description: Optional[str] = None


class PotteryGroup(PotteryGroupBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    members: List[PotteryGroupMember] = []
    versions: List[GroupVersion] = []

    class Config:
        from_attributes = True


class OperationLogBase(BaseModel):
    user_id: int
    operation_type: str
    target_type: str
    target_id: int
    description: Optional[str] = None
    ip_address: Optional[str] = None


class OperationLogCreate(OperationLogBase):
    pass


class OperationLog(OperationLogBase):
    id: int
    created_at: datetime
    user: Optional[User] = None

    class Config:
        from_attributes = True


class UnderwaterImageBase(BaseModel):
    pottery_id: int
    group_id: Optional[int] = None
    image_number: str
    image_type: Optional[str] = "现场照片"
    file_type: Optional[str] = "image"
    description: Optional[str] = None
    coordinate_x: Optional[str] = None
    coordinate_y: Optional[str] = None
    coordinate_z: Optional[str] = None
    depth: Optional[str] = None
    shooting_time: Optional[datetime] = None
    photographer: Optional[str] = None
    trench_number: Optional[str] = None
    water_area: Optional[str] = None


class UnderwaterImageCreate(UnderwaterImageBase):
    file_path: str
    uploaded_by: int


class UnderwaterImageUpdate(BaseModel):
    group_id: Optional[int] = None
    image_type: Optional[str] = None
    description: Optional[str] = None
    coordinate_x: Optional[str] = None
    coordinate_y: Optional[str] = None
    coordinate_z: Optional[str] = None
    depth: Optional[str] = None
    shooting_time: Optional[datetime] = None
    photographer: Optional[str] = None
    trench_number: Optional[str] = None
    water_area: Optional[str] = None


class UnderwaterImage(UnderwaterImageBase):
    id: int
    file_path: str
    uploaded_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RepairComparisonImageBase(BaseModel):
    repair_plan_id: int
    image_type: str
    image_stage: str
    description: Optional[str] = None


class RepairComparisonImageCreate(RepairComparisonImageBase):
    image_path: str
    uploaded_by: int


class RepairComparisonImage(RepairComparisonImageBase):
    id: int
    image_path: str
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewRecordBase(BaseModel):
    repair_plan_id: int
    review_opinion: Optional[str] = None
    review_conclusion: Optional[str] = None
    review_date: Optional[date] = None
    is_returned: bool = False
    return_reason: Optional[str] = None


class ReviewRecordCreate(ReviewRecordBase):
    reviewer_id: int
    reviewer_name: Optional[str] = None


class ReviewRecordUpdate(BaseModel):
    review_opinion: Optional[str] = None
    review_conclusion: Optional[str] = None
    review_date: Optional[date] = None
    is_returned: Optional[bool] = None
    return_reason: Optional[str] = None


class ReviewRecord(ReviewRecordBase):
    id: int
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RepairPlanBase(BaseModel):
    pottery_id: int
    group_id: Optional[int] = None
    task_id: Optional[int] = None
    plan_name: str
    plan_description: Optional[str] = None
    repair_method: Optional[str] = None
    materials_used: Optional[str] = None
    estimated_duration: Optional[int] = None
    expected_completion_date: Optional[date] = None
    restorer_id: Optional[int] = None
    restorer_name: Optional[str] = None

    @validator('expected_completion_date')
    def expected_completion_date_not_past(cls, v):
        if v and v < date.today():
            raise ValueError('预计完成日期不能早于当前日期')
        return v


class RepairPlanCreate(RepairPlanBase):
    pass


class RepairPlanUpdate(BaseModel):
    plan_name: Optional[str] = None
    plan_description: Optional[str] = None
    repair_method: Optional[str] = None
    materials_used: Optional[str] = None
    estimated_duration: Optional[int] = None
    expected_completion_date: Optional[date] = None
    status: Optional[str] = None
    progress: Optional[str] = None
    restorer_id: Optional[int] = None
    restorer_name: Optional[str] = None

    @validator('expected_completion_date')
    def expected_completion_date_not_past(cls, v):
        if v and v < date.today():
            raise ValueError('预计完成日期不能早于当前日期')
        return v


class RepairPlan(RepairPlanBase):
    id: int
    plan_number: str
    status: str
    progress: str
    created_by: int
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    review_records: List[ReviewRecord] = []
    comparison_images: List[RepairComparisonImage] = []

    class Config:
        from_attributes = True
