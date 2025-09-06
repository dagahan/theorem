package middleware

import (
	"net/http"

	"llm-gateway/internal/models"
	"llm-gateway/internal/services"
	"llm-gateway/pkg/jwt"

	"github.com/gin-gonic/gin"
)

// AuthMiddleware создает middleware для аутентификации
func AuthMiddleware(jwtManager *jwt.JWTManager, userService *services.UserService) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error: "Authorization header is required",
				Code:  http.StatusUnauthorized,
			})
			c.Abort()
			return
		}

		tokenString, err := jwt.ExtractTokenFromHeader(authHeader)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:   "Invalid authorization header format",
				Message: err.Error(),
				Code:    http.StatusUnauthorized,
			})
			c.Abort()
			return
		}

		claims, err := jwtManager.ValidateToken(tokenString)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:   "Invalid token",
				Message: err.Error(),
				Code:    http.StatusUnauthorized,
			})
			c.Abort()
			return
		}

		// Проверяем что это access токен
		if claims.Type != "access" {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error: "Invalid token type",
				Code:  http.StatusUnauthorized,
			})
			c.Abort()
			return
		}

		// Получаем пользователя из базы данных
		user, err := userService.GetUserByID(claims.UserID)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:   "User not found",
				Message: err.Error(),
				Code:    http.StatusUnauthorized,
			})
			c.Abort()
			return
		}

		// Проверяем что пользователь активен
		if !user.IsActive {
			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Error: "User is inactive",
				Code:  http.StatusForbidden,
			})
			c.Abort()
			return
		}

		// Сохраняем данные пользователя в контекст
		c.Set("user", user)
		c.Set("userID", claims.UserID)
		c.Set("sessionID", claims.SessionID)
		c.Set("userRole", claims.Role)

		c.Next()
	}
}

// RequireRole создает middleware для проверки роли пользователя
func RequireRole(requiredRoles ...models.UserRole) gin.HandlerFunc {
	return func(c *gin.Context) {
		userRole, exists := c.Get("userRole")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error: "User role not found in context",
				Code:  http.StatusUnauthorized,
			})
			c.Abort()
			return
		}

		role, ok := userRole.(string)
		if !ok {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error: "Invalid user role type",
				Code:  http.StatusInternalServerError,
			})
			c.Abort()
			return
		}

		// Проверяем есть ли роль пользователя в списке требуемых ролей
		hasRequiredRole := false
		for _, requiredRole := range requiredRoles {
			if string(requiredRole) == role {
				hasRequiredRole = true
				break
			}
		}

		if !hasRequiredRole {
			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Error: "Insufficient permissions",
				Code:  http.StatusForbidden,
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// OptionalAuth создает middleware для опциональной аутентификации
func OptionalAuth(jwtManager *jwt.JWTManager, userService *services.UserService) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.Next()
			return
		}

		tokenString, err := jwt.ExtractTokenFromHeader(authHeader)
		if err != nil {
			c.Next()
			return
		}

		claims, err := jwtManager.ValidateToken(tokenString)
		if err != nil {
			c.Next()
			return
		}

		if claims.Type != "access" {
			c.Next()
			return
		}

		user, err := userService.GetUserByID(claims.UserID)
		if err != nil || !user.IsActive {
			c.Next()
			return
		}

		// Сохраняем данные пользователя в контекст если токен валиден
		c.Set("user", user)
		c.Set("userID", claims.UserID)
		c.Set("sessionID", claims.SessionID)
		c.Set("userRole", claims.Role)

		c.Next()
	}
}