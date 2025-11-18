"""Pydantic схемы для жилых комплексов."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class HousingComplexBase(BaseModel):
    """Базовая схема жилого комплекса."""
    name: str = Field(..., max_length=500, description="Название ЖК")
    description: Optional[str] = Field(None, description="Описание ЖК")
    developer: Optional[str] = Field(None, max_length=300, description="Застройщик")


class HousingComplexCreate(HousingComplexBase):
    """Схема для создания ЖК."""
    source_url: str = Field(..., max_length=1000, description="URL источника данных")


class HousingComplexResponse(HousingComplexBase):
    """Схема ответа с данными ЖК."""
    id: int
    source_url: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

