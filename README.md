# theorem

Микросервисная архитектура с Gateway и VLLM сервисом для работы с языковыми моделями.

## Структура проекта

- `gateway/` - FastAPI Gateway сервис
- `vllm/` - VLLM сервис для работы с языковыми моделями
- `docker-compose.yaml` - Конфигурация Docker Compose
- `.env` - Переменные окружения

## Запуск

1. Убедитесь, что Docker и Docker Compose установлены
2. Запустите все сервисы:
   ```bash
   docker compose up --build
   ```

3. Или запустите только VLLM сервис:
   ```bash
   docker compose up vllm --build
   ```

## Тестирование VLLM

После запуска VLLM сервиса, вы можете протестировать его работу:

```bash
python test_vllm.py
```

## API Endpoints

### VLLM Service (порт 8000)
- `GET /health` - Проверка здоровья сервиса
- `POST /v1/chat/completions` - Генерация текста

### Gateway Service (порт 10080)
- FastAPI документация доступна по адресу: http://localhost:10080/docs

## Модель

По умолчанию используется TinyLlama-1.1B-Chat-v1.0 - небольшая тестовая модель, которая автоматически загружается при первом запуске.

## Переменные окружения

Основные настройки в файле `.env`:
- `VLLM_PORT=8000` - Порт VLLM сервиса
- `GATEWAY_PORT=10080` - Порт Gateway сервиса
