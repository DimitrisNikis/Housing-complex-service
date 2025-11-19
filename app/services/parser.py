"""Парсер данных о жилых комплексах с наш.дом.рф через API с использованием Playwright и Stealth."""
from typing import List, Optional, NamedTuple
from pydantic import ValidationError
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright_stealth import Stealth
import logging
from urllib.parse import quote
import json
import re

from app.schemas.parser import ComplexParsedDTO
from app.config import get_settings


class FetchResult(NamedTuple):
    """Результат запроса парсера с метаинформацией."""
    complexes: List[ComplexParsedDTO]  # Отфильтрованные результаты
    total_requested: int  # Количество записей, запрошенных у API (до фильтрации)

logger = logging.getLogger(__name__)
settings = get_settings()


class NashDomParser:
    """
    Парсер для сайта наш.дом.рф.
    
    Использует Playwright с Stealth для обхода антибот-системы ServicePipe.
    Выполняет API запросы через page.evaluate() с JavaScript fetch для максимальной 
    имитации реального браузера.
    
    Не выполняет сохранение в БД - только возвращает список DTO.
    """
    
    # Используем IDN (Punycode) версию URL для совместимости
    BASE_URL = "https://xn--80az8a.xn--d1aqf.xn--p1ai"
    _SEARCH_PATH = "/сервисы/kn"
    SEARCH_URL = f"{BASE_URL}{quote(_SEARCH_PATH, safe='/')}"
    
    # Известный API endpoint для получения ЖК
    API_ENDPOINT = f"{BASE_URL}/сервисы/api/kn/object"
    
    def __init__(self, headless: Optional[bool] = None):
        """
        Инициализация парсера с Playwright и Stealth.
        
        Args:
            headless: Запуск браузера в headless режиме (по умолчанию из настроек)
        """
        self.headless = headless if headless is not None else settings.PARSER_HEADLESS
        self.browser_timeout = settings.PARSER_BROWSER_TIMEOUT
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def _init_browser(self):
        """Инициализировать браузер Playwright с Stealth."""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            # Создаём контекст с реалистичными параметрами браузера
            self.context = await self.browser.new_context(
                locale="ru-RU",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1400, "height": 900},
                timezone_id='Europe/Moscow',
            )
            
            logger.info(f"Браузер Playwright инициализирован (headless={self.headless})")
    
    async def _apply_stealth(self, page: Page):
        """Применить Stealth для обхода детекции."""
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        logger.debug("Stealth применён к странице")
    
    async def _wait_for_antibot(self, page: Page):
        """Дождаться обхода антибот-системы."""
        # Ждём загрузки страницы
        await page.goto(self.SEARCH_URL, wait_until="networkidle", timeout=60000)
        
        # Ждём 6 секунд для работы антибота (как в примере)
        await page.wait_for_timeout(6000)
        
        # Пробуем дождаться исчезновения спиннера
        try:
            await page.wait_for_selector(
                ".spinner, #id_spinner",
                state="detached",
                timeout=8000
            )
            logger.debug("Индикатор загрузки антибота исчез")
        except Exception as e:
            logger.debug(f"Индикатор загрузки антибота не исчез или уже исчез: {e}")
    
    def _build_api_url(self, offset: int = 0, limit: int = 100, search: str = "") -> str:
        """Построить URL API запроса с параметрами."""
        params = []
        
        if offset is not None:
            params.append(f"offset={offset}")
        if limit is not None:
            params.append(f"limit={limit}")
        if search:
            params.append(f"search={quote(search)}")
            params.append(f"searchValue={quote(search)}")
        
        query_string = "&".join(params)
        return f"{self.API_ENDPOINT}?{query_string}" if params else self.API_ENDPOINT
    
    def _extract_complexes_from_json(self, json_data) -> List[dict]:
        """
        Извлечь список ЖК из JSON ответа API.
        
        Структура ответа: {"data": {"list": [...]}}
        
        Args:
            json_data: Распарсенный JSON ответ
            
        Returns:
            Список словарей с данными ЖК
        """
        complexes_list = []
        
        # Структура согласно примеру: result['data']['list']
        if isinstance(json_data, dict):
            if 'data' in json_data and isinstance(json_data['data'], dict):
                if 'list' in json_data['data']:
                    complexes_list = json_data['data']['list']
                    logger.debug("JSON ответ - объект с полем data.list")
                else:
                    # Если нет 'list', но есть 'data' как список
                    if isinstance(json_data['data'], list):
                        complexes_list = json_data['data']
                        logger.debug("JSON ответ - объект с полем data (список)")
            elif 'data' in json_data and isinstance(json_data['data'], list):
                complexes_list = json_data['data']
                logger.debug("JSON ответ - объект с полем data (список)")
            elif 'list' in json_data and isinstance(json_data['list'], list):
                complexes_list = json_data['list']
                logger.debug("JSON ответ - объект с полем list")
            # Если JSON - прямой массив
            elif isinstance(json_data, list):
                complexes_list = json_data
                logger.debug("JSON ответ - прямой массив объектов")
        
        if not complexes_list:
            logger.warning(f"Не удалось извлечь список ЖК из JSON. Структура: {type(json_data)}")
            if isinstance(json_data, dict):
                logger.debug(f"Ключи в JSON: {list(json_data.keys())}")
                if 'data' in json_data:
                    logger.debug(f"Тип data: {type(json_data['data'])}, ключи: {list(json_data['data'].keys()) if isinstance(json_data['data'], dict) else 'list'}")
        
        return complexes_list
    
    def _filter_by_city(self, complexes_list: List[dict], city: str) -> List[dict]:
        """
        Фильтровать список ЖК по городу, используя поле shortAddr и регулярное выражение.
        
        Ищет паттерн "г. {город}" или "{город}" в поле shortAddr.
        
        Args:
            complexes_list: Список сырых JSON объектов ЖК
            city: Название города для фильтрации (например, "Москва")
            
        Returns:
            Отфильтрованный список ЖК
        """
        if not city or not complexes_list:
            return complexes_list
        
        # Нормализуем название города (убираем лишние пробелы, приводим к нижнему регистру для поиска)
        city_normalized = city.strip().lower()
        
        # Создаём паттерн для поиска: "г. {город}" или просто "{город}"
        # Используем \b для границ слов, чтобы не находить подстроки
        city_escaped = re.escape(city_normalized)
        pattern = re.compile(
            r'(?:г\.\s*)?' + city_escaped + r'(?:\s|$|,)',
            re.IGNORECASE
        )
        
        filtered = []
        for item in complexes_list:
            short_addr = item.get('shortAddr', '')
            if short_addr and pattern.search(short_addr):
                filtered.append(item)
            else:
                logger.debug(f"ЖК исключён из фильтрации по городу '{city}': shortAddr='{short_addr}'")
        
        return filtered
    
    def _map_json_to_dto(self, item: dict) -> dict:
        """
        Маппинг полей из JSON API в формат ComplexParsedDTO.
        
        Маппинг полей API наш.дом.рф:
        - hobjId → id (идентификатор объекта)
        - objCommercNm → name (название ЖК)
        - shortAddr → address (адрес ЖК, используется для фильтрации по городу)
        - developer.shortName/fullName → developer (застройщик как строка)
        - siteStatus → status (статус ЖК)
        - latitude/longitude → координаты (уже в нужном формате)
        - hobjId → url (формируется или используется hobjRenderPhotoUrl)
        
        Args:
            item: Элемент из JSON ответа API
            
        Returns:
            Словарь для создания ComplexParsedDTO
        """
        # Извлекаем ID: используем hobjId из API наш.дом.рф
        hobj_id = item.get('hobjId', item.get('id', ''))
        mapped_id = str(hobj_id) if hobj_id else ''
        
        # Извлекаем название: используем objCommercNm
        mapped_name = item.get('objCommercNm', item.get('name', item.get('title', 'Неизвестный ЖК')))
        if not mapped_name or mapped_name == 'Неизвестный ЖК':
            mapped_name = 'Неизвестный ЖК'
        
        # Извлекаем адрес: используем shortAddr из JSON
        mapped_address = item.get('shortAddr', item.get('objAddr', item.get('address', item.get('location', None))))
        if not mapped_address:
            mapped_address = None
        
        # Извлекаем застройщика: developer - это объект, нужно извлечь строку
        dev_obj = item.get('developer')
        mapped_developer = None
        if isinstance(dev_obj, dict):
            # Извлекаем shortName или fullName из объекта developer
            mapped_developer = dev_obj.get('shortName') or dev_obj.get('fullName')
        elif isinstance(dev_obj, str):
            mapped_developer = dev_obj
        
        # Извлекаем статус: используем siteStatus
        mapped_status = item.get('siteStatus', item.get('status', item.get('state')))
        
        # Формируем URL: используем hobjRenderPhotoUrl или формируем из hobjId
        mapped_url = item.get('hobjRenderPhotoUrl')
        if not mapped_url and hobj_id:
            mapped_url = f"{self.BASE_URL}/сервисы/kn/{hobj_id}"
        
        # Координаты уже в правильном формате в JSON
        mapped_latitude = item.get('latitude', item.get('lat'))
        mapped_longitude = item.get('longitude', item.get('lng', item.get('lon')))
        
        # Если координаты в виде объекта или массива (fallback)
        if not mapped_latitude or not mapped_longitude:
            if 'coordinates' in item:
                coords = item['coordinates']
                if isinstance(coords, dict):
                    mapped_latitude = coords.get('lat', coords.get('latitude')) or mapped_latitude
                    mapped_longitude = coords.get('lng', coords.get('lon', coords.get('longitude'))) or mapped_longitude
                elif isinstance(coords, list) and len(coords) >= 2:
                    mapped_longitude = coords[0]  # Обычно [lng, lat]
                    mapped_latitude = coords[1]
        
        mapped = {
            'id': mapped_id,
            'name': mapped_name,
            'address': mapped_address,
            'developer': mapped_developer,
            'status': mapped_status,
            'url': mapped_url,
            'latitude': mapped_latitude,
            'longitude': mapped_longitude,
        }
        
        return mapped
    
    async def fetch_complexes(
        self,
        offset: int = 0,
        limit: int = 100,
        search: str = "",
        return_metadata: bool = False
    ) -> List[ComplexParsedDTO] | FetchResult:
        """
        Получить список жилых комплексов через API с использованием Playwright и Stealth.
        
        Процесс:
        1. Открывает страницу в Playwright с применением Stealth
        2. Ждёт обхода антибот-системы
        3. Выполняет API запрос через page.evaluate() с JavaScript fetch
        4. Парсит JSON ответ и преобразует в ComplexParsedDTO
        
        ВАЖНО: Метод НЕ сохраняет данные в БД - только возвращает список DTO.
        
        Args:
            offset: Смещение для пагинации (по умолчанию 0)
            limit: Количество результатов на странице (по умолчанию 100)
            search: Поисковый запрос для фильтрации по городу (по умолчанию пустая строка)
            return_metadata: Если True, возвращает FetchResult с метаинформацией о количестве
                           запрошенных записей (до фильтрации). Если False, возвращает только
                           список ComplexParsedDTO (по умолчанию False)
            
        Returns:
            Если return_metadata=False: Список объектов ComplexParsedDTO с данными о жилых комплексах
            Если return_metadata=True: FetchResult(complexes, total_requested) с отфильтрованными
                                      результатами и количеством запрошенных у API (до фильтрации)
            
        Raises:
            ValidationError: При ошибках валидации данных
            Exception: При других неожиданных ошибках
            
        Пример использования:
            parser = NashDomParser()
            # Простой вызов - возвращает только список
            complexes = await parser.fetch_complexes(offset=0, limit=50, search="Москва")
            for complex_dto in complexes:
                print(f"{complex_dto.name} - {complex_dto.address}")
            
            # Вызов с метаинформацией для пагинации
            result = await parser.fetch_complexes(offset=0, limit=1000, search="Москва", return_metadata=True)
            filtered_complexes = result.complexes  # Отфильтрованные результаты
            total_requested = result.total_requested  # Сколько запрошено у API (до фильтрации)
            
            await parser.close()
        """
        page: Optional[Page] = None
        try:
            # Инициализируем браузер
            await self._init_browser()
            
            # Создаём новую страницу
            page = await self.context.new_page()
            
            # Применяем Stealth для обхода детекции
            await self._apply_stealth(page)
            
            # Ждём обхода антибот-системы
            await self._wait_for_antibot(page)
            
            # Формируем URL API запроса
            api_url = self._build_api_url(offset=offset, limit=limit, search=search)
            logger.info(f"Выполнение API запроса: {api_url}")
            
            # Выполняем API запрос через JavaScript fetch в браузере
            js_code = f"""
                async () => {{
                    try {{
                        const response = await fetch("{api_url}", {{
                            method: "GET",
                            credentials: "include"
                        }});
                        
                        if (!response.ok) {{
                            return {{ error: `HTTP ${{response.status}}: ${{response.statusText}}` }};
                        }}
                        
                        const json = await response.json().catch(() => null);
                        if (!json) {{
                            return {{ error: "Failed to parse JSON" }};
                        }}
                        
                        return json;
                    }} catch (error) {{
                        return {{ error: error.message }};
                    }}
                }}
            """
            
            result = await page.evaluate(js_code)
            
            if not result:
                logger.error("❌ JSON не удалось получить - результат пустой")
                return []
            
            if 'error' in result:
                logger.error(f"❌ Ошибка при выполнении запроса: {result['error']}")
                raise Exception(f"API запрос не удался: {result['error']}")
            
            logger.info(f"✓ Получен JSON ответ от API")
            
            # Сохраняем JSON для отладки
            try:
                with open("debug_api_response.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                logger.debug("JSON ответ сохранён в debug_api_response.json")
            except Exception as e:
                logger.debug(f"Не удалось сохранить JSON: {e}")
            
            # Извлекаем список ЖК из JSON
            complexes_list = self._extract_complexes_from_json(result)
            
            if not complexes_list:
                logger.warning("Список ЖК пуст в JSON ответе")
                if return_metadata:
                    return FetchResult(complexes=[], total_requested=0)
                return []
            
            # Сохраняем количество запрошенных у API (до фильтрации)
            total_requested = len(complexes_list)
            logger.info(f"Найдено {total_requested} ЖК в JSON ответе")
            
            # Фильтруем по городу, если указан параметр search
            if search:
                complexes_list = self._filter_by_city(complexes_list, search)
                logger.info(f"После фильтрации по городу '{search}': {len(complexes_list)} ЖК")
            
            # Преобразуем в ComplexParsedDTO
            complexes = []
            for item in complexes_list:
                try:
                    # Маппим поля JSON в формат DTO
                    mapped_item = self._map_json_to_dto(item)
                    
                    # Валидация через Pydantic модель
                    complex_dto = ComplexParsedDTO(**mapped_item)
                    complexes.append(complex_dto)
                    
                except ValidationError as e:
                    logger.warning(f"Ошибка валидации данных ЖК: {e}. Пропускаем элемент.")
                    logger.debug(f"Проблемные данные: {mapped_item if 'mapped_item' in locals() else item}")
                    continue
                except Exception as e:
                    logger.error(f"Ошибка при обработке элемента ЖК: {e}")
                    logger.debug(f"Проблемные данные: {item}")
                    continue
            
            logger.info(f"✓ Успешно обработано {len(complexes)} ЖК из {len(complexes_list)} полученных")
            
            if return_metadata:
                return FetchResult(complexes=complexes, total_requested=total_requested)
            return complexes
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге ЖК: {e}", exc_info=True)
            raise
        finally:
            if page:
                await page.close()
    
    async def _close_browser(self):
        """Закрыть браузер Playwright."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            logger.debug("Браузер Playwright закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии браузера: {e}")
    
    async def close(self):
        """Закрыть браузер Playwright."""
        await self._close_browser()
    
    async def __aenter__(self):
        """Поддержка async контекстного менеджера."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Поддержка async контекстного менеджера."""
        await self.close()
