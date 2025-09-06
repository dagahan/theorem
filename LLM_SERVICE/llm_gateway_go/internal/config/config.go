package config

import (
	"os"
	"strconv"
	"time"

	"github.com/joho/godotenv"
	"github.com/sirupsen/logrus"
)

// Config содержит всю конфигурацию приложения
type Config struct {
	Server ServerConfig
	DB     DatabaseConfig
	JWT    JWTConfig
	Redis  RedisConfig
	S3     S3Config
	Log    LogConfig
}

// ServerConfig содержит конфигурацию сервера
type ServerConfig struct {
	Host string
	Port string
}

// DatabaseConfig содержит конфигурацию базы данных
type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	Name     string
	SSLMode  string
}

// JWTConfig содержит конфигурацию JWT
type JWTConfig struct {
	Secret                string
	AccessTokenExpire     time.Duration
	RefreshTokenExpire    time.Duration
}

// RedisConfig содержит конфигурацию Redis
type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

// S3Config содержит конфигурацию S3
type S3Config struct {
	Bucket          string
	Region          string
	Endpoint        string
	AccessKeyID     string
	SecretAccessKey string
}

// LogConfig содержит конфигурацию логирования
type LogConfig struct {
	Level  string
	Format string
}

// Load загружает конфигурацию из переменных окружения
func Load() (*Config, error) {
	// Загружаем .env файл если он существует
	if err := godotenv.Load(); err != nil {
		logrus.Warn("No .env file found, using system environment variables")
	}

	config := &Config{
		Server: ServerConfig{
			Host: getEnv("SERVER_HOST", "0.0.0.0"),
			Port: getEnv("SERVER_PORT", "8080"),
		},
		DB: DatabaseConfig{
			Host:     getEnv("DB_HOST", "localhost"),
			Port:     getEnv("DB_PORT", "5432"),
			User:     getEnv("DB_USER", "postgres"),
			Password: getEnv("DB_PASSWORD", "password"),
			Name:     getEnv("DB_NAME", "llm_gateway"),
			SSLMode:  getEnv("DB_SSLMODE", "disable"),
		},
		JWT: JWTConfig{
			Secret:             getEnv("JWT_SECRET", "your-super-secret-jwt-key"),
			AccessTokenExpire:  getDurationEnv("JWT_ACCESS_TOKEN_EXPIRE", 15*time.Minute),
			RefreshTokenExpire: getDurationEnv("JWT_REFRESH_TOKEN_EXPIRE", 7*24*time.Hour),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       getIntEnv("REDIS_DB", 0),
		},
		S3: S3Config{
			Bucket:          getEnv("S3_BUCKET", "llm-gateway-uploads"),
			Region:          getEnv("S3_REGION", "us-east-1"),
			Endpoint:        getEnv("S3_ENDPOINT", ""),
			AccessKeyID:     getEnv("AWS_ACCESS_KEY_ID", ""),
			SecretAccessKey: getEnv("AWS_SECRET_ACCESS_KEY", ""),
		},
		Log: LogConfig{
			Level:  getEnv("LOG_LEVEL", "info"),
			Format: getEnv("LOG_FORMAT", "json"),
		},
	}

	return config, nil
}

// getEnv получает переменную окружения или возвращает значение по умолчанию
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getIntEnv получает переменную окружения как int или возвращает значение по умолчанию
func getIntEnv(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

// getDurationEnv получает переменную окружения как time.Duration или возвращает значение по умолчанию
func getDurationEnv(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}