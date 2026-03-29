"""Kafka producer for sending conversion notifications."""
import json
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None


class KafkaNotificationProducer:
    """
    Отправка уведомлений о завершении конвертации в Kafka.
    
    Если Kafka недоступен, логирует сообщения и продолжает работу.
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        topics: Dict[str, str],
        logger: logging.Logger,
        enabled: bool = True
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.logger = logger
        self.enabled = enabled and KAFKA_AVAILABLE
        self._producer: Optional[KafkaProducer] = None
        
        if self.enabled:
            self._init_producer()
    
    def _init_producer(self):
        """Инициализация Kafka producer."""
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                acks='all',
                retries=3
            )
            self.logger.info(f"Kafka producer initialized: {self.bootstrap_servers}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Kafka producer: {e}")
            self.enabled = False
    
    def send_completed(
        self,
        job_id: UUID,
        source_uri: str,
        output_uri: Optional[str],
        statistics: Dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        traceparent: Optional[str] = None
    ):
        """Отправить уведомление об успешном завершении."""
        event = {
            "event_type": "conversion_completed",
            "job_id": str(job_id),
            "status": "completed",
            "source_uri": source_uri,
            "output_uri": output_uri,
            "error_message": None,
            "warning_message": None,
            "statistics": statistics,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "traceparent": traceparent
        }
        self._send(self.topics.get('completed', 'conversion.completed'), event)
    
    def send_failed(
        self,
        job_id: UUID,
        source_uri: str,
        output_uri: Optional[str],
        error_message: str,
        statistics: Dict[str, Any],
        started_at: Optional[datetime],
        completed_at: datetime,
        traceparent: Optional[str] = None
    ):
        """Отправить уведомление об ошибке."""
        event = {
            "event_type": "conversion_failed",
            "job_id": str(job_id),
            "status": "failed",
            "source_uri": source_uri,
            "output_uri": output_uri,
            "error_message": error_message,
            "warning_message": None,
            "statistics": statistics,
            "started_at": started_at.isoformat() if started_at else None,
            "completed_at": completed_at.isoformat(),
            "traceparent": traceparent
        }
        self._send(self.topics.get('failed', 'conversion.failed'), event)
    
    def send_cancelled(
        self,
        job_id: UUID,
        source_uri: str,
        output_uri: Optional[str],
        statistics: Dict[str, Any],
        started_at: Optional[datetime],
        completed_at: datetime,
        traceparent: Optional[str] = None
    ):
        """Отправить уведомление об отмене."""
        event = {
            "event_type": "conversion_cancelled",
            "job_id": str(job_id),
            "status": "cancelled",
            "source_uri": source_uri,
            "output_uri": output_uri,
            "error_message": None,
            "warning_message": "Job cancelled by user",
            "statistics": statistics,
            "started_at": started_at.isoformat() if started_at else None,
            "completed_at": completed_at.isoformat(),
            "traceparent": traceparent
        }
        self._send(self.topics.get('cancelled', 'conversion.cancelled'), event)
    
    def _send(self, topic: str, event: Dict[str, Any]):
        """Отправить сообщение в Kafka."""
        if not self.enabled or not self._producer:
            self.logger.debug(f"Kafka disabled, would send to {topic}: {event}")
            return
        
        try:
            future = self._producer.send(topic, value=event)
            future.get(timeout=10)
            self.logger.debug(f"Sent event to {topic}: {event.get('event_type')}")
        except KafkaError as e:
            self.logger.error(f"Failed to send Kafka message: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending Kafka message: {e}")
    
    def close(self):
        """Закрыть producer."""
        if self._producer:
            self._producer.flush()
            self._producer.close()