"""Background worker for running conversion jobs."""
import threading
import logging
from typing import Optional
from uuid import UUID
from pathlib import Path
from datetime import datetime

from ...models.config import ConverterConfig
from ...core.converter import HDXConverter
from ..models.requests import JobStatus
from .job_manager import JobManager
from .kafka_producer import KafkaNotificationProducer


class ConversionWorker:
    """
    Фоновый воркер для выполнения задач конвертации.
    
    Запускает конвертацию в отдельном потоке, обновляет статус в JobManager,
    отправляет уведомления в Kafka.
    """
    
    def __init__(
        self,
        job_manager: JobManager,
        kafka_producer: Optional[KafkaNotificationProducer],
        logger: logging.Logger
    ):
        self.job_manager = job_manager
        self.kafka_producer = kafka_producer
        self.logger = logger
        self._active_threads: dict[UUID, threading.Thread] = {}
    
    def start_job(
        self,
        job_id: UUID,
        source_uri: str,
        output_uri: Optional[str],
        config: ConverterConfig,
        traceparent: Optional[str] = None
    ):
        """
        Запустить конвертацию в фоновом потоке.
        
        Args:
            job_id: Идентификатор задачи
            source_uri: Путь к исходному документу
            output_uri: Путь для результатов
            config: Конфигурация конвертера
            traceparent: W3C Trace-Context для трассировки
        """
        thread = threading.Thread(
            target=self._run_conversion,
            args=(job_id, source_uri, output_uri, config, traceparent),
            daemon=True
        )
        
        self._active_threads[job_id] = thread
        thread.start()
        
        self.logger.info(f"Started background job {job_id}")
    
    def _run_conversion(
        self,
        job_id: UUID,
        source_uri: str,
        output_uri: Optional[str],
        config: ConverterConfig,
        traceparent: Optional[str]
    ):
        """
        Выполнить конвертацию.
        
        Этот метод запускается в отдельном потоке.
        """
        try:
            # Обновляем статус на PROCESSING
            self.job_manager.update_job_status(
                job_id,
                JobStatus.PROCESSING,
                started_at=datetime.now()
            )
            
            # Проверяем отмену перед началом
            job = self.job_manager.get_job(job_id)
            if job and job.cancel_requested:
                self._handle_cancellation(job_id, source_uri, output_uri, config)
                return
            
            # Инициализируем конвертер
            converter = HDXConverter(config, self.logger)
            
            # Запускаем конвертацию
            # TODO: Добавить прогресс в HDXConverter (опционально)
            converter.convert(Path(source_uri))
            
            # Проверяем отмену после конвертации
            job = self.job_manager.get_job(job_id)
            if job and job.cancel_requested:
                self._handle_cancellation(job_id, source_uri, output_uri, config)
                return
            
            # Получаем статистику
            stats = self._get_statistics(converter)
            
            # Обновляем статус на COMPLETED
            self.job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                statistics=stats
            )
            
            # Отправляем уведомление в Kafka
            if self.kafka_producer:
                job = self.job_manager.get_job(job_id)
                self.kafka_producer.send_completed(
                    job_id=job_id,
                    source_uri=source_uri,
                    output_uri=output_uri,
                    statistics=stats,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                    traceparent=traceparent
                )
            
            self.logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            self._handle_error(job_id, source_uri, output_uri, config, str(e), traceparent)
    
    def _handle_cancellation(
        self,
        job_id: UUID,
        source_uri: str,
        output_uri: Optional[str],
        config: ConverterConfig
    ):
        """Обработка отмены задачи."""
        self.logger.info(f"Job {job_id} cancelled by user")
        
        # Получаем статистику (частичную)
        stats = {"conversion": {"errors_encountered": 1}}
        
        self.job_manager.update_job_status(
            job_id,
            JobStatus.CANCELLED,
            statistics=stats,
            warning_message="Job cancelled by user"
        )
        
        # Отправляем уведомление
        if self.kafka_producer:
            job = self.job_manager.get_job(job_id)
            self.kafka_producer.send_cancelled(
                job_id=job_id,
                source_uri=source_uri,
                output_uri=output_uri,
                statistics=stats,
                started_at=job.started_at,
                completed_at=job.completed_at
            )
    
    def _handle_error(
        self,
        job_id: UUID,
        source_uri: str,
        output_uri: Optional[str],
        config: ConverterConfig,
        error_message: str,
        traceparent: Optional[str]
    ):
        """Обработка ошибки конвертации."""
        self.logger.error(f"Job {job_id} failed: {error_message}")
        
        # Получаем статистику (частичную)
        stats = {"conversion": {"errors_encountered": 1}}
        
        self.job_manager.update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=error_message,
            statistics=stats
        )
        
        # Отправляем уведомление
        if self.kafka_producer:
            job = self.job_manager.get_job(job_id)
            self.kafka_producer.send_failed(
                job_id=job_id,
                source_uri=source_uri,
                output_uri=output_uri,
                error_message=error_message,
                statistics=stats,
                started_at=job.started_at,
                completed_at=job.completed_at,
                traceparent=traceparent
            )
    
    def _get_statistics(self, converter: HDXConverter) -> dict:
        """Получить статистику из конвертера."""
        try:
            # Статистика доступна через stats_collector
            stats = converter.stats_collector.get_statistics_summary()
            return {
                "conversion": stats.get("conversion", {}),
                "validation": stats.get("validation", {})
            }
        except Exception as e:
            self.logger.warning(f"Failed to get statistics: {e}")
            return {"conversion": {}, "validation": {}}
    
    def cancel_job(self, job_id: UUID) -> bool:
        """
        Отменить задачу.
        
        Устанавливает флаг отмены. Воркер проверяет этот флаг при возможности.
        """
        return self.job_manager.request_cancel(job_id)