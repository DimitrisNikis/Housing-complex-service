"""API роуты для привязок домов к ЖК."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.housing_complex import HousingComplex
from app.models.house import House
from app.models.binding import Binding
from app.schemas.binding import BindingCreate, BindingResponse, BindingListResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/bindings", tags=["bindings"])


@router.post("", response_model=BindingResponse, status_code=status.HTTP_201_CREATED)
async def create_binding(
    binding: BindingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Создать привязку дома к ЖК.
    
    Автоматически создает дом, если его еще нет (по адресу).
    Если дом с таким адресом уже существует, использует его.
    
    Проверяет:
    - Существование ЖК
    - Отсутствие дубликата привязки
    """
    # Проверяем существование ЖК
    housing_complex = db.query(HousingComplex).filter(
        HousingComplex.id == binding.housing_complex_id
    ).first()
    if not housing_complex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ЖК с ID {binding.housing_complex_id} не найден"
        )
    
    # Ищем или создаем дом по адресу
    house = db.query(House).filter(House.address == binding.address).first()
    
    if not house:
        # Создаем новый дом
        house = House(
            address=binding.address,
            floors=binding.floors,
            apartments_count=binding.apartments_count
        )
        db.add(house)
        db.flush()  # Получаем ID без коммита
    else:
        # Обновляем существующий дом, если переданы новые данные
        if binding.floors is not None:
            house.floors = binding.floors
        if binding.apartments_count is not None:
            house.apartments_count = binding.apartments_count
    
    # Проверяем на дубликат привязки
    existing_binding = db.query(Binding).filter(
        Binding.house_id == house.id,
        Binding.housing_complex_id == binding.housing_complex_id
    ).first()
    if existing_binding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Такая привязка уже существует"
        )
    
    # Создаем привязку
    new_binding = Binding(
        house_id=house.id,
        housing_complex_id=binding.housing_complex_id
    )
    db.add(new_binding)
    db.commit()
    db.refresh(new_binding)
    
    # Загружаем связанные объекты для ответа
    db.refresh(new_binding, ["house", "housing_complex"])
    
    return new_binding


@router.get("", response_model=BindingListResponse)
async def get_bindings(
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(100, ge=1, le=1000, description="Лимит записей"),
    house_id: int = Query(None, description="Фильтр по ID дома"),
    housing_complex_id: int = Query(None, description="Фильтр по ID ЖК"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получить список привязок.
    
    Поддерживает фильтрацию по house_id и housing_complex_id.
    """
    db_query = db.query(Binding)
    
    # Применяем фильтры
    if house_id is not None:
        db_query = db_query.filter(Binding.house_id == house_id)
    if housing_complex_id is not None:
        db_query = db_query.filter(Binding.housing_complex_id == housing_complex_id)
    
    # Подсчитываем общее количество
    total = db_query.count()
    
    # Получаем данные с пагинацией
    bindings = db_query.offset(skip).limit(limit).all()
    
    return BindingListResponse(items=bindings, total=total)


@router.delete("/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_binding(
    binding_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Удалить привязку по ID.
    """
    binding = db.query(Binding).filter(Binding.id == binding_id).first()
    if not binding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Привязка с ID {binding_id} не найдена"
        )
    
    db.delete(binding)
    db.commit()
    
    return None

