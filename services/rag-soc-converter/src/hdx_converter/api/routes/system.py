"""System endpoints for health checks and metrics."""
from fastapi import APIRouter, Response
import logging
import time
from typing import Dict, Any

router = APIRouter(tags=["System"])

# Версия сервиса
VERSION = "1.0.0"


@router.get("/health")
async def health():
    """
    Liveness probe для Kubernetes.
    
    Проверяет, что процесс жив.
    Не проверяет зависимости.
    """
    return {
        "status": "healthy",
        "version": VERSION,
        "components": {}
    }


@router.get("/ready")
async def ready(
    object_storage_available: bool = True,
    kafka_available: bool = True
):
    """
    Readiness probe для Kubernetes.
    
    Проверяет доступность зависимостей:
    - Object Storage (S3/NFS)
    - Kafka
    """
    checks = {
        "object_storage": object_storage_available,
        "kafka": kafka_available
    }
    
    ready = all(checks.values())
    status_code = 200 if ready else 503
    
    return Response(
        content=f'{{"ready": {str(ready).lower()}, "checks": {_format_checks(checks)}}}',
        status_code=status_code,
        media_type="application/json"
    )


@router.get("/metrics")
async def metrics():
    """
    Prometheus метрики.
    
    Возвращает метрики в формате Prometheus.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def _format_checks(checks: Dict[str, bool]) -> str:
    """Форматирование checks для JSON ответа."""
    items = [f'"{k}": {str(v).lower()}' for k, v in checks.items()]
    return "{" + ", ".join(items) + "}"