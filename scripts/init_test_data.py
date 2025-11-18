"""Скрипт для инициализации тестовых данных."""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.house import House
from app.models.housing_complex import HousingComplex
from app.services.updater import DataUpdater


def init_test_data():
    """Инициализировать тестовые данные."""
    db: Session = SessionLocal()
    try:
        # Создаем тестовые дома
        houses_data = [
            "г. Москва, ул. Солнечная, д. 1",
            "г. Москва, ул. Солнечная, д. 2",
            "г. Москва, пр-т Центральный, д. 10",
            "г. Москва, пр-т Центральный, д. 12",
            "г. Москва, Лесная ул., д. 5",
        ]
        
        created_houses = 0
        for address in houses_data:
            existing = db.query(House).filter(House.address == address).first()
            if not existing:
                house = House(address=address)
                db.add(house)
                created_houses += 1
        
        db.commit()
        print(f"Создано домов: {created_houses}")
        
        # Запускаем актуализацию для создания ЖК
        updater = DataUpdater(db)
        result = updater.update_housing_complexes()
        print(f"Актуализация ЖК: добавлено {result['added']}, обновлено {result['updated']}, без изменений {result['unchanged']}")
        
        # Закрываем парсер
        updater.close()
        
        print("Инициализация тестовых данных завершена")
        
    except Exception as e:
        print(f"Ошибка при инициализации данных: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_test_data()

