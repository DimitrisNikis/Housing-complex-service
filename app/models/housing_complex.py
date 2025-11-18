"""Модель жилого комплекса."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import hashlib


class HousingComplex(Base):
    """Модель жилого комплекса."""
    
    __tablename__ = "housing_complexes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    developer = Column(String(300))
    # URL источника для отслеживания изменений
    source_url = Column(String(1000), unique=True, nullable=False, index=True)
    # Хэш значимых полей для отслеживания изменений
    data_hash = Column(String(64), nullable=False, index=True)
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    bindings = relationship("Binding", back_populates="housing_complex", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_housing_complex_data_hash', 'data_hash'),
    )
    
    @classmethod
    def calculate_hash(cls, name: str, description: str = None, developer: str = None) -> str:
        """Вычислить хэш значимых полей."""
        data_str = f"{name}|{description or ''}|{developer or ''}"
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    def __repr__(self):
        return f"<HousingComplex(id={self.id}, name='{self.name}')>"

