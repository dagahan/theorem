package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/dagahan/theorem/users/internal/app"
	"github.com/dagahan/theorem/users/internal/config"
)

func main() {
	logger := setupLogger()

	cfg, err := config.NewConfig()
	if err != nil {
		logger.Error("failed to read config", slog.Any("error", err))
		os.Exit(1)
	}

	a, err := app.New(context.Background(), cfg, logger)
	if err != nil {
		logger.Error("failed to create app",
			"error", err,
		)
		os.Exit(1)
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	errChan := make(chan error)
	go a.Start(errChan)

	select {
	case err := <-errChan:
		logger.Error("failed to start server",
			"error", err,
		)
		os.Exit(1)
	case <-ctx.Done():
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := a.Stop(ctx); err != nil {
			logger.Error("failed to stop server",
				"error", err,
			)
			os.Exit(1)
		}
	}
}

// setupLogger creates a new slog logger with JSON handler at debug level
func setupLogger() *slog.Logger {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		AddSource: true,
		Level:     slog.LevelDebug,
	})

	logger := slog.New(handler)
	return logger
}
