package handlers

import (
	"llm-gateway/internal/middleware"
	"llm-gateway/internal/services"
	"llm-gateway/pkg/auth"

	"github.com/gin-gonic/gin"
)

// SetupRoutes настраивает маршруты API
func SetupRoutes(
	userService *services.UserService,
	sessionService *services.SessionService,
	jwtService *auth.JWTService,
) *gin.Engine {
	// Создаем Gin роутер
	router := gin.New()

	// Добавляем middleware
	router.Use(middleware.LoggerMiddleware())
	router.Use(middleware.RecoveryMiddleware())

	// Создаем обработчики
	userHandler := NewUserHandler(userService, sessionService, jwtService)

	// API v1
	v1 := router.Group("/api/v1")
	{
		// Публичные маршруты (не требуют аутентификации)
		public := v1.Group("/")
		{
			public.POST("/register", userHandler.Register)
			public.POST("/login", userHandler.Login)
		}

		// Защищенные маршруты (требуют аутентификации)
		protected := v1.Group("/")
		protected.Use(middleware.AuthMiddleware(jwtService))
		{
			// Пользовательские маршруты
			users := protected.Group("/users")
			{
				users.GET("/profile", userHandler.GetProfile)
				users.POST("/logout", userHandler.Logout)
			}

			// Административные маршруты
			admin := protected.Group("/admin")
			admin.Use(middleware.RequireAdmin())
			{
				admin.POST("/ban", userHandler.BanUser)
				admin.POST("/unban", userHandler.UnbanUser)
			}
		}
	}

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "ok",
			"service": "llm-gateway",
		})
	})

	return router
}