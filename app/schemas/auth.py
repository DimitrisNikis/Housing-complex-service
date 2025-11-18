"""Pydantic схемы для авторизации."""
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Схема токена."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Схема данных токена."""
    username: Optional[str] = None


class UserLogin(BaseModel):
    """Схема входа пользователя."""
    username: str
    password: str


class UserCreate(BaseModel):
    """Схема создания пользователя."""
    username: str
    password: str


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""
    id: int
    username: str
    is_active: bool
    
    class Config:
        from_attributes = True

