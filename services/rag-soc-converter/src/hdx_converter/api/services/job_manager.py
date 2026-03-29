"""In-memory job manager for conversion tasks."""
import threading
from typing import Dict, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

from ...models.config import ConverterConfig
from ...core.converter import HDXConverter
from ..models.requests import JobStatus, JobStatusResponse, JobSummary


@dataclass
class ConversionJob:
    """Внутреннее представление задачи конвертации."""
    job_id: UUID
    source_uri: str
    output_uri: Optional[str]
    status: JobStatus
    progress_percent: int = 0
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    statistics: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: Optional[ConverterConfig] = None
    thread: Optional[threading.Thread] = None
    cancel_requested: bool = False


class JobManager:
    """
    In-memory менеджер задач конвертации.
    
    Хранит все задачи в словаре. При перезапуске сервиса задачи теряются.
    Для MVP этого достаточно.
    """
    
    def __init__(self, logger: logging.Logger):
        self._jobs: Dict[UUID, ConversionJob] = {}
        self._lock = threading.Lock()
        self.logger = logger
    
    def create_job(
        self,
        source_uri: str,
        output_uri: Optional[str],
        config: ConverterConfig
    ) -> UUID:
        """Создать новую задачу."""
        job_id = uuid4()
        
        with self._lock:
            self._jobs[job_id] = ConversionJob(
                job_id=job_id,
                source_uri=source_uri,
                output_uri=output_uri,
                status=JobStatus.PENDING,
                config=config
            )
        
        self.logger.info(f"Job created: {job_id}, source: {source_uri}")
        return job_id
    
    def get_job(self, job_id: UUID) -> Optional[ConversionJob]:
        """Получить задачу по ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[JobSummary], int]:
        """Получить список задач с фильтрацией."""
        with self._lock:
            jobs = list(self._jobs.values())
            
            if status:
                jobs = [j for j in jobs if j.status == status]
            
            total = len(jobs)
            
            # Сортировка по времени создания (новые сверху)
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            
            # Пагинация
            jobs = jobs[offset:offset + limit]
            
            summaries = [
                JobSummary(
                    job_id=j.job_id,
                    status=j.status,
                    source_uri=j.source_uri,
                    output_uri=j.output_uri,
                    created_at=j.created_at,
                    started_at=j.started_at,
                    completed_at=j.completed_at
                )
                for j in jobs
            ]
            
            return summaries, total
    
    def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        **kwargs
    ) -> bool:
        """Обновить статус задачи."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            job.status = status
            
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            if status == JobStatus.PROCESSING and not job.started_at:
                job.started_at = datetime.now()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                job.completed_at = datetime.now()
                job.progress_percent = 100
            
            self.logger.debug(f"Job {job_id} status updated: {status}")
            return True
    
    def update_progress(self, job_id: UUID, progress_percent: int):
        """Обновить прогресс выполнения."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress_percent = progress_percent
    
    def request_cancel(self, job_id: UUID) -> bool:
        """Запросить отмену задачи."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False
            
            job.cancel_requested = True
            return True