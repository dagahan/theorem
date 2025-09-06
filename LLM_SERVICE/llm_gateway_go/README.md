# LLM Gateway

Современный API Gateway для LLM сервисов, написанный на Go с использованием Gin фреймворка.

## Особенности

- 🔐 **Аутентификация и авторизация** - JWT токены с refresh механизмом
- 👥 **Управление пользователями** - регистрация, вход, профили
- 🛡️ **Безопасность** - хеширование паролей, валидация данных
- 📊 **Логирование** - структурированные логи с Logrus
- 🐳 **Docker** - готовые контейнеры для разработки и продакшена
- 🗄️ **База данных** - PostgreSQL с GORM ORM
- ⚡ **Производительность** - оптимизированный для высокой нагрузки
- 🔧 **Конфигурация** - гибкая настройка через переменные окружения

## Архитектура

```
llm-gateway/
├── cmd/server/          # Точка входа приложения
├── internal/            # Внутренние пакеты
│   ├── config/         # Конфигурация
│   ├── handlers/       # HTTP обработчики
│   ├── middleware/     # Middleware для Gin
│   ├── models/         # Модели данных и DTO
│   ├── services/       # Бизнес-логика
│   └── utils/          # Утилиты
├── pkg/                # Публичные пакеты
│   ├── auth/          # Аутентификация
│   ├── database/      # Работа с БД
│   └── jwt/           # JWT токены
└── web/               # Статические файлы
```

## Быстрый старт

### Предварительные требования

- Go 1.22+
- Docker и Docker Compose
- PostgreSQL (если запускаете локально)

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd llm-gateway
```

2. **Установите зависимости:**
```bash
make deps
```

3. **Настройте переменные окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл под ваши нужды
```

4. **Запустите с Docker Compose:**
```bash
make docker-compose-up
```

Или запустите локально:

```bash
# Запустите PostgreSQL и Redis
docker-compose up -d postgres redis

# Запустите приложение
make run
```

## API Документация

### Аутентификация

Все защищенные эндпоинты требуют заголовок:
```
Authorization: Bearer <access_token>
```

### Эндпоинты

#### Публичные

- `POST /api/v1/users/register` - Регистрация пользователя
- `POST /api/v1/users/login` - Вход пользователя
- `GET /health` - Проверка здоровья сервиса

#### Защищенные

- `POST /api/v1/users/logout` - Выход пользователя
- `GET /api/v1/users/profile` - Получить профиль
- `PUT /api/v1/users/profile` - Обновить профиль

#### Административные

- `POST /api/v1/admin/ban` - Заблокировать пользователя
- `POST /api/v1/admin/unban` - Разблокировать пользователя

### Примеры запросов

#### Регистрация
```bash
curl -X POST http://localhost:8080/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "password": "SecurePass123!"
  }'
```

#### Вход
```bash
curl -X POST http://localhost:8080/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "testuser",
    "password": "SecurePass123!"
  }'
```

#### Получение профиля
```bash
curl -X GET http://localhost:8080/api/v1/users/profile \
  -H "Authorization: Bearer <access_token>"
```

## Конфигурация

Все настройки приложения управляются через переменные окружения:

### Сервер
- `SERVER_HOST` - Хост сервера (по умолчанию: 0.0.0.0)
- `SERVER_PORT` - Порт сервера (по умолчанию: 8080)

### База данных
- `DB_HOST` - Хост PostgreSQL
- `DB_PORT` - Порт PostgreSQL
- `DB_USER` - Пользователь БД
- `DB_PASSWORD` - Пароль БД
- `DB_NAME` - Имя БД
- `DB_SSLMODE` - SSL режим

### JWT
- `JWT_SECRET` - Секретный ключ для JWT
- `JWT_ACCESS_TOKEN_EXPIRE` - Время жизни access токена
- `JWT_REFRESH_TOKEN_EXPIRE` - Время жизни refresh токена

### Redis
- `REDIS_HOST` - Хост Redis
- `REDIS_PORT` - Порт Redis
- `REDIS_PASSWORD` - Пароль Redis
- `REDIS_DB` - Номер БД Redis

### Логирование
- `LOG_LEVEL` - Уровень логирования (debug, info, warn, error)
- `LOG_FORMAT` - Формат логов (json, text)

## Разработка

### Команды Make

```bash
make help              # Показать все доступные команды
make build             # Собрать приложение
make run               # Запустить приложение
make test              # Запустить тесты
make fmt               # Форматировать код
make lint              # Проверить код
make docker-build      # Собрать Docker образ
make docker-compose-up # Запустить все сервисы
make dev               # Запуск в режиме разработки с hot reload
```

### Структура проекта

Проект следует стандартным Go конвенциям:

- `cmd/` - Точки входа приложений
- `internal/` - Приватные пакеты приложения
- `pkg/` - Публичные пакеты, которые могут использоваться другими проектами
- `web/` - Статические файлы

### Паттерны

- **Dependency Injection** - Сервисы внедряются через конструкторы
- **Repository Pattern** - Абстракция доступа к данным
- **Middleware Pattern** - Перехватчики для HTTP запросов
- **Service Layer** - Бизнес-логика отделена от HTTP слоя

## Безопасность

- Пароли хешируются с помощью bcrypt
- JWT токены подписываются HMAC-SHA256
- IP адреса хешируются для анонимности
- Валидация всех входящих данных
- CORS настроен для безопасности
- Graceful shutdown для корректного завершения

## Мониторинг

- Health check эндпоинт: `GET /health`
- Структурированные логи в JSON формате
- Метрики производительности
- Graceful shutdown с таймаутом

## Лицензия

MIT License

## Вклад в проект

1. Fork репозиторий
2. Создайте feature branch
3. Сделайте commit изменений
4. Push в branch
5. Создайте Pull Request

## Поддержка

Если у вас есть вопросы или проблемы, создайте issue в репозитории.