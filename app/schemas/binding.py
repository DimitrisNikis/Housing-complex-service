"""Pydantic схемы для привязок."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from app.schemas.house import HouseResponse
from app.schemas.housing_complex import HousingComplexResponse


class BindingCreate(BaseModel):
    """Схема для создания привязки."""
    housing_complex_id: int = Field(..., description="ID жилого комплекса")
    address: str = Field(..., max_length=500, description="Адрес дома")
    floors: Optional[int] = Field(None, description="Этажность дома")
    apartments_count: Optional[int] = Field(None, description="Количество квартир")


class BindingBase(BaseModel):
    """Базовая схема привязки."""
    house_id: int = Field(..., description="ID дома")
    housing_complex_id: int = Field(..., description="ID жилого комплекса")


class BindingResponse(BindingBase):
    """Схема ответа с данными привязки."""
    id: int
    created_at: datetime
    house: Optional[HouseResponse] = None
    housing_complex: Optional[HousingComplexResponse] = None
    
    class Config:
        from_attributes = True


class BindingListResponse(BaseModel):
    """Схема списка привязок."""
    items: List[BindingResponse]
    total: int

