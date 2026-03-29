"""OpenTelemetry middleware for distributed tracing."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для распределённой трассировки.
    
    Извлекает traceparent из заголовка и добавляет trace_id в логи.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Извлекаем traceparent
        traceparent = request.headers.get("traceparent")
        
        if traceparent:
            # Парсим trace_id
            # Формат: 00-{trace-id}-{span-id}-{flags}
            parts = traceparent.split("-")
            if len(parts) >= 3:
                trace_id = parts[1]
                request.state.trace_id = trace_id
                
                # Добавляем в логи
                logger.debug(f"Trace ID: {trace_id}")
        
        response = await call_next(request)
        
        # Добавляем trace_id в ответ (опционально)
        if hasattr(request.state, 'trace_id'):
            response.headers["X-Trace-Id"] = request.state.trace_id
        
        return response