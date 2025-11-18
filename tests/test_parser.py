"""Тестовый скрипт для проверки парсера."""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.services.parser import NashDomParser

# Настройка логирования для видимости всех сообщений
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_parser():
    """Тестирование парсера."""
    parser = NashDomParser()
    
    try:
        print("=" * 60)
        print("Тестирование парсера наш.дом.рф")
        print("=" * 60)
        
        # Тест 1: Базовый запрос с небольшим лимитом
        print("\n1. Тест: получение первых 10 ЖК")
        print("-" * 60)
        try:
            complexes = await parser.fetch_complexes(offset=0, limit=10)
            print(f"   ✓ Получено ЖК: {len(complexes)}")
            
            if complexes:
                print("\n   Первые 3 ЖК:")
                for i, complex_dto in enumerate(complexes[:3], 1):
                    print(f"\n   {i}. {complex_dto.name}")
                    print(f"      ID: {complex_dto.id}")
                    print(f"      Адрес: {complex_dto.address}")
                    print(f"      Застройщик: {complex_dto.developer or 'Не указан'}")
                    print(f"      Статус: {complex_dto.status or 'Не указан'}")
                    if complex_dto.url:
                        print(f"      URL: {complex_dto.url}")
                    if complex_dto.latitude and complex_dto.longitude:
                        print(f"      Координаты: {complex_dto.latitude}, {complex_dto.longitude}")
            else:
                print("   ⚠ Нет данных для отображения")
        except Exception as e:
            print(f"   ✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # Тест 2: Поиск
        print("\n2. Тест: поиск по запросу 'Москва'")
        print("-" * 60)
        try:
            search_complexes = await parser.fetch_complexes(offset=0, limit=5, search="Москва")
            print(f"   ✓ Найдено ЖК: {len(search_complexes)}")
            
            if search_complexes:
                print("\n   Найденные ЖК:")
                for i, complex_dto in enumerate(search_complexes[:3], 1):
                    print(f"   {i}. {complex_dto.name} - {complex_dto.address}")
        except Exception as e:
            print(f"   ✗ Ошибка: {e}")
        
        # Тест 3: Пагинация
        print("\n3. Тест: пагинация (offset=10, limit=5)")
        print("-" * 60)
        try:
            paginated = await parser.fetch_complexes(offset=10, limit=5)
            print(f"   ✓ Получено ЖК: {len(paginated)}")
            
            if paginated:
                print("\n   Элементы со сдвигом:")
                for i, complex_dto in enumerate(paginated[:2], 1):
                    print(f"   {i}. {complex_dto.name}")
        except Exception as e:
            print(f"   ✗ Ошибка: {e}")
        
        # Тест 4: Проверка структуры данных
        print("\n4. Тест: проверка структуры данных")
        print("-" * 60)
        try:
            test_complexes = await parser.fetch_complexes(offset=0, limit=1)
            if test_complexes:
                complex_dto = test_complexes[0]
                print(f"   ✓ Обязательные поля:")
                print(f"      - id: {complex_dto.id} (тип: {type(complex_dto.id).__name__})")
                print(f"      - name: {complex_dto.name} (тип: {type(complex_dto.name).__name__})")
                print(f"      - address: {complex_dto.address} (тип: {type(complex_dto.address).__name__})")
                print(f"   ✓ Опциональные поля:")
                print(f"      - developer: {complex_dto.developer} (тип: {type(complex_dto.developer).__name__ if complex_dto.developer else 'None'})")
                print(f"      - status: {complex_dto.status} (тип: {type(complex_dto.status).__name__ if complex_dto.status else 'None'})")
                print(f"      - url: {complex_dto.url} (тип: {type(complex_dto.url).__name__ if complex_dto.url else 'None'})")
                print(f"      - latitude: {complex_dto.latitude} (тип: {type(complex_dto.latitude).__name__ if complex_dto.latitude else 'None'})")
                print(f"      - longitude: {complex_dto.longitude} (тип: {type(complex_dto.longitude).__name__ if complex_dto.longitude else 'None'})")
            else:
                print("   ⚠ Нет данных для проверки структуры")
        except Exception as e:
            print(f"   ✗ Ошибка: {e}")
        
        print("\n" + "=" * 60)
        print("Тестирование завершено!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(test_parser())

