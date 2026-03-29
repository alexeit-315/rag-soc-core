"""FastAPI application for Converter Service."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from typing import Optional

from .routes import conversion, system
from .middleware.tracing import TracingMiddleware
from .middleware.logging import JSONLoggingMiddleware
from .services.job_manager import JobManager
from .services.worker import ConversionWorker
from .services.kafka_producer import KafkaNotificationProducer

# Глобальные объекты (для доступа из роутов)
job_manager: Optional[JobManager] = None
worker: Optional[ConversionWorker] = None


def create_app(
    logger: logging.Logger,
    kafka_bootstrap_servers: Optional[str] = None,
    kafka_enabled: bool = False
) -> FastAPI:
    """
    Создание и настройка FastAPI приложения.
    
    Args:
        logger: Логгер для сервиса
        kafka_bootstrap_servers: Адреса Kafka брокеров
        kafka_enabled: Включить ли отправку в Kafka
    
    Returns:
        Настроенное FastAPI приложение
    """
    global job_manager, worker
    
    app = FastAPI(
        title="Converter Service API",
        description="Сервис конвертации документов технической документации для RAG-платформы",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # CORS (для тестирования)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Middleware для трассировки
    app.add_middleware(TracingMiddleware)
    
    # Middleware для JSON логирования
    app.add_middleware(JSONLoggingMiddleware, service_name="rag-soc-converter")
    
    # Инициализация сервисов
    job_manager = JobManager(logger)
    
    # Инициализация Kafka producer
    kafka_producer = None
    if kafka_enabled and kafka_bootstrap_servers:
        kafka_producer = KafkaNotificationProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            topics={
                "completed": os.getenv("KAFKA_TOPIC_COMPLETED", "conversion.completed"),
                "failed": os.getenv("KAFKA_TOPIC_FAILED", "conversion.failed"),
                "cancelled": os.getenv("KAFKA_TOPIC_CANCELLED", "conversion.cancelled")
            },
            logger=logger,
            enabled=kafka_enabled
        )
    
    worker = ConversionWorker(job_manager, kafka_producer, logger)
    
    # Регистрация роутов
    app.include_router(conversion.router)
    app.include_router(system.router)
    
    return app


def shutdown():
    """Очистка ресурсов при остановке."""
    global worker
    if worker and worker.kafka_producer:
        worker.kafka_producer.close()