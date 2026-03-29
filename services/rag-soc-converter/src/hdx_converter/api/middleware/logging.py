"""JSON logging middleware."""
import json
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
from datetime import datetime


class JSONLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для JSON логирования запросов.

    Формат логов соответствует стандартам:
    {
        "timestamp": "2024-03-25T10:30:00.123Z",
        "level": "INFO",
        "service": "rag-soc-converter",
        "trace_id": "...",
        "method": "POST",
        "path": "/api/v1/convert",
        "status_code": 202,
        "duration_ms": 123
    }
    """

    def __init__(self, app, service_name: str = "rag-soc-converter"):
        super().__init__(app)
        self.service_name = service_name
        self.logger = logging.getLogger("api")

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        # Получаем trace_id
        trace_id = getattr(request.state, 'trace_id', None)

        # Формируем timestamp с микросекундами (совместимо с Windows)
        now = datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S") + f".{now.microsecond:06d}Z"

        # Формируем JSON лог
        log_entry = {
            "timestamp": timestamp,
            "level": "INFO",
            "service": self.service_name,
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2)
        }
        
        self.logger.info(json.dumps(log_entry))
        
        return response