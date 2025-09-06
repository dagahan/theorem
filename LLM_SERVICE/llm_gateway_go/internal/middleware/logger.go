package middleware

import (
	"time"

	"llm-gateway/pkg/logger"

	"github.com/gin-gonic/gin"
)

// LoggerMiddleware middleware для логирования запросов
func LoggerMiddleware() gin.HandlerFunc {
	return gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		logger.GetLogger().WithFields(map[string]interface{}{
			"timestamp":   param.TimeStamp.Format(time.RFC3339),
			"status":      param.StatusCode,
			"latency":     param.Latency,
			"client_ip":   param.ClientIP,
			"method":      param.Method,
			"path":        param.Path,
			"user_agent":  param.Request.UserAgent(),
			"error":       param.ErrorMessage,
		}).Info("HTTP Request")
		
		return ""
	})
}

// RecoveryMiddleware middleware для восстановления после паники
func RecoveryMiddleware() gin.HandlerFunc {
	return gin.CustomRecovery(func(c *gin.Context, recovered interface{}) {
		logger.GetLogger().WithField("error", recovered).Error("Panic recovered")
		
		c.JSON(500, gin.H{
			"error":   "Internal Server Error",
			"message": "Something went wrong",
		})
	})
}