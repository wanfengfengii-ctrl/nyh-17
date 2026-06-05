from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import date, timedelta
from typing import Optional, List

from database import engine, Base, get_db
from models import User, Pottery, CleaningRecord, PotteryGroup, PotteryGroupMember, StorageRecord
from schemas import PotteryCreate, PotteryUpdate, CleaningRecordCreate, PotteryGroupCreate, PotteryGroupUpdate, StorageRecordCreate
from auth import get_password_hash, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="水下考古陶片拼合编目系统")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def datetime_format(value, format="%Y-%m-%d"):
    return value.strftime(format)


templates.env.filters["strftime"] = datetime_format


def init_default_user(db: Session):
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        hashed_password = get_password_hash("admin123")
        admin = User(username="admin", hashed_password=hashed_password, full_name="系统管理员")
        db.add(admin)
        db.commit()


with next(get_db()) as db:
    init_default_user(db)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "用户名或密码错误"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_potteries = db.query(Pottery).count()
    total_cleaned = db.query(Pottery).filter(Pottery.current_status == "已清洗").count()
    total_groups = db.query(PotteryGroup).count()
    total_stored = db.query(StorageRecord).filter(StorageRecord.is_official == True).count()

    recent_potteries = db.query(Pottery).order_by(Pottery.created_at.desc()).limit(5).all()
    recent_groups = db.query(PotteryGroup).order_by(PotteryGroup.created_at.desc()).limit(5).all()

    damage_stats = {
        "轻微": db.query(Pottery).filter(Pottery.damage_level == "轻微").count(),
        "中度": db.query(Pottery).filter(Pottery.damage_level == "中度").count(),
        "严重": db.query(Pottery).filter(Pottery.damage_level == "严重").count()
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "total_potteries": total_potteries,
        "total_cleaned": total_cleaned,
        "total_groups": total_groups,
        "total_stored": total_stored,
        "recent_potteries": recent_potteries,
        "recent_groups": recent_groups,
        "damage_stats": damage_stats,
        "today": date.today().isoformat()
    })


@app.get("/potteries", response_class=HTMLResponse)
async def list_potteries(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    keyword: Optional[str] = None,
    water_area: Optional[str] = None,
    damage_level: Optional[str] = None,
    current_status: Optional[str] = None
):
    query = db.query(Pottery)

    if keyword:
        query = query.filter(or_(
            Pottery.pottery_number.contains(keyword),
            Pottery.decoration_description.contains(keyword),
            Pottery.material.contains(keyword)
        ))
    if water_area:
        query = query.filter(Pottery.water_area == water_area)
    if damage_level:
        query = query.filter(Pottery.damage_level == damage_level)
    if current_status:
        query = query.filter(Pottery.current_status == current_status)

    potteries = query.order_by(Pottery.created_at.desc()).all()

    water_areas = [r[0] for r in db.query(Pottery.water_area).distinct().all() if r[0]]

    return templates.TemplateResponse("potteries.html", {
        "request": request,
        "current_user": current_user,
        "potteries": potteries,
        "keyword": keyword,
        "water_area": water_area,
        "damage_level": damage_level,
        "current_status": current_status,
        "water_areas": water_areas
    })


@app.get("/potteries/add", response_class=HTMLResponse)
async def add_pottery_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("pottery_form.html", {
        "request": request,
        "current_user": current_user,
        "pottery": None,
        "today": date.today().isoformat()
    })


@app.post("/potteries/add")
async def add_pottery(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pottery_number: str = Form(...),
    water_area: str = Form(...),
    trench_number: str = Form(...),
    material: str = Form(...),
    decoration_description: str = Form(...),
    damage_level: str = Form(...),
    current_status: str = Form(...),
    recovery_date: date = Form(...)
):
    existing = db.query(Pottery).filter(Pottery.pottery_number == pottery_number).first()
    if existing:
        return templates.TemplateResponse("pottery_form.html", {
            "request": request,
            "current_user": current_user,
            "pottery": None,
            "today": date.today().isoformat(),
            "error": "陶片编号已存在"
        })

    if recovery_date > date.today():
        return templates.TemplateResponse("pottery_form.html", {
            "request": request,
            "current_user": current_user,
            "pottery": None,
            "today": date.today().isoformat(),
            "error": "出水日期不能晚于当前日期"
        })

    pottery = Pottery(
        pottery_number=pottery_number,
        water_area=water_area,
        trench_number=trench_number,
        material=material,
        decoration_description=decoration_description,
        damage_level=damage_level,
        current_status=current_status,
        recovery_date=recovery_date
    )
    db.add(pottery)
    db.commit()
    db.refresh(pottery)

    return RedirectResponse(url="/potteries", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/potteries/{pottery_id}/edit", response_class=HTMLResponse)
async def edit_pottery_page(
    pottery_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pottery = db.query(Pottery).filter(Pottery.id == pottery_id).first()
    if not pottery:
        return RedirectResponse(url="/potteries", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("pottery_form.html", {
        "request": request,
        "current_user": current_user,
        "pottery": pottery,
        "today": date.today().isoformat()
    })


@app.post("/potteries/{pottery_id}/edit")
async def edit_pottery(
    pottery_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    water_area: str = Form(...),
    trench_number: str = Form(...),
    material: str = Form(...),
    decoration_description: str = Form(...),
    damage_level: str = Form(...),
    current_status: str = Form(...),
    recovery_date: date = Form(...)
):
    pottery = db.query(Pottery).filter(Pottery.id == pottery_id).first()
    if not pottery:
        return RedirectResponse(url="/potteries", status_code=status.HTTP_303_SEE_OTHER)

    if recovery_date > date.today():
        return templates.TemplateResponse("pottery_form.html", {
            "request": request,
            "current_user": current_user,
            "pottery": pottery,
            "today": date.today().isoformat(),
            "error": "出水日期不能晚于当前日期"
        })

    pottery.water_area = water_area
    pottery.trench_number = trench_number
    pottery.material = material
    pottery.decoration_description = decoration_description
    pottery.damage_level = damage_level
    pottery.current_status = current_status
    pottery.recovery_date = recovery_date

    db.commit()
    return RedirectResponse(url="/potteries", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/potteries/{pottery_id}", response_class=HTMLResponse)
async def pottery_detail(
    pottery_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pottery = db.query(Pottery).filter(Pottery.id == pottery_id).first()
    if not pottery:
        return RedirectResponse(url="/potteries", status_code=status.HTTP_303_SEE_OTHER)

    cleaning_records = db.query(CleaningRecord).filter(CleaningRecord.pottery_id == pottery_id).order_by(CleaningRecord.cleaning_date.desc()).all()

    groups = db.query(PotteryGroup).join(PotteryGroupMember).filter(PotteryGroupMember.pottery_id == pottery_id).all()

    storage_record = db.query(StorageRecord).filter(StorageRecord.pottery_id == pottery_id).first()

    return templates.TemplateResponse("pottery_detail.html", {
        "request": request,
        "current_user": current_user,
        "pottery": pottery,
        "cleaning_records": cleaning_records,
        "groups": groups,
        "storage_record": storage_record
    })


@app.get("/potteries/{pottery_id}/cleaning/add", response_class=HTMLResponse)
async def add_cleaning_page(
    pottery_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pottery = db.query(Pottery).filter(Pottery.id == pottery_id).first()
    if not pottery:
        return RedirectResponse(url="/potteries", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("cleaning_form.html", {
        "request": request,
        "current_user": current_user,
        "pottery": pottery,
        "today": date.today().isoformat()
    })


@app.post("/potteries/{pottery_id}/cleaning/add")
async def add_cleaning(
    pottery_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cleaning_date: date = Form(...),
    cleaner: str = Form(...),
    cleaning_method: str = Form(...),
    cleaning_result: str = Form(...),
    notes: str = Form("")
):
    pottery = db.query(Pottery).filter(Pottery.id == pottery_id).first()
    if not pottery:
        return RedirectResponse(url="/potteries", status_code=status.HTTP_303_SEE_OTHER)

    if cleaning_date > date.today():
        return templates.TemplateResponse("cleaning_form.html", {
            "request": request,
            "current_user": current_user,
            "pottery": pottery,
            "today": date.today().isoformat(),
            "error": "清洗日期不能晚于当前日期"
        })

    cleaning = CleaningRecord(
        pottery_id=pottery_id,
        cleaning_date=cleaning_date,
        cleaner=cleaner,
        cleaning_method=cleaning_method,
        cleaning_result=cleaning_result,
        notes=notes
    )
    db.add(cleaning)
    db.commit()

    return RedirectResponse(url=f"/potteries/{pottery_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/groups", response_class=HTMLResponse)
async def list_groups(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    is_completed: Optional[str] = None
):
    query = db.query(PotteryGroup)
    if is_completed is not None and is_completed != "":
        query = query.filter(PotteryGroup.is_completed == (is_completed == "true"))

    groups = query.order_by(PotteryGroup.created_at.desc()).all()
    return templates.TemplateResponse("groups.html", {
        "request": request,
        "current_user": current_user,
        "groups": groups,
        "is_completed": is_completed
    })


@app.get("/groups/add", response_class=HTMLResponse)
async def add_group_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
    active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(PotteryGroup.is_completed == False).all()
    active_pottery_ids = [r[0] for r in active_group_members]
    excluded_ids = stored_pottery_ids + active_pottery_ids

    available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()

    return templates.TemplateResponse("group_form.html", {
        "request": request,
        "current_user": current_user,
        "group": None,
        "available_potteries": available_potteries,
        "selected_potteries": []
    })


@app.post("/groups/add")
async def add_group(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    group_number: str = Form(...),
    confidence: int = Form(...),
    organizer: str = Form(...),
    notes: str = Form(""),
    pottery_ids: List[int] = Form([])
):
    existing = db.query(PotteryGroup).filter(PotteryGroup.group_number == group_number).first()
    if existing:
        stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
        active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(PotteryGroup.is_completed == False).all()
        active_pottery_ids = [r[0] for r in active_group_members]
        excluded_ids = stored_pottery_ids + active_pottery_ids
        available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()

        return templates.TemplateResponse("group_form.html", {
            "request": request,
            "current_user": current_user,
            "group": None,
            "available_potteries": available_potteries,
            "selected_potteries": pottery_ids,
            "error": "组号已存在"
        })

    if confidence < 0 or confidence > 100:
        stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
        active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(PotteryGroup.is_completed == False).all()
        active_pottery_ids = [r[0] for r in active_group_members]
        excluded_ids = stored_pottery_ids + active_pottery_ids
        available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()

        return templates.TemplateResponse("group_form.html", {
            "request": request,
            "current_user": current_user,
            "group": None,
            "available_potteries": available_potteries,
            "selected_potteries": pottery_ids,
            "error": "拼合可信度范围为0-100"
        })

    for pid in pottery_ids:
        official_storage = db.query(StorageRecord).filter(
            StorageRecord.pottery_id == pid,
            StorageRecord.is_official == True
        ).first()
        if official_storage:
            pottery = db.query(Pottery).filter(Pottery.id == pid).first()
            stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
            active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(PotteryGroup.is_completed == False).all()
            active_pottery_ids = [r[0] for r in active_group_members]
            excluded_ids = stored_pottery_ids + active_pottery_ids
            available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()
            
            return templates.TemplateResponse("group_form.html", {
                "request": request,
                "current_user": current_user,
                "group": None,
                "available_potteries": available_potteries,
                "selected_potteries": [p for p in pottery_ids if p != pid],
                "error": f"陶片 {pottery.pottery_number if pottery else pid} 已正式入库，无法加入拼合组"
            })

        in_other_group = db.query(PotteryGroupMember).join(PotteryGroup).filter(
            PotteryGroupMember.pottery_id == pid,
            PotteryGroup.is_completed == False
        ).first()
        if in_other_group:
            pottery = db.query(Pottery).filter(Pottery.id == pid).first()
            stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
            active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(PotteryGroup.is_completed == False).all()
            active_pottery_ids = [r[0] for r in active_group_members]
            excluded_ids = stored_pottery_ids + active_pottery_ids
            available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()
            
            return templates.TemplateResponse("group_form.html", {
                "request": request,
                "current_user": current_user,
                "group": None,
                "available_potteries": available_potteries,
                "selected_potteries": [p for p in pottery_ids if p != pid],
                "error": f"陶片 {pottery.pottery_number if pottery else pid} 已在其他进行中的拼合组中"
            })

    group = PotteryGroup(
        group_number=group_number,
        confidence=confidence,
        organizer=organizer,
        notes=notes,
        is_completed=False
    )
    db.add(group)
    db.flush()

    for pid in pottery_ids:
        member = PotteryGroupMember(group_id=group.id, pottery_id=pid)
        db.add(member)

    db.commit()
    return RedirectResponse(url="/groups", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/groups/{group_id}/edit", response_class=HTMLResponse)
async def edit_group_page(
    group_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(PotteryGroup).filter(PotteryGroup.id == group_id).first()
    if not group:
        return RedirectResponse(url="/groups", status_code=status.HTTP_303_SEE_OTHER)

    has_official = any(m.pottery.storage_record and m.pottery.storage_record.is_official for m in group.members)
    if has_official:
        groups = db.query(PotteryGroup).order_by(PotteryGroup.created_at.desc()).all()
        return templates.TemplateResponse("groups.html", {
            "request": request,
            "current_user": current_user,
            "groups": groups,
            "is_completed": None,
            "error": "包含已正式入库的陶片，无法修改"
        })

    stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
    active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(
        PotteryGroup.is_completed == False,
        PotteryGroup.id != group_id
    ).all()
    active_pottery_ids = [r[0] for r in active_group_members]
    excluded_ids = stored_pottery_ids + active_pottery_ids

    available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()
    selected_potteries = [m.pottery_id for m in group.members]

    return templates.TemplateResponse("group_form.html", {
        "request": request,
        "current_user": current_user,
        "group": group,
        "available_potteries": available_potteries,
        "selected_potteries": selected_potteries
    })


@app.post("/groups/{group_id}/edit")
async def edit_group(
    group_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    confidence: int = Form(...),
    organizer: str = Form(...),
    notes: str = Form(""),
    is_completed: str = Form("false"),
    pottery_ids: List[int] = Form([])
):
    group = db.query(PotteryGroup).filter(PotteryGroup.id == group_id).first()
    if not group:
        return RedirectResponse(url="/groups", status_code=status.HTTP_303_SEE_OTHER)

    has_official = any(m.pottery.storage_record and m.pottery.storage_record.is_official for m in group.members)
    
    current_member_ids = {m.pottery_id for m in group.members}
    new_member_ids = set(pottery_ids)
    
    if has_official and current_member_ids != new_member_ids:
        groups = db.query(PotteryGroup).order_by(PotteryGroup.created_at.desc()).all()
        return templates.TemplateResponse("groups.html", {
            "request": request,
            "current_user": current_user,
            "groups": groups,
            "is_completed": None,
            "error": "该拼合组包含已正式入库的陶片，无法修改组成员"
        })

    if confidence < 0 or confidence > 100:
        stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
        active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(
            PotteryGroup.is_completed == False,
            PotteryGroup.id != group_id
        ).all()
        active_pottery_ids = [r[0] for r in active_group_members]
        excluded_ids = stored_pottery_ids + active_pottery_ids
        available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()

        return templates.TemplateResponse("group_form.html", {
            "request": request,
            "current_user": current_user,
            "group": group,
            "available_potteries": available_potteries,
            "selected_potteries": pottery_ids,
            "error": "拼合可信度范围为0-100"
        })

    if not has_official:
        for pid in pottery_ids:
            if pid not in current_member_ids:
                official_storage = db.query(StorageRecord).filter(
                    StorageRecord.pottery_id == pid,
                    StorageRecord.is_official == True
                ).first()
                if official_storage:
                    pottery = db.query(Pottery).filter(Pottery.id == pid).first()
                    stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
                    active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(
                        PotteryGroup.is_completed == False,
                        PotteryGroup.id != group_id
                    ).all()
                    active_pottery_ids = [r[0] for r in active_group_members]
                    excluded_ids = stored_pottery_ids + active_pottery_ids
                    available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()
                    
                    return templates.TemplateResponse("group_form.html", {
                        "request": request,
                        "current_user": current_user,
                        "group": group,
                        "available_potteries": available_potteries,
                        "selected_potteries": [p for p in pottery_ids if p != pid],
                        "error": f"陶片 {pottery.pottery_number if pottery else pid} 已正式入库，无法加入拼合组"
                    })

                in_other_group = db.query(PotteryGroupMember).join(PotteryGroup).filter(
                    PotteryGroupMember.pottery_id == pid,
                    PotteryGroup.is_completed == False,
                    PotteryGroup.id != group_id
                ).first()
                if in_other_group:
                    pottery = db.query(Pottery).filter(Pottery.id == pid).first()
                    stored_pottery_ids = [r[0] for r in db.query(StorageRecord.pottery_id).filter(StorageRecord.is_official == True).all()]
                    active_group_members = db.query(PotteryGroupMember.pottery_id).join(PotteryGroup).filter(
                        PotteryGroup.is_completed == False,
                        PotteryGroup.id != group_id
                    ).all()
                    active_pottery_ids = [r[0] for r in active_group_members]
                    excluded_ids = stored_pottery_ids + active_pottery_ids
                    available_potteries = db.query(Pottery).filter(~Pottery.id.in_(excluded_ids)).all()
                    
                    return templates.TemplateResponse("group_form.html", {
                        "request": request,
                        "current_user": current_user,
                        "group": group,
                        "available_potteries": available_potteries,
                        "selected_potteries": [p for p in pottery_ids if p != pid],
                        "error": f"陶片 {pottery.pottery_number if pottery else pid} 已在其他进行中的拼合组中"
                    })

    group.confidence = confidence
    group.organizer = organizer
    group.notes = notes
    group.is_completed = is_completed == "true"

    if not has_official:
        db.query(PotteryGroupMember).filter(PotteryGroupMember.group_id == group_id).delete()
        for pid in pottery_ids:
            member = PotteryGroupMember(group_id=group.id, pottery_id=pid)
            db.add(member)

    db.commit()
    return RedirectResponse(url="/groups", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/groups/{group_id}", response_class=HTMLResponse)
async def group_detail(
    group_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(PotteryGroup).filter(PotteryGroup.id == group_id).first()
    if not group:
        return RedirectResponse(url="/groups", status_code=status.HTTP_303_SEE_OTHER)

    severe_count = 0
    official_count = 0
    for m in group.members:
        if m.pottery.damage_level == "严重":
            severe_count += 1
        if m.pottery.storage_record and m.pottery.storage_record.is_official:
            official_count += 1

    return templates.TemplateResponse("group_detail.html", {
        "request": request,
        "current_user": current_user,
        "group": group,
        "severe_count": severe_count,
        "official_count": official_count
    })


@app.get("/storage", response_class=HTMLResponse)
async def list_storage(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    is_official: Optional[str] = None
):
    query = db.query(StorageRecord)
    if is_official is not None and is_official != "":
        query = query.filter(StorageRecord.is_official == (is_official == "true"))

    records = query.order_by(StorageRecord.storage_date.desc()).all()
    return templates.TemplateResponse("storage.html", {
        "request": request,
        "current_user": current_user,
        "records": records,
        "is_official": is_official
    })


@app.get("/storage/add", response_class=HTMLResponse)
async def add_storage_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    stored_ids = [r[0] for r in db.query(StorageRecord.pottery_id).all()]
    available_potteries = db.query(Pottery).filter(~Pottery.id.in_(stored_ids)).all()

    return templates.TemplateResponse("storage_form.html", {
        "request": request,
        "current_user": current_user,
        "record": None,
        "available_potteries": available_potteries,
        "today": date.today().isoformat()
    })


@app.post("/storage/add")
async def add_storage(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pottery_id: int = Form(...),
    storage_date: date = Form(...),
    location: str = Form(...),
    registrar: str = Form(...),
    notes: str = Form(""),
    is_official: str = Form("false")
):
    existing = db.query(StorageRecord).filter(StorageRecord.pottery_id == pottery_id).first()
    if existing:
        return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)

    if storage_date > date.today():
        stored_ids = [r[0] for r in db.query(StorageRecord.pottery_id).all()]
        available_potteries = db.query(Pottery).filter(~Pottery.id.in_(stored_ids)).all()
        return templates.TemplateResponse("storage_form.html", {
            "request": request,
            "current_user": current_user,
            "record": None,
            "available_potteries": available_potteries,
            "today": date.today().isoformat(),
            "error": "入库日期不能晚于当前日期"
        })

    record = StorageRecord(
        pottery_id=pottery_id,
        storage_date=storage_date,
        location=location,
        registrar=registrar,
        notes=notes,
        is_official=is_official == "true"
    )
    db.add(record)
    db.commit()

    return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    type: str = "all"
):
    results = {
        "potteries": [],
        "groups": [],
        "storage": []
    }

    if q:
        if type in ["all", "pottery"]:
            results["potteries"] = db.query(Pottery).filter(or_(
                Pottery.pottery_number.contains(q),
                Pottery.water_area.contains(q),
                Pottery.decoration_description.contains(q),
                Pottery.material.contains(q)
            )).all()

        if type in ["all", "group"]:
            results["groups"] = db.query(PotteryGroup).filter(or_(
                PotteryGroup.group_number.contains(q),
                PotteryGroup.organizer.contains(q),
                PotteryGroup.notes.contains(q)
            )).all()

        if type in ["all", "storage"]:
            results["storage"] = db.query(StorageRecord).filter(or_(
                StorageRecord.location.contains(q),
                StorageRecord.registrar.contains(q)
            )).join(Pottery).filter(or_(
                Pottery.pottery_number.contains(q),
                StorageRecord.location.contains(q),
                StorageRecord.registrar.contains(q)
            )).all()

    return templates.TemplateResponse("search.html", {
        "request": request,
        "current_user": current_user,
        "q": q,
        "type": type,
        "results": results
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
