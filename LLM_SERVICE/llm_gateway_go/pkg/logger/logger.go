package logger

import (
	"os"

	"github.com/sirupsen/logrus"
)

// Logger глобальный экземпляр логгера
var Logger *logrus.Logger

// Init инициализирует логгер
func Init() {
	Logger = logrus.New()
	
	// Настройка формата вывода
	Logger.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
		TimestampFormat: "2006-01-02 15:04:05",
	})
	
	// Уровень логирования
	Logger.SetLevel(logrus.InfoLevel)
	
	// Вывод в stdout
	Logger.SetOutput(os.Stdout)
}

// GetLogger возвращает экземпляр логгера
func GetLogger() *logrus.Logger {
	if Logger == nil {
		Init()
	}
	return Logger
}