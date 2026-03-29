# HDX Converter

A modular tool for converting HDX documentation to multiple formats (TXT, MD, JSON) with comprehensive metadata extraction.

## Features

- Extracts content from HDX (HTML) files
- Preserves internal links and navigation
- Generates structured metadata in JSON format (schema 1.2)
- Converts to multiple formats: TXT, Markdown, HTML backup
- Validates metadata completeness
- Handles images and tables
- Provides detailed statistics and reporting
- Modular architecture for easy extension

## Установка

### Создание и активация виртуального окружения
```bash
# Перейдите в директорию проекта
cd /path/to/rag-soc-core/services/rag-soc-converter

# Создание виртуального окружения
python3 -m venv venv_converter

# Активация виртуального окружения
# Для Windows (GitBash):
. venv_converter/Scripts/activate
```

### Установка зависимостей
```bash
# Убедитесь, что виртуальное окружение активировано
# В командной строке должно быть (venv_converter)

# Установка зависимостей
pip install fastapi uvicorn kafka-python prometheus-client

# Для работы с S3 (если нужно)
pip install boto3

# Если есть файл requirements.txt (рекомендованный способ)
pip install -r requirements.txt
```

### Проверка установки
```bash
# Проверка установленных пакетов
pip list | grep -E "fastapi|uvicorn|kafka|prometheus"

# Ожидаемый вывод:
# fastapi              0.104.0
# kafka-python         2.0.2
# prometheus-client    0.19.0
# uvicorn              0.24.0
```

### Сборка контейнера
```bash
# Создание директорий для данных
mkdir -p /tmp/converter_input /tmp/converter_output

# Сборка образа
docker build -t rag-soc-converter:1.0.8 .
```

## Запуск API сервера

### Вариант 1: Минимальный запуск (без Kafka)
```bash
# Из корневой директории проекта
python -m hdx_converter.cli api --host 0.0.0.0 --port 8080
```

### Вариант 2: С указанием уровня логирования
```bash
# DEBUG режим для отладки
python -m hdx_converter.cli api --host 0.0.0.0 --port 8080 --log-level 3
```

### Вариант 3: С включенной Kafka интеграцией
```bash
# С локальным Kafka
python -m hdx_converter.cli api \
  --host 0.0.0.0 \
  --port 8080 \
  --kafka-enabled \
  --kafka-bootstrap-servers localhost:9092 \
  --log-level 3
```

### Вариант 4: В docker с выключенной Kafka
```bash
# Запуск контейнера
docker run -d \
  --name rag-soc-converter \
  -p 8080:8080 \
  -v /tmp/converter_input:/data/input:ro \
  -v /tmp/converter_output:/data/output \
  -e KAFKA_ENABLED=false \
  rag-soc-converter:1.0.8

# Просмотр логов
docker logs rag-soc-converter

# Остановка
docker stop rag-soc-converter 2>/dev/null || true

# Удаление
docker rm rag-soc-converter 2>/dev/null || true
docker rmi rag-soc-converter:1.0.8 2>/dev/null || true
```

### Вариант 5: Через docker compose c выключенной Kafka (рекомендованный способ)
```bash
# Запуск в фоне
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Перезапуск
docker-compose restart
```


## Тестирование

### Проверка работоспособности

В другом терминале выполните проверку

```bash
# Проверка health
curl http://localhost:8080/health

# Ожидаемый ответ:
# {"status":"healthy","version":"1.0.0","components":{}}

# Проверка ready
curl http://localhost:8080/ready

# Ожидаемый ответ:
# {"ready":true,"checks":{"object_storage":true,"kafka":true}}

# Проверка OpenAPI документации
# Откройте в браузере: http://localhost:8080/docs
```

### Тестирование API

#### Запуск конвертации

```bash
# Создайте тестовый HDX файл или используйте существующий
# Запустите конвертацию
curl -X POST http://localhost:8080/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{
    "source_uri": "../../source/HiSecEngine_USG6000F_V600R024C10_04_en_AEP01098.hdx",
    "output_uri": "../../../../output",
    "log_level": 2
  }'
```

Ожидаемый вывод:

``` json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "source_uri": "/path/to/your/test.hdx",
  "output_uri": "/path/to/output",
  "created_at": "2024-03-27T10:00:00Z"
}
```


#### Проверка статуса задачи

```bash
# Замените JOB_ID на полученный из предыдущего ответа
curl http://localhost:8080/api/v1/convert/JOB_ID/status
```

#### Получение списка задач

```bash
# Все задачи
curl http://localhost:8080/api/v1/convert

# Только завершенные
curl "http://localhost:8080/api/v1/convert?status=completed"

# С пагинацией
curl "http://localhost:8080/api/v1/convert?limit=10&offset=0"
```


