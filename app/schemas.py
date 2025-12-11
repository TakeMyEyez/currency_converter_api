from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6)

class UserInDB(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class CurrencyRateBase(BaseModel):
    base_currency: str = Field(..., min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    target_currency: str = Field(..., min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    rate: float = Field(..., gt=0)
    
    @validator('base_currency', 'target_currency')
    def currency_uppercase(cls, v):
        return v.upper()

class CurrencyRateCreate(CurrencyRateBase):
    pass

class CurrencyRateUpdate(BaseModel):
    rate: float = Field(..., gt=0)
    is_active: Optional[bool] = None

class CurrencyRateResponse(CurrencyRateBase):
    id: int
    is_active: bool
    last_updated: datetime
    
    class Config:
        from_attributes = True

class ConversionRequest(BaseModel):
    amount: float = Field(..., gt=0)
    from_currency: str = Field(..., min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    to_currency: str = Field(..., min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    
    @validator('from_currency', 'to_currency')
    def currency_uppercase(cls, v):
        return v.upper()

class ConversionResponse(BaseModel):
    id: int
    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float
    rate_used: float
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ConversionHistoryResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float
    rate_used: float
    timestamp: datetime
    
    class Config:
        from_attributes = True