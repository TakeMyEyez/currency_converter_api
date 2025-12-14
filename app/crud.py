from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app import models, schemas
from app.auth import get_password_hash
from datetime import datetime, timedelta

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = get_user(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

def get_currency_rate(db: Session, rate_id: int):
    return db.query(models.CurrencyRate).filter(models.CurrencyRate.id == rate_id).first()

def get_currency_rates(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.CurrencyRate).offset(skip).limit(limit).all()

def get_active_currency_rate(db: Session, base_currency: str, target_currency: str):
    return db.query(models.CurrencyRate).filter(
        and_(
            models.CurrencyRate.base_currency == base_currency,
            models.CurrencyRate.target_currency == target_currency,
            models.CurrencyRate.is_active == True
        )
    ).first()

def create_currency_rate(db: Session, currency_rate: schemas.CurrencyRateCreate):
    existing_rate = get_active_currency_rate(db, currency_rate.base_currency, currency_rate.target_currency)
    if existing_rate:
        existing_rate.is_active = False
        db.commit()
    
    db_currency_rate = models.CurrencyRate(**currency_rate.dict())
    db.add(db_currency_rate)
    db.commit()
    db.refresh(db_currency_rate)
    return db_currency_rate

def update_currency_rate(db: Session, rate_id: int, rate_update: schemas.CurrencyRateUpdate):
    db_rate = get_currency_rate(db, rate_id)
    if db_rate:
        for field, value in rate_update.dict(exclude_unset=True).items():
            setattr(db_rate, field, value)
        db.commit()
        db.refresh(db_rate)
    return db_rate

def delete_currency_rate(db: Session, rate_id: int):
    db_currency_rate = get_currency_rate(db, rate_id)
    if db_currency_rate:
        db.delete(db_currency_rate)
        db.commit()
    return db_currency_rate

def create_conversion(db: Session, conversion: schemas.ConversionResponse, user_id: int):
    db_conversion = models.ConversionHistory(
        user_id=user_id,
        amount=conversion.amount,
        from_currency=conversion.from_currency,
        to_currency=conversion.to_currency,
        converted_amount=conversion.converted_amount,
        rate_used=conversion.rate_used
    )
    db.add(db_conversion)
    db.commit()
    db.refresh(db_conversion)
    return db_conversion

def get_user_conversions(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.ConversionHistory).filter(
        models.ConversionHistory.user_id == user_id
    ).order_by(models.ConversionHistory.timestamp.desc()).offset(skip).limit(limit).all()

def get_conversion_by_id(db: Session, conversion_id: int):
    return db.query(models.ConversionHistory).filter(models.ConversionHistory.id == conversion_id).first()

def get_all_conversions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ConversionHistory).order_by(
        models.ConversionHistory.timestamp.desc()
    ).offset(skip).limit(limit).all()