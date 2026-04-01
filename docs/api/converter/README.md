# Converter Service API

Сервис конвертации документов технической документации для RAG-платформы.

---

## 📋 Обзор

Сервис **Converter** отвечает за конвертацию исходных документов технической документации в структурированный машиночитаемый формат (JSON) и человекочитаемые форматы (TXT, MD).

### Основные возможности

| Возможность | Описание |
|-------------|----------|
| **Поддерживаемые форматы** | HDX (Huawei Documentation eXtract), HTML, XML, PDF |
| **Выходные форматы** | JSON (структурированный), TXT, MD |
| **Метаданные** | filename, dc_identifier, title, breadcrumbs, product_series, firmware_versions, features_set, validation_flag, related_documents и другие |
| **Способы запуска** | REST API (асинхронный, возвращает job_id) и Kafka (асинхронный) |
| **Kafka интеграция** | Уведомления о завершении отправляются в Kafka |
| **Распределённая трассировка** | Поддержка W3C Trace-Context (`traceparent` header) |
| **Мониторинг** | Prometheus метрики, health checks для Kubernetes |

---

## 🚀 Быстрый старт

### Запуск конвертации через REST API

```bash
curl -X POST https://converter.rag-system.company.com/api/v1/convert \
  -H "traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01" \
  -H "Content-Type: application/json" \
  -d '{
    "source_uri": "s3://bucket/docs/platform_X_v2.1.hdx"
  }'
```

**Ответ:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "source_uri": "s3://bucket/docs/platform_X_v2.1.hdx",
  "output_uri": "s3://bucket/output/platform_X_v2.1",
  "created_at": "2024-03-25T10:00:00Z"
}
```

### Проверка статуса

```bash
curl -X GET https://converter.rag-system.company.com/api/v1/convert/550e8400-e29b-41d4-a716-446655440000/status
```

**Ответ (в процессе):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percent": 45,
  "source_uri": "s3://bucket/docs/platform_X_v2.1.hdx",
  "output_uri": "s3://bucket/output/platform_X_v2.1",
  "started_at": "2024-03-25T10:00:05Z"
}
```

**Ответ (завершено):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress_percent": 100,
  "source_uri": "s3://bucket/docs/platform_X_v2.1.hdx",
  "output_uri": "s3://bucket/output/platform_X_v2.1",
  "statistics": {
    "conversion": {
      "total_html_files": 100,
      "duration_seconds": 126.37
    }
  },
  "completed_at": "2024-03-25T10:02:05Z"
}
```

### Асинхронный запуск через Kafka

```python
from kafka import KafkaProducer
import json
import uuid

producer = KafkaProducer(
    bootstrap_servers=['kafka.rag-system:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

request = {
    "request_id": str(uuid.uuid4()),
    "source_uri": "s3://bucket/docs/platform_X_v2.1.hdx",
    "log_level": 2
}

producer.send('conversion.request', value=request)
```

---

## 📚 Документация

| Документ | Описание |
|----------|----------|
| [**OpenAPI Specification**](./converter-api.yaml) | Полная спецификация REST API в формате OpenAPI 3.0 (YAML) |
| [**API Examples**](./converter-api-examples.md) | Подробные примеры использования REST API |
| [**Kafka Events**](./converter-kafka-events.md) | Описание Kafka сообщений и топиков |

---

## 🔌 Эндпоинты REST API

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/v1/convert` | Запуск конвертации документа или папки |
| `GET` | `/api/v1/convert` | Получение списка задач (с фильтрацией) |
| `GET` | `/api/v1/convert/{job_id}/status` | Получение статуса конвертации |
| `POST` | `/api/v1/convert/{job_id}/cancel` | Отмена конвертации |
| `GET` | `/health` | Liveness probe для Kubernetes |
| `GET` | `/ready` | Readiness probe для Kubernetes |
| `GET` | `/metrics` | Prometheus метрики |

---

## 📨 Kafka Топики

| Топик | Тип | Описание |
|-------|-----|----------|
| `conversion.request` | Input | Запрос на запуск конвертации (асинхронный режим) |
| `conversion.request.error` | Output | Ошибки валидации запроса |
| `conversion.completed` | Output | Успешное завершение конвертации |
| `conversion.failed` | Output | Завершение с ошибкой |
| `conversion.cancelled` | Output | Отмена задачи |
| `conversion.progress` | Output | Промежуточные события прогресса (опционально) |

---

## 🏥 Health Checks (Kubernetes)

| Эндпоинт | Назначение | Использование |
|----------|------------|---------------|
| `/health` | Liveness probe | Проверка живости сервиса (процесс работает) |
| `/ready` | Readiness probe | Проверка готовности принимать трафик (все зависимости доступны) |

### Пример проверки готовности

```bash
curl -X GET https://converter.rag-system.company.com/ready
```

**Ответ (готов):**
```json
{
  "ready": true,
  "checks": {
    "object_storage": true,
    "kafka": true
  }
}
```

**Ответ (не готов):**
```json
{
  "ready": false,
  "checks": {
    "object_storage": true,
    "kafka": false
  }
}
```

---

## 📊 Prometheus Метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `converter_requests_total` | Counter | Общее количество запросов |
| `converter_requests_duration_seconds` | Histogram | Длительность запросов |
| `converter_errors_total` | Counter | Количество ошибок |
| `converter_jobs_total` | Counter | Количество созданных задач по статусам |
| `converter_active_jobs` | Gauge | Количество активных задач |

### Пример получения метрик

```bash
curl -X GET https://converter.rag-system.company.com/metrics
```

**Ответ:**
```
# HELP converter_requests_total Total number of requests
# TYPE converter_requests_total counter
converter_requests_total{method="POST",endpoint="/convert"} 42
converter_requests_total{method="GET",endpoint="/convert/status"} 156

# HELP converter_requests_duration_seconds Request duration in seconds
# TYPE converter_requests_duration_seconds histogram
converter_requests_duration_seconds_bucket{method="POST",le="0.1"} 35
converter_requests_duration_seconds_bucket{method="POST",le="0.5"} 42
converter_requests_duration_seconds_sum{method="POST"} 8.5
converter_requests_duration_seconds_count{method="POST"} 42

# HELP converter_jobs_total Total number of conversion jobs
# TYPE converter_jobs_total counter
converter_jobs_total{status="pending"} 5
converter_jobs_total{status="processing"} 3
converter_jobs_total{status="completed"} 28
converter_jobs_total{status="failed"} 4
converter_jobs_total{status="cancelled"} 2

# HELP converter_active_jobs Currently active jobs
# TYPE converter_active_jobs gauge
converter_active_jobs 3
```

---

## 🔐 Безопасность

### Аутентификация
- **Внутренние вызовы:** mTLS через Istio
- **Внешние вызовы:** JWT (проксируется через API Gateway)

### Трассировка
Все запросы должны содержать `traceparent` header в формате W3C Trace-Context:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

**Формат:** `00-{trace-id}-{span-id}-{trace-flags}`

---

## 📊 Параметры запуска

| Параметр | Тип | Обязательный | Описание |
|----------|-----|:-------------:|----------|
| `source_uri` | string | ✅ | Путь к исходному документу или папке (HDX, HTML, XML, PDF) |
| `output_uri` | string | ❌ | Выходная директория (по умолчанию: `{source_uri}_output`) |
| `max_articles` | integer | ❌ | Обработать только первые N статей (для тестирования) |
| `skip_extract` | boolean | ❌ | Пропустить извлечение HDX, использовать сохраненные HTML |
| `log_level` | integer (0-3) | ❌ | 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG (по умолчанию: 2) |

---

## 🧪 Тестирование

### Запуск API сервера локально

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
python -m hdx_converter.cli api --host 0.0.0.0 --port 8080

# С включенной Kafka интеграцией
python -m hdx_converter.cli api \
  --host 0.0.0.0 \
  --port 8080 \
  --kafka-enabled \
  --kafka-bootstrap-servers localhost:9092
```

### Проверка через curl

```bash
# Health check
curl http://localhost:8080/health

# Readiness check
curl http://localhost:8080/ready

# Prometheus метрики
curl http://localhost:8080/metrics

# Запуск конвертации
curl -X POST http://localhost:8080/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{
    "source_uri": "/path/to/file.hdx",
    "output_uri": "/path/to/output",
    "log_level": 3
  }'

# Статус задачи
curl http://localhost:8080/api/v1/convert/{job_id}/status

# Список задач
curl "http://localhost:8080/api/v1/convert?status=completed&limit=10"

# Отмена задачи
curl -X POST http://localhost:8080/api/v1/convert/{job_id}/cancel
```

---

## 🐳 Docker

### Сборка образа

```bash
docker build -t harbor.domain/rag-soc/converter:1.0.0 .
```

### Запуск контейнера

```bash
docker run -p 8080:8080 \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e KAFKA_ENABLED=true \
  harbor.domain/rag-soc/converter:1.0.0
```

### Kubernetes deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: converter
  namespace: rag-soc
spec:
  replicas: 2
  selector:
    matchLabels:
      app: converter
  template:
    metadata:
      labels:
        app: converter
    spec:
      containers:
      - name: converter
        image: harbor.domain/rag-soc/converter:1.0.0
        ports:
        - containerPort: 8080
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka.default.svc.cluster.local:9092"
        - name: KAFKA_ENABLED
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

---

## 📞 Поддержка

| Контакт | Назначение |
|---------|------------|
| [RAG System Team](mailto:rag-team@company.com) | Техническая поддержка |
| [GitHub Issues](https://github.com/company/rag-converter/issues) | Баг-репорты |
| [Confluence](https://confluence.company.com/rag/converter) | Внутренняя документация |

---

## 🔗 Ссылки

- [OpenAPI Specification](./converter-api.yaml) — REST API спецификация
- [API Examples](./converter-api-examples.md) — примеры использования REST API
- [Kafka Events](./converter-kafka-events.md) — описание Kafka сообщений
- [RAG Platform Documentation](https://confluence.company.com/rag) — общая документация платформы

---

## 📝 Схема работы

```
┌─────────────────────────────────────────────────────────────────┐
│                      Converter Service                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │  REST API   │───▶│ Job Manager │───▶│   Background        │ │
│  │  (FastAPI)  │    │ (In-memory) │    │   Worker            │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│         │                                     │                │
│         │                                     ▼                │
│         │                            ┌─────────────────────┐   │
│         │                            │   HDXConverter      │   │
│         │                            │   (core logic)      │   │
│         │                            └─────────────────────┘   │
│         │                                     │                │
│         ▼                                     ▼                │
│  ┌─────────────┐                    ┌─────────────────────┐     │
│  │   Health    │                    │   Kafka Producer    │     │
│  │   Checks    │                    │   (notifications)   │     │
│  └─────────────┘                    └─────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Сравнение способов запуска

| Характеристика | REST API | Kafka |
|----------------|----------|-------|
| **Синхронность** | Асинхронный (возвращает job_id) | Асинхронный (неблокирующий) |
| **Ожидание ответа** | Немедленное получение job_id | Нет немедленного ответа (опционально через reply_to) |
| **Нагрузка** | Ограничена HTTP-сервером | Высокая пропускная способность |
| **Надежность** | Зависит от HTTP | At-least-once / exactly-once |
| **Use Case** | Ручной запуск, отладка, CI/CD | Автоматизированные пайплайны, ETL, массовая обработка |
