"""Главный файл приложения FastAPI."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, SessionLocal
from app.models import HousingComplex, House, Binding, User  # Импортируем модели для создания таблиц
from app.api import auth, bindings
from app.services.updater import DataUpdater

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()
scheduler = AsyncIOScheduler()


async def update_housing_complexes_task():
    """Асинхронная задача для выполнения периодической актуализации данных."""
    logger.info("Запуск периодической актуализации данных")
    db = SessionLocal()
    updater = None
    try:
        updater = DataUpdater(db)
        result = await updater.update_housing_complexes()
        logger.info(f"Результат актуализации: {result}")
    except Exception as e:
        logger.error(f"Ошибка при актуализации данных: {e}")
    finally:
        if updater:
            await updater.close()
        db.close()


def update_housing_complexes():
    """Обёртка для синхронного вызова async функции через APScheduler."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Если event loop уже запущен, создаём задачу
        asyncio.create_task(update_housing_complexes_task())
    else:
        # Иначе запускаем синхронно
        loop.run_until_complete(update_housing_complexes_task())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info("Запуск приложения")
    
    # Создаем таблицы в БД (если еще не созданы)
    try:
        from app.database import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы БД проверены/созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
    
    # Запускаем периодическую задачу актуализации
    scheduler.add_job(
        update_housing_complexes,
        trigger=IntervalTrigger(hours=settings.PARSER_SCHEDULER_HOURS),
        id="update_housing_complexes",
        name="Актуализация данных о ЖК",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Планировщик запущен (интервал: {settings.PARSER_SCHEDULER_HOURS} часов)")
    
    # Выполняем первую актуализацию при старте
    import asyncio
    asyncio.create_task(update_housing_complexes_task())
    
    yield
    
    # Shutdown
    logger.info("Остановка приложения")
    scheduler.shutdown()


# Создаем приложение FastAPI
app = FastAPI(
    title="Housing Complex Service",
    description="Микросервис для сбора данных о жилых комплексах и привязке домов",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(bindings.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "message": "Housing Complex Service API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

