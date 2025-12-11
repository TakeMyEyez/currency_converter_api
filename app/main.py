from fastapi import FastAPI, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import os
import random

from app.dependencies import templates
from app.database import engine, get_db, Base, SessionLocal
from app import models, schemas, crud, auth
from app.config import settings
from app.admin import admin_router

Base.metadata.create_all(bind=engine)

def create_initial_admin():
    db = SessionLocal()
    try:
        ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
        ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
        
        admin_user = crud.get_user_by_username(db, username=ADMIN_USERNAME)
        
        if not admin_user:
            user_create = schemas.UserCreate(
                username=ADMIN_USERNAME,
                password=ADMIN_PASSWORD
            )
            admin_user = crud.create_user(db=db, user=user_create)
            print(f"✅ Администратор '{ADMIN_USERNAME}' успешно создан!")
        
        if not admin_user.is_admin:
            admin_user.is_admin = True
            db.commit()
            print(f"✅ Пользователь '{ADMIN_USERNAME}' получил права администратора!")
            
    except Exception as e:
        print(f"❌ Ошибка при создании админа: {str(e)}")
    finally:
        db.close()

create_initial_admin()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(admin_router, prefix="/admin", tags=["admin"])

async def get_exchange_rate(base_currency: str, target_currency: str, db: Session):
    rate = crud.get_active_currency_rate(db, base_currency.upper(), target_currency.upper())
    if rate:
        return rate.rate
    
    reverse_rate = crud.get_active_currency_rate(db, target_currency.upper(), base_currency.upper())
    if reverse_rate:
        return 1 / reverse_rate.rate
    
    base = base_currency.upper()
    target = target_currency.upper()

    demo_rates = {
        ("USD", "EUR"): 0.92,
        ("EUR", "USD"): 1.08,
        ("USD", "RUB"): 90.0,
        ("EUR", "RUB"): 98.0,
        ("USD", "GBP"): 0.79,
        ("GBP", "USD"): 1.27,
        ("USD", "JPY"): 148.0,
        ("JPY", "USD"): 0.0068,
        ("EUR", "GBP"): 0.86,
        ("GBP", "EUR"): 1.16,
        ("RUB", "USD"): 0.0111,
        ("RUB", "EUR"): 0.0102,
    }
    
    if (base, target) in demo_rates:
        crud.create_currency_rate(db, schemas.CurrencyRateCreate(
            base_currency=base,
            target_currency=target,
            rate=demo_rates[(base, target)]
        ))
        return demo_rates[(base, target)]
    elif base == target:
        return 1.0
    else:
        demo_rate = round(random.uniform(0.5, 2.0), 4)
        crud.create_currency_rate(db, schemas.CurrencyRateCreate(
            base_currency=base,
            target_currency=target,
            rate=demo_rate
        ))
        return demo_rate

@app.middleware("http")
async def check_token_middleware(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path in ["/", "/login", "/register", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]:
        return await call_next(request)
    
    if request.url.path.startswith("/api/"):
        return await call_next(request)
    
    auth_header = request.cookies.get("access_token")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        request.scope['headers'].append((b'authorization', f'Bearer {token}'.encode()))
    
    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверное имя пользователя или пароль"
        })
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=1800)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != password_confirm:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Пароли не совпадают"
        })
    
    if crud.get_user_by_username(db, username=username):
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Имя пользователя уже занято"
        })
    
    user_create = schemas.UserCreate(username=username, password=password)
    user = crud.create_user(db=db, user=user_create)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, max_age=1800)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: schemas.UserInDB = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    recent_conversions = crud.get_user_conversions(db, current_user.id, limit=10)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "conversions": recent_conversions
    })

@app.get("/convert", response_class=HTMLResponse)
async def convert_page(
    request: Request,
    current_user: schemas.UserInDB = Depends(auth.get_current_active_user)
):
    return templates.TemplateResponse("convert.html", {
        "request": request,
        "user": current_user
    })

@app.post("/convert")
async def convert_currency_form(
    request: Request,
    amount: float = Form(...),
    from_currency: str = Form(...),
    to_currency: str = Form(...),
    current_user: schemas.UserInDB = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        rate = await get_exchange_rate(from_currency, to_currency, db)
        converted_amount = amount * rate
        
        conversion_response = schemas.ConversionResponse(
            id=0,
            amount=amount,
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            converted_amount=round(converted_amount, 2),
            rate_used=rate,
            timestamp=datetime.now()
        )
        
        db_conversion = crud.create_conversion(db, conversion_response, current_user.id)
        
        return templates.TemplateResponse("convert.html", {
            "request": request,
            "user": current_user,
            "result": {
                "amount": amount,
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "converted_amount": round(converted_amount, 2),
                "rate": rate
            },
            "success": "Конвертация успешно выполнена!"
        })
    except Exception as e:
        return templates.TemplateResponse("convert.html", {
            "request": request,
            "user": current_user,
            "error": f"Ошибка: {str(e)}",
            "success": False
        })

@app.get("/history", response_class=HTMLResponse)
async def history_page(
    request: Request,
    current_user: schemas.UserInDB = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    conversions = crud.get_user_conversions(db, current_user.id)
    return templates.TemplateResponse("history.html", {
        "request": request,
        "conversions": conversions,
        "user": current_user
    })

@app.post("/api/v1/auth/register", response_model=schemas.UserInDB)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    return crud.create_user(db=db, user=user)

@app.post("/api/v1/auth/login", response_model=schemas.Token)
def login_api(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/users/me", response_model=schemas.UserInDB)
async def read_users_me(current_user: schemas.UserInDB = Depends(auth.get_current_active_user)):
    return current_user

@app.post("/api/v1/convert", response_model=schemas.ConversionResponse)
async def convert_currency_api(
    conversion: schemas.ConversionRequest,
    current_user: schemas.UserInDB = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        rate = await get_exchange_rate(conversion.from_currency, conversion.to_currency, db)
        converted_amount = conversion.amount * rate
        
        conversion_response = schemas.ConversionResponse(
            id=0,
            amount=conversion.amount,
            from_currency=conversion.from_currency.upper(),
            to_currency=conversion.to_currency.upper(),
            converted_amount=round(converted_amount, 2),
            rate_used=rate,
            timestamp=datetime.now()
        )
        
        db_conversion = crud.create_conversion(db, conversion_response, current_user.id)
        conversion_response.id = db_conversion.id
        
        return conversion_response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/conversions/history", response_model=List[schemas.ConversionHistoryResponse])
async def get_conversion_history_api(
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.UserInDB = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    conversions = crud.get_user_conversions(db, current_user.id, skip=skip, limit=limit)
    return conversions

@app.get("/api/v1/rates", response_model=List[schemas.CurrencyRateResponse])
def get_currency_rates_api(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    rates = crud.get_currency_rates(db, skip=skip, limit=limit)
    return rates

@app.get("/api/v1/rates/{base_currency}/{target_currency}")
def get_specific_rate_api(
    base_currency: str,
    target_currency: str,
    db: Session = Depends(get_db)
):
    rate = crud.get_active_currency_rate(db, base_currency.upper(), target_currency.upper())
    if not rate:
        raise HTTPException(status_code=404, detail="Currency rate not found")
    return rate

@app.post("/api/v1/admin/rates", response_model=schemas.CurrencyRateResponse)
def create_currency_rate_api(
    currency_rate: schemas.CurrencyRateCreate,
    current_user: schemas.UserInDB = Depends(auth.get_current_admin_user),
    db: Session = Depends(get_db)
):
    return crud.create_currency_rate(db=db, currency_rate=currency_rate)

@app.put("/api/v1/admin/rates/{rate_id}", response_model=schemas.CurrencyRateResponse)
def update_currency_rate_api(
    rate_id: int,
    rate_update: schemas.CurrencyRateUpdate,
    current_user: schemas.UserInDB = Depends(auth.get_current_admin_user),
    db: Session = Depends(get_db)
):
    rate = crud.update_currency_rate(db=db, rate_id=rate_id, rate_update=rate_update)
    if rate is None:
        raise HTTPException(status_code=404, detail="Currency rate not found")
    return rate

@app.delete("/api/v1/admin/rates/{rate_id}")
def delete_currency_rate_api(
    rate_id: int,
    current_user: schemas.UserInDB = Depends(auth.get_current_admin_user),
    db: Session = Depends(get_db)
):
    success = crud.delete_currency_rate(db=db, rate_id=rate_id)
    if not success:
        raise HTTPException(status_code=404, detail="Currency rate not found")
    return {"message": "Currency rate deleted successfully"}

@app.get("/api/v1/admin/users", response_model=List[schemas.UserInDB])
def get_all_users_api(
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.UserInDB = Depends(auth.get_current_admin_user),
    db: Session = Depends(get_db)
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found"}
        )
    return templates.TemplateResponse("404.html", {"request": request})

@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error"}
        )
    return RedirectResponse("/", status_code=303)