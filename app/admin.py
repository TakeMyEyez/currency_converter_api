from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import get_current_admin_user
from app.database import get_db
from app.dependencies import templates

admin_router = APIRouter(dependencies=[Depends(get_current_admin_user)])

@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    rates = crud.get_currency_rates(db)
    users = crud.get_users(db)
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "rates": rates,
        "users": users,
        "active_tab": "dashboard"
    })

@admin_router.get("/rates", response_class=HTMLResponse)
async def admin_rates(request: Request, db: Session = Depends(get_db)):
    rates = crud.get_currency_rates(db)
    return templates.TemplateResponse("admin_rates.html", {
        "request": request,
        "rates": rates,
        "active_tab": "rates"
    })

@admin_router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db)):
    users = crud.get_users(db)
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "users": users,
        "active_tab": "users"
    })

@admin_router.post("/api/rates", response_class=HTMLResponse)
async def create_rate(
    request: Request,
    base_currency: str = Form(...),
    target_currency: str = Form(...),
    rate: float = Form(...),
    db: Session = Depends(get_db)
):
    try:
        currency_rate = schemas.CurrencyRateCreate(
            base_currency=base_currency.upper(),
            target_currency=target_currency.upper(),
            rate=rate
        )
        crud.create_currency_rate(db, currency_rate)
        return RedirectResponse(url="/admin/rates?success=Курс успешно добавлен", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/rates?error={str(e)}", status_code=303)

@admin_router.post("/api/rates/{rate_id}/toggle", response_class=HTMLResponse)
async def toggle_rate(
    rate_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        rate = crud.get_currency_rate(db, rate_id)
        if not rate:
            return RedirectResponse(url="/admin/rates?error=Курс не найден", status_code=303)
        
        rate.is_active = not rate.is_active
        db.commit()
        return RedirectResponse(url="/admin/rates?success=Статус курса изменен", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/rates?error={str(e)}", status_code=303)

@admin_router.post("/api/rates/{rate_id}/delete", response_class=HTMLResponse)
async def delete_rate(
    rate_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        success = crud.delete_currency_rate(db, rate_id)
        if not success:
            return RedirectResponse(url="/admin/rates?error=Курс не найден", status_code=303)
        return RedirectResponse(url="/admin/rates?success=Курс успешно удален", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/rates?error={str(e)}", status_code=303)

@admin_router.post("/api/rates/{rate_id}/update", response_class=HTMLResponse)
async def update_rate(
    rate_id: int,
    request: Request,
    rate: float = Form(...),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    try:
        current_rate = crud.get_currency_rate(db, rate_id)
        if not current_rate:
            return RedirectResponse(url="/admin/rates?error=Курс не найден", status_code=303)
        
        rate_update = schemas.CurrencyRateUpdate(
            rate=rate,
            is_active=is_active
        )
        updated_rate = crud.update_currency_rate(db, rate_id, rate_update)
        if not updated_rate:
            return RedirectResponse(url="/admin/rates?error=Курс не найден", status_code=303)
        return RedirectResponse(url="/admin/rates?success=Курс успешно обновлен", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/rates?error={str(e)}", status_code=303)

@admin_router.post("/api/users/{user_id}/toggle-active", response_class=HTMLResponse)
async def toggle_user_active(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = crud.get_user(db, user_id)
        if not user:
            return RedirectResponse(url="/admin/users?error=Пользователь не найден", status_code=303)
        
        current_user = request.state.user if hasattr(request, 'state') and hasattr(request.state, 'user') else None
        if current_user and user.id == current_user.id:
            return RedirectResponse(url="/admin/users?error=Нельзя изменить статус самого себя", status_code=303)
        
        user.is_active = not user.is_active
        db.commit()
        return RedirectResponse(url="/admin/users?success=Статус пользователя изменен", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/users?error={str(e)}", status_code=303)

@admin_router.post("/api/users/{user_id}/toggle-admin", response_class=HTMLResponse)
async def toggle_user_admin(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = crud.get_user(db, user_id)
        if not user:
            return RedirectResponse(url="/admin/users?error=Пользователь не найден", status_code=303)
        
        current_user = request.state.user if hasattr(request, 'state') and hasattr(request.state, 'user') else None
        if current_user and user.id == current_user.id:
            return RedirectResponse(url="/admin/users?error=Нельзя изменить права самого себя", status_code=303)
        
        user.is_admin = not user.is_admin
        db.commit()
        return RedirectResponse(url="/admin/users?success=Права пользователя изменены", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/users?error={str(e)}", status_code=303)

@admin_router.post("/api/users/{user_id}/delete", response_class=HTMLResponse)
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        current_user = request.state.user if hasattr(request, 'state') and hasattr(request.state, 'user') else None
        if current_user and user_id == current_user.id:
            return RedirectResponse(url="/admin/users?error=Нельзя удалить самого себя", status_code=303)
        
        success = crud.delete_user(db, user_id)
        if not success:
            return RedirectResponse(url="/admin/users?error=Пользователь не найден", status_code=303)
        return RedirectResponse(url="/admin/users?success=Пользователь успешно удален", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/admin/users?error={str(e)}", status_code=303)
    