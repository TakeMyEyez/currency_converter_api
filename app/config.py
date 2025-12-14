import os
from typing import Optional

class Settings:
    PROJECT_NAME: str = "Currency Converter API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./currency_converter.db")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    def __init__(self):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            self.DATABASE_URL = os.getenv("DATABASE_URL", self.DATABASE_URL)
            self.SECRET_KEY = os.getenv("SECRET_KEY", self.SECRET_KEY)
            self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(self.ACCESS_TOKEN_EXPIRE_MINUTES)))
        except ImportError:
            pass

settings = Settings()