"""REST API endpoints for conversion operations."""
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from typing import Optional
from uuid import UUID

from ..models.requests import (
    ConvertRequest,
    ConvertResponse,
    JobStatusResponse,
    JobListResponse,
    CancelResponse,
    JobStatus,
    ErrorResponse
)
from ..services.job_manager import JobManager
from ..services.worker import ConversionWorker

router = APIRouter(prefix="/api/v1/convert", tags=["Conversion"])


def get_job_manager() -> JobManager:
    """Dependency для получения JobManager."""
    from ..app import job_manager
    return job_manager


def get_worker() -> ConversionWorker:
    """Dependency для получения ConversionWorker."""
    from ..app import worker
    return worker


@router.post(
    "",
    response_model=ConvertResponse,
    status_code=202,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def convert(
    request: Request,
    conv_request: ConvertRequest,
    job_manager: JobManager = Depends(get_job_manager),
    worker: ConversionWorker = Depends(get_worker)
):
    """
    Запуск конвертации документа или папки.
    
    Асинхронно запускает процесс конвертации и возвращает job_id.
    """
    # Получаем traceparent из заголовка
    traceparent = request.headers.get("traceparent")
    
    # Создаем конфигурацию конвертера
    from ...models.config import ConverterConfig
    from pathlib import Path
    
    # Определяем output_dir
    if conv_request.output_uri:
        output_dir = Path(conv_request.output_uri)
    else:
        # Генерируем на основе source_uri
        source_path = Path(conv_request.source_uri)
        output_dir = source_path.parent / f"{source_path.stem}_output"

    # Преобразуем числовой log_level в строковый формат
    log_level_map = {0: "ERROR", 1: "WARNING", 2: "INFO", 3: "DEBUG"}
    log_level_str = log_level_map.get(conv_request.log_level, "INFO")
    
    # Создаем конфигурацию
    config = ConverterConfig(
        output_dir=output_dir,
        max_articles=conv_request.max_articles,
        skip_extract=conv_request.skip_extract,
        generate_text=True,
        generate_markdown=True,
        generate_json_metadata=True,
        backup_html=True,
        print_statistics=True,
        save_skipped_files=True,
        validate_metadata=True,
        log_level=log_level_str
    )
    
    # Создаем задачу
    job_id = job_manager.create_job(
        source_uri=conv_request.source_uri,
        output_uri=conv_request.output_uri,
        config=config
    )
    
    # Запускаем в фоне
    worker.start_job(
        job_id=job_id,
        source_uri=conv_request.source_uri,
        output_uri=conv_request.output_uri,
        config=config,
        traceparent=traceparent
    )
    
    # Получаем созданную задачу
    job = job_manager.get_job(job_id)
    
    return ConvertResponse(
        job_id=job_id,
        status=job.status,
        source_uri=job.source_uri,
        output_uri=job.output_uri,
        created_at=job.created_at
    )


@router.get(
    "",
    response_model=JobListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Фильтр по статусу"),
    limit: int = Query(50, ge=1, le=100, description="Количество задач на страницу"),
    offset: int = Query(0, ge=0, description="Смещение"),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Получение списка задач с фильтрацией и пагинацией."""
    jobs, total = job_manager.get_jobs(
        status=status,
        limit=limit,
        offset=offset
    )
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_job_status(
    job_id: UUID,
    job_manager: JobManager = Depends(get_job_manager)
):
    """Получение статуса конвертации."""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Job not found",
                "code": "JOB_NOT_FOUND",
                "details": {"job_id": str(job_id)}
            }
        )
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_percent=job.progress_percent,
        source_uri=job.source_uri,
        output_uri=job.output_uri,
        error_message=job.error_message,
        warning_message=job.warning_message,
        statistics=job.statistics,
        started_at=job.started_at,
        completed_at=job.completed_at
    )


@router.post(
    "/{job_id}/cancel",
    response_model=CancelResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def cancel_job(
    job_id: UUID,
    job_manager: JobManager = Depends(get_job_manager),
    worker: ConversionWorker = Depends(get_worker)
):
    """Отмена конвертации."""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Job not found",
                "code": "JOB_NOT_FOUND",
                "details": {"job_id": str(job_id)}
            }
        )
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=409,
            detail={
                "error": f"Cannot cancel job: job already {job.status.value}",
                "code": "JOB_ALREADY_COMPLETED",
                "details": {"job_id": str(job_id), "status": job.status.value}
            }
        )
    
    cancelled = worker.cancel_job(job_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Cannot cancel job: job already completed or in terminal state",
                "code": "CANCEL_FAILED",
                "details": {"job_id": str(job_id)}
            }
        )
    
    return CancelResponse(
        job_id=job_id,
        status=JobStatus.CANCELLED,
        message="Job cancelled successfully"
    )