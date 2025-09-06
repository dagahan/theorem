package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"llm-gateway/internal/config"
	"llm-gateway/internal/handlers"
	"llm-gateway/internal/middleware"
	"llm-gateway/internal/services"
	"llm-gateway/pkg/database"
	"llm-gateway/pkg/jwt"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

func main() {
	// Загружаем конфигурацию
	cfg, err := config.Load()
	if err != nil {
		logrus.WithError(err).Fatal("Failed to load configuration")
	}

	// Настраиваем логирование
	setupLogging(cfg.Log)

	logrus.Info("Starting LLM Gateway server...")

	// Подключаемся к базе данных
	db, err := database.NewDatabase(&cfg.DB)
	if err != nil {
		logrus.WithError(err).Fatal("Failed to connect to database")
	}
	defer db.Close()

	// Выполняем миграции
	if err := db.AutoMigrate(); err != nil {
		logrus.WithError(err).Fatal("Failed to run database migrations")
	}

	// Создаем JWT менеджер
	jwtManager := jwt.NewJWTManager(cfg.JWT.Secret, cfg.JWT.AccessTokenExpire, cfg.JWT.RefreshTokenExpire)

	// Создаем сервисы
	userService := services.NewUserService(db)
	sessionService := services.NewSessionService(db)

	// Создаем обработчики
	userHandler := handlers.NewUserHandler(userService, sessionService, jwtManager)

	// Настраиваем Gin
	if cfg.Log.Level == "debug" {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	// Добавляем middleware
	router.Use(middleware.LoggingMiddleware())
	router.Use(middleware.RecoveryMiddleware())
	router.Use(middleware.CORSMiddleware())

	// Настраиваем маршруты
	setupRoutes(router, userHandler, jwtManager, userService)

	// Создаем HTTP сервер
	server := &http.Server{
		Addr:    fmt.Sprintf("%s:%s", cfg.Server.Host, cfg.Server.Port),
		Handler: router,
	}

	// Запускаем сервер в горутине
	go func() {
		logrus.WithFields(logrus.Fields{
			"host": cfg.Server.Host,
			"port": cfg.Server.Port,
		}).Info("Server starting...")

		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logrus.WithError(err).Fatal("Failed to start server")
		}
	}()

	// Ждем сигнал для graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logrus.Info("Shutting down server...")

	// Graceful shutdown с таймаутом
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		logrus.WithError(err).Error("Server forced to shutdown")
	}

	logrus.Info("Server exited")
}

// setupLogging настраивает логирование
func setupLogging(logCfg config.LogConfig) {
	// Устанавливаем уровень логирования
	level, err := logrus.ParseLevel(logCfg.Level)
	if err != nil {
		level = logrus.InfoLevel
	}
	logrus.SetLevel(level)

	// Устанавливаем формат логирования
	if logCfg.Format == "json" {
		logrus.SetFormatter(&logrus.JSONFormatter{
			TimestampFormat: time.RFC3339,
		})
	} else {
		logrus.SetFormatter(&logrus.TextFormatter{
			FullTimestamp:   true,
			TimestampFormat: time.RFC3339,
		})
	}
}

// setupRoutes настраивает маршруты API
func setupRoutes(router *gin.Engine, userHandler *handlers.UserHandler, jwtManager *jwt.JWTManager, userService *services.UserService) {
	// Группа для публичных маршрутов
	public := router.Group("/api/v1")
	{
		// Маршруты для пользователей
		users := public.Group("/users")
		{
			users.POST("/register", userHandler.Register)
			users.POST("/login", userHandler.Login)
		}
	}

	// Группа для защищенных маршрутов
	protected := router.Group("/api/v1")
	protected.Use(middleware.AuthMiddleware(jwtManager, userService))
	{
		// Маршруты для пользователей
		users := protected.Group("/users")
		{
			users.POST("/logout", userHandler.Logout)
			users.GET("/profile", userHandler.GetProfile)
			users.PUT("/profile", userHandler.UpdateProfile)
		}

		// Маршруты только для админов
		admin := protected.Group("/admin")
		admin.Use(middleware.RequireRole(models.RoleAdmin, models.RoleGod))
		{
			admin.POST("/ban", userHandler.BanUser)
			admin.POST("/unban", userHandler.UnbanUser)
		}
	}

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":    "ok",
			"timestamp": time.Now().Format(time.RFC3339),
			"service":   "llm-gateway",
		})
	})

	// 404 handler
	router.NoRoute(func(c *gin.Context) {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Not found",
			"code":  http.StatusNotFound,
		})
	})
}