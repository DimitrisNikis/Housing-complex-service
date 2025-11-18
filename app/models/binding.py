"""Модель привязки дома к жилому комплексу."""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Binding(Base):
    """Модель привязки дома к жилому комплексу."""
    
    __tablename__ = "bindings"
    
    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    housing_complex_id = Column(Integer, ForeignKey("housing_complexes.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    house = relationship("House", back_populates="bindings")
    housing_complex = relationship("HousingComplex", back_populates="bindings")
    
    __table_args__ = (
        UniqueConstraint('house_id', 'housing_complex_id', name='uq_house_housing_complex'),
        Index('idx_binding_house', 'house_id'),
        Index('idx_binding_housing_complex', 'housing_complex_id'),
    )
    
    def __repr__(self):
        return f"<Binding(id={self.id}, house_id={self.house_id}, housing_complex_id={self.housing_complex_id})>"

