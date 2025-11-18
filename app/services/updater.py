"""Сервис актуализации данных о жилых комплексах."""
from sqlalchemy.orm import Session
from app.models.housing_complex import HousingComplex
from app.services.parser import NashDomParser
from app.utils.hashing import calculate_data_hash
from app.config import get_settings
import logging
import asyncio

logger = logging.getLogger(__name__)
settings = get_settings()


class DataUpdater:
    """Сервис для актуализации данных о ЖК."""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = NashDomParser()
    
    async def update_housing_complexes(self, city: str = None):
        """
        Актуализировать данные о жилых комплексах.
        
        Логика:
        1. Парсим данные из источника (async)
        2. Для каждого ЖК:
           - Если нет в БД по source_url → добавляем
           - Если есть в БД → сравниваем хэш:
             * Хэш изменился → обновляем данные
             * Хэш не изменился → пропускаем
        """
        logger.info("Начало актуализации данных о ЖК")
        
        try:
            # Используем город из настроек, если не указан явно
            search_city = city or settings.PARSER_CITY
            logger.info(f"Поиск ЖК для города: {search_city}")
            
            # Получаем данные из парсера с пагинацией (async)
            # Парсер сам фильтрует по городу через shortAddr регуляркой
            page_size = settings.PARSER_PAGE_SIZE
            max_results = settings.PARSER_MAX_RESULTS if settings.PARSER_MAX_RESULTS > 0 else None
            
            all_complex_dtos = []
            offset = 0
            
            while True:
                # Получаем страницу данных с метаинформацией
                fetch_result = await self.parser.fetch_complexes(
                    offset=offset,
                    limit=page_size,
                    search=search_city,
                    return_metadata=True
                )
                
                page_complexes = fetch_result.complexes
                total_requested = fetch_result.total_requested
                
                if not page_complexes:
                    logger.debug(f"Больше нет данных, остановка пагинации на offset={offset}")
                    break
                
                all_complex_dtos.extend(page_complexes)
                logger.info(
                    f"Загружено страница: {len(page_complexes)} ЖК (запрошено у API: {total_requested}) "
                    f"(offset={offset}, всего: {len(all_complex_dtos)})"
                )
                
                # Проверяем лимит максимального количества результатов
                if max_results and len(all_complex_dtos) >= max_results:
                    all_complex_dtos = all_complex_dtos[:max_results]
                    logger.info(f"Достигнут лимит максимального количества результатов: {max_results}")
                    break
                
                # Если API вернул меньше, чем запрашивали - это последняя страница
                # Важно: проверяем total_requested (до фильтрации), а не len(page_complexes) (после фильтрации)
                if total_requested < page_size:
                    logger.debug(f"API вернул меньше запрошенного ({total_requested} < {page_size}), последняя страница")
                    break
                
                offset += page_size
            
            complex_dtos = all_complex_dtos
            logger.info(f"Всего получено {len(complex_dtos)} ЖК из источника")
            
            added_count = 0
            updated_count = 0
            unchanged_count = 0
            
            # Размер батча для коммитов (чтобы не создавать огромные SQL запросы)
            batch_size = 100
            
            for idx, complex_dto in enumerate(complex_dtos, 1):
                # Формируем source_url для отслеживания изменений
                # Приоритет у уникального идентификатора hobjId, а не у URL изображения
                # hobjRenderPhotoUrl может быть одинаковым для разных ЖК
                if complex_dto.id:
                    # Используем уникальный идентификатор hobjId для формирования source_url
                    source_url = f"{NashDomParser.BASE_URL}/сервисы/kn/{complex_dto.id}"
                elif complex_dto.url:
                    # Fallback на URL только если нет ID
                    source_url = complex_dto.url
                else:
                    logger.warning(f"Не удалось сформировать source_url для ЖК: {complex_dto.name}")
                    continue  # Пропускаем, если нет ID
                
                new_hash = calculate_data_hash(
                    name=complex_dto.name,
                    description=None,  # Описание не входит в ComplexParsedDTO
                    developer=complex_dto.developer
                )
                
                # Ищем существующий ЖК по source_url
                existing = self.db.query(HousingComplex).filter(
                    HousingComplex.source_url == source_url
                ).first()
                
                if existing is None:
                    # Новый ЖК - добавляем
                    new_complex = HousingComplex(
                        name=complex_dto.name,
                        description=None,  # Описание не входит в ComplexParsedDTO
                        developer=complex_dto.developer,
                        source_url=source_url,
                        data_hash=new_hash
                    )
                    self.db.add(new_complex)
                    added_count += 1
                    logger.debug(f"Добавлен новый ЖК: {complex_dto.name}")
                else:
                    # Существующий ЖК - проверяем хэш
                    if existing.data_hash != new_hash:
                        # Данные изменились - обновляем
                        existing.name = complex_dto.name
                        existing.developer = complex_dto.developer
                        existing.data_hash = new_hash
                        updated_count += 1
                        logger.debug(f"Обновлен ЖК: {complex_dto.name}")
                    else:
                        # Данные не изменились - пропускаем
                        unchanged_count += 1
                
                # Коммитим батчами, чтобы не создавать огромные SQL запросы
                if idx % batch_size == 0:
                    try:
                        self.db.commit()
                        logger.debug(f"Закоммичен батч: {idx}/{len(complex_dtos)} записей")
                    except Exception as e:
                        logger.error(f"Ошибка при коммите батча на записи {idx}: {e}")
                        self.db.rollback()
                        raise
            
            # Сохраняем оставшиеся изменения
            try:
                self.db.commit()
                logger.debug(f"Закоммичены оставшиеся изменения")
            except Exception as e:
                logger.error(f"Ошибка при финальном коммите: {e}")
                self.db.rollback()
                raise
            logger.info(
                f"Актуализация завершена. "
                f"Добавлено: {added_count}, Обновлено: {updated_count}, Без изменений: {unchanged_count}"
            )
            
            return {
                "added": added_count,
                "updated": updated_count,
                "unchanged": unchanged_count
            }
            
        except Exception as e:
            logger.error(f"Ошибка при актуализации данных: {e}")
            self.db.rollback()
            raise
    
    async def close(self):
        """Закрыть парсер."""
        await self.parser.close()

