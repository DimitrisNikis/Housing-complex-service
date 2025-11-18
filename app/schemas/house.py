"""Pydantic схемы для домов."""
from pydantic import BaseModel, Field
from typing import Optional


class HouseBase(BaseModel):
    """Базовая схема дома."""
    address: str = Field(..., max_length=500, description="Адрес дома")
    floors: Optional[int] = Field(None, description="Этажность дома")
    apartments_count: Optional[int] = Field(None, description="Количество квартир")


class HouseCreate(HouseBase):
    """Схема для создания дома."""
    pass


class HouseResponse(HouseBase):
    """Схема ответа с данными дома."""
    id: int
    
    class Config:
        from_attributes = True

