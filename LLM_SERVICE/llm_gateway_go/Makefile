# Makefile для LLM Gateway

# Переменные
BINARY_NAME=llm-gateway
DOCKER_IMAGE=llm-gateway
DOCKER_TAG=latest

# Цвета для вывода
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m # No Color

.PHONY: help build run test clean docker-build docker-run docker-compose-up docker-compose-down

# Помощь
help: ## Показать справку
	@echo "$(GREEN)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Сборка приложения
build: ## Собрать приложение
	@echo "$(GREEN)Сборка приложения...$(NC)"
	go build -o $(BINARY_NAME) ./cmd/server

# Запуск приложения
run: ## Запустить приложение
	@echo "$(GREEN)Запуск приложения...$(NC)"
	go run ./cmd/server

# Тестирование
test: ## Запустить тесты
	@echo "$(GREEN)Запуск тестов...$(NC)"
	go test -v ./...

# Очистка
clean: ## Очистить собранные файлы
	@echo "$(GREEN)Очистка...$(NC)"
	go clean
	rm -f $(BINARY_NAME)

# Установка зависимостей
deps: ## Установить зависимости
	@echo "$(GREEN)Установка зависимостей...$(NC)"
	go mod download
	go mod tidy

# Форматирование кода
fmt: ## Форматировать код
	@echo "$(GREEN)Форматирование кода...$(NC)"
	go fmt ./...

# Проверка кода
lint: ## Проверить код
	@echo "$(GREEN)Проверка кода...$(NC)"
	golangci-lint run

# Сборка Docker образа
docker-build: ## Собрать Docker образ
	@echo "$(GREEN)Сборка Docker образа...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

# Запуск Docker контейнера
docker-run: ## Запустить Docker контейнер
	@echo "$(GREEN)Запуск Docker контейнера...$(NC)"
	docker run -p 8080:8080 --env-file .env $(DOCKER_IMAGE):$(DOCKER_TAG)

# Запуск с docker-compose
docker-compose-up: ## Запустить все сервисы с docker-compose
	@echo "$(GREEN)Запуск всех сервисов...$(NC)"
	docker-compose up -d

# Остановка docker-compose
docker-compose-down: ## Остановить все сервисы
	@echo "$(GREEN)Остановка всех сервисов...$(NC)"
	docker-compose down

# Просмотр логов
logs: ## Просмотр логов
	@echo "$(GREEN)Просмотр логов...$(NC)"
	docker-compose logs -f

# Перезапуск сервисов
restart: docker-compose-down docker-compose-up ## Перезапустить все сервисы

# Полная очистка (включая Docker)
clean-all: clean docker-compose-down ## Полная очистка
	@echo "$(GREEN)Полная очистка...$(NC)"
	docker system prune -f
	docker volume prune -f

# Разработка - запуск с hot reload
dev: ## Запуск в режиме разработки
	@echo "$(GREEN)Запуск в режиме разработки...$(NC)"
	@if command -v air > /dev/null; then \
		air; \
	else \
		echo "$(YELLOW)Air не установлен. Устанавливаем...$(NC)"; \
		go install github.com/cosmtrek/air@latest; \
		air; \
	fi

# Генерация документации
docs: ## Генерировать документацию
	@echo "$(GREEN)Генерация документации...$(NC)"
	godoc -http=:6060

# Проверка безопасности
security: ## Проверка безопасности
	@echo "$(GREEN)Проверка безопасности...$(NC)"
	gosec ./...

# Бенчмарки
bench: ## Запустить бенчмарки
	@echo "$(GREEN)Запуск бенчмарков...$(NC)"
	go test -bench=. ./...

# Покрытие тестами
coverage: ## Показать покрытие тестами
	@echo "$(GREEN)Покрытие тестами...$(NC)"
	go test -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html
	@echo "$(GREEN)Отчет сохранен в coverage.html$(NC)"