"""Модели базы данных."""
from app.models.housing_complex import HousingComplex
from app.models.house import House
from app.models.binding import Binding
from app.models.user import User

__all__ = ["HousingComplex", "House", "Binding", "User"]

