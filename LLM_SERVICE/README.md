# LLM Service Microservices

Микросервисная архитектура для работы с LLM, состоящая из трех основных сервисов:

- **RAG Service (Go)** - основной сервис для обработки запросов и поиска документов
- **Embedder Service (Python)** - сервис для векторизации текстовых данных
- **QdrantDB** - векторная база данных для хранения эмбеддингов
- **vLLM Service** - сервис для запуска LLM моделей

## Архитектура

```
┌─────────────┐    gRPC    ┌─────────────┐    HTTP    ┌─────────────┐
│   Client    │ ────────── │ RAG Service │ ────────── │ QdrantDB    │
└─────────────┘            └─────────────┘            └─────────────┘
                                    │
                               gRPC │
                                    ▼
                            ┌─────────────┐
                            │ Embedder    │
                            │ Service     │
                            └─────────────┘
```

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Go 1.22+ (для локальной разработки)
- Python 3.13+ (для локальной разработки)

### Запуск всех сервисов

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd llm-service

# Запустите все сервисы
docker-compose up -d

# Проверьте статус
docker-compose ps
```

### Загрузка документов

```bash
# Загрузите документы в Qdrant
python3 scripts/upload_documents.py path/to/document.xlsx

# Или с дополнительными параметрами
python3 scripts/upload_documents.py path/to/document.xml \
  --embedder-host localhost:50051 \
  --qdrant-host localhost:6333 \
  --collection-name documents \
  --chunk-size 250 \
  --chunk-overlap 50
```

## API Документация

### RAG Service (Go)

**Базовый URL:** `http://localhost:8080`

#### Эндпоинты

- `POST /api/v1/search` - Поиск документов
- `GET /health` - Проверка здоровья сервиса

#### Примеры запросов

```bash
# Поиск документов
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "где указан остаток хода?",
    "top_k": 20
  }'

# Проверка здоровья
curl http://localhost:8080/health
```

### Embedder Service (Python)

**gRPC порт:** `50051`

#### Методы

- `EmbedText` - Векторизация одного текста
- `EmbedBatch` - Векторизация пакета текстов

### vLLM Service

**Базовый URL:** `http://localhost:8000`

#### Эндпоинты

- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `GET /health` - Проверка здоровья

## Конфигурация

### Переменные окружения

Основные настройки в `.env`:

```env
# DOCKER & COMPOSE CONFIGURATION
COMPOSE_PROJECT_NAME=llm-service
DOCKER_CONTAINERS_RESTART=no
TZ=UTC

# QDRANT SERVICE CONFIGURATION
QDRANT_HOST=localhost
QDRANT_PORT=6333

# EMBEDDER SERVICE CONFIGURATION
EMBEDDER_HOST=localhost
EMBEDDER_PORT=50051

# RAG SERVICE CONFIGURATION
RAG_HOST=localhost
RAG_PORT=8080

# VLLM_MATH SERVICE CONFIGURATION
VLLM_MATH_HOST=localhost
VLLM_MATH_PORT=8000
MODEL_SRC=Qwen/Qwen2-0.5B-Instruct
MODEL_NAME=Qwen2-0.5B-Instruct
MAX_LEN=1024
TP_SIZE=1
HF_CACHE_DIR=/data/hf-cache
GPU_UTIL=0.92
DTYPE=auto

# MODEL CONFIGURATION
EMBEDDER_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
LOG_LEVEL=info
LOG_FORMAT=json
```

## Разработка

### Локальная разработка

```bash
# Запустите зависимости
docker-compose up -d qdrant embedder

# Запустите RAG сервис локально
cd rag
go run cmd/server/main.go

# Запустите Embedder сервис локально
cd embedder_python
uv run python src/services/embedder_service.py
```

### Сборка образов

```bash
# Сборка всех образов
docker-compose build

# Сборка конкретного сервиса
docker-compose build rag
docker-compose build embedder
docker-compose build qdrant
```

### Логи

```bash
# Просмотр логов всех сервисов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f rag
docker-compose logs -f embedder
docker-compose logs -f qdrant
```

## Поддерживаемые форматы документов

### Excel (.xlsx)
Ожидаемые столбцы:
- "Раздел руководства"
- "Вопросы" 
- "Ответ"

### XML (Wikipedia dump)
Стандартный формат Wikipedia XML dump.

## Мониторинг

### Health Checks

```bash
# RAG Service
curl http://localhost:8080/health

# vLLM Service
curl http://localhost:8000/health

# Qdrant
curl http://localhost:6333/health
```

### Метрики

- RAG Service: логи в JSON формате
- Embedder Service: структурированные логи
- Qdrant: встроенные метрики на порту 6333

## Troubleshooting

### Частые проблемы

1. **Сервис не запускается**
   ```bash
   # Проверьте логи
   docker-compose logs <service_name>
   
   # Проверьте статус
   docker-compose ps
   ```

2. **Ошибки подключения к gRPC**
   ```bash
   # Убедитесь что embedder сервис запущен
   docker-compose ps embedder
   
   # Проверьте сеть
   docker network ls
   ```

3. **Проблемы с Qdrant**
   ```bash
   # Проверьте доступность
   curl http://localhost:6333/health
   
   # Очистите данные
   docker-compose down
   rm -rf qdrant-data
   docker-compose up -d
   ```

## Лицензия

MIT License