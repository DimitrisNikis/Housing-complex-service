"""Конфигурация приложения."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/housing_db"
    
    # JWT
    SECRET_KEY: str = "secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Parser
    PARSER_CITY: str = "Москва"
    PARSER_SCHEDULER_HOURS: int = 3  # Интервал актуализации в часах
    PARSER_HEADLESS: bool = True  # Запуск браузера в headless режиме
    PARSER_BROWSER_TIMEOUT: int = 30000  # Таймаут для ожидания элементов (мс)
    PARSER_PAGE_SIZE: int = 1000  # Размер страницы для пагинации (количество записей за один запрос)
    PARSER_MAX_RESULTS: int = 1500  # Максимальное количество результатов (0 = без лимита, загружать все)
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки приложения (singleton)."""
    return Settings()

