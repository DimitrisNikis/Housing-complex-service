"""Pydantic схемы для валидации."""
from app.schemas.housing_complex import HousingComplexBase, HousingComplexCreate, HousingComplexResponse
from app.schemas.house import HouseBase, HouseCreate, HouseResponse
from app.schemas.binding import BindingBase, BindingCreate, BindingResponse, BindingListResponse
from app.schemas.auth import Token, TokenData, UserLogin
from app.schemas.parser import ComplexParsedDTO

__all__ = [
    "HousingComplexBase",
    "HousingComplexCreate",
    "HousingComplexResponse",
    "HouseBase",
    "HouseCreate",
    "HouseResponse",
    "BindingBase",
    "BindingCreate",
    "BindingResponse",
    "BindingListResponse",
    "Token",
    "TokenData",
    "UserLogin",
    "ComplexParsedDTO",
]

