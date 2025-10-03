# Theorem Frontend

Frontend для AI-наставника Theorem по подготовке к ЕГЭ по математике.

## Конфигурация

Все настройки фронтенда управляются через глобальный `.env` файл в `/home/usov/myprojects/theorem/LLM_SERVICE/.env`.

### Основные переменные окружения:

```bash
# API Configuration
VITE_API_BASE_URL=http://100.87.209.118:8080
VITE_API_TIMEOUT=10000

# Frontend Configuration  
FRONTEND_HOST=192.168.0.102
FRONTEND_PORT=4173
FRONTEND_PROTOCOL=http
FRONTEND_NGINX_PORT=4173
FRONTEND_NGINX_DEV_PORT=5173

# Environment
NODE_ENV=production
```

## Запуск

### Production режим:
```bash
./entrypoint.sh
```

### Development режим:
```bash
NODE_ENV=development npm run dev
```

### Сборка:
```bash
npm run build
```

## Изменение конфигурации

1. Отредактируйте файл `/home/usov/myprojects/theorem/LLM_SERVICE/.env`
2. Пересоберите фронтенд: `npm run build`
3. Перезапустите сервис: `./entrypoint.sh`

## Структура проекта

- `src/config.js` - Конфигурация приложения
- `src/api/client.js` - API клиент
- `src/auth.js` - Управление аутентификацией
- `src/pages/` - Страницы приложения
- `entrypoint.sh` - Скрипт запуска