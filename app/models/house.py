"""Модель дома."""
from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import relationship
from app.database import Base


class House(Base):
    """Модель дома."""
    
    __tablename__ = "houses"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(500), nullable=False, unique=True, index=True)
    floors = Column(Integer, nullable=True, comment="Этажность дома")
    apartments_count = Column(Integer, nullable=True, comment="Количество квартир")
    
    # Связи
    bindings = relationship("Binding", back_populates="house", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_house_address', 'address'),
    )
    
    def __repr__(self):
        return f"<House(id={self.id}, address='{self.address}', floors={self.floors}, apartments={self.apartments_count})>"

