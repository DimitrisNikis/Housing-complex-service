"""Pydantic схемы для парсинга данных из внешних источников."""
from pydantic import BaseModel, Field
from typing import Optional


class ComplexParsedDTO(BaseModel):
    """
    Модель данных о жилом комплексе, полученных из HTML парсинга наш.дом.рф.
    
    Используется для валидации и преобразования данных из HTML страницы.
    Все поля, кроме id, name и address, опциональны.
    """
    id: str = Field(..., description="Идентификатор жилого комплекса")
    name: str = Field(..., description="Название жилого комплекса")
    address: str = Field(..., description="Адрес жилого комплекса")
    developer: Optional[str] = Field(None, description="Застройщик")
    status: Optional[str] = Field(None, description="Статус жилого комплекса")
    url: Optional[str] = Field(None, description="URL страницы жилого комплекса на сайте")
    latitude: Optional[float] = Field(None, description="Широта (координата)")
    longitude: Optional[float] = Field(None, description="Долгота (координата)")
    
    class Config:
        """Конфигурация модели."""
        # Игнорируем дополнительные поля, которых нет в модели
        extra = "ignore"
