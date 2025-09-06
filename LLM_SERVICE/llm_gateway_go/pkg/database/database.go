package database

import (
	"fmt"

	"llm-gateway/internal/config"
	"llm-gateway/internal/models"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// Database представляет подключение к базе данных
type Database struct {
	DB *gorm.DB
}

// NewDatabase создает новое подключение к базе данных
func NewDatabase(cfg *config.DatabaseConfig) (*Database, error) {
	dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.Name, cfg.SSLMode)

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	return &Database{DB: db}, nil
}

// AutoMigrate выполняет автоматическую миграцию моделей
func (d *Database) AutoMigrate() error {
	return d.DB.AutoMigrate(
		&models.User{},
		&models.Image{},
		&models.Session{},
	)
}

// Close закрывает подключение к базе данных
func (d *Database) Close() error {
	sqlDB, err := d.DB.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

// GetDB возвращает экземпляр GORM DB
func (d *Database) GetDB() *gorm.DB {
	return d.DB
}