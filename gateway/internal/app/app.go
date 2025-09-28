package app

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"time"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	"github.com/dagahan/theorem/gateway/internal/config"
	authservice "github.com/dagahan/theorem/gateway/internal/service/auth"
	llmservice "github.com/dagahan/theorem/gateway/internal/service/llm"
	authmiddleware "github.com/dagahan/theorem/gateway/internal/transport/http/middleware/auth"
	authhandler "github.com/dagahan/theorem/gateway/internal/transport/http/v1/auth"
	llmhandler "github.com/dagahan/theorem/gateway/internal/transport/http/v1/llm"
	llmpb "github.com/dagahan/theorem/gen/go/llm_gateway/v1"
	userpb "github.com/dagahan/theorem/gen/go/users/v1"
)

type App struct {
	e                   *echo.Echo
	llmGatewayGRPCConn  *grpc.ClientConn
	userServiceGRPCConn *grpc.ClientConn
	cfg                 *config.Config
	l                   *slog.Logger
}

// New creates and initializes a new instance of App
func New(cfg *config.Config, l *slog.Logger) (*App, error) {
	a := &App{
		cfg: cfg,
		l:   l,
	}

	if err := a.initLLMGatewayGRPCConn(); err != nil {
		return nil, fmt.Errorf("failed to init llm service grpc client: %w", err)
	}
	llmGatewayGRPCClient := llmpb.NewLLMGatewayServiceClient(a.llmGatewayGRPCConn)

	if err := a.initUserServiceGRPCConn(); err != nil {
		return nil, fmt.Errorf("failed to init users service grpc client: %w", err)
	}
	authServiceGRPCClient := userpb.NewAuthServiceClient(a.userServiceGRPCConn)

	llmService := llmservice.New(a.l, llmGatewayGRPCClient)
	authService := authservice.New(a.l, authServiceGRPCClient)

	authMiddleware := authmiddleware.New(authService)

	llmHandler := llmhandler.New(llmService, authMiddleware)
	authHandler := authhandler.New(authService)

	a.initEcho()

	apiGroup := a.e.Group("/api/v1")
	llmGroup := apiGroup.Group("/llm")
	authGroup := apiGroup.Group("/auth")

	llmHandler.Setup(llmGroup)
	authHandler.Setup(authGroup)

	return a, nil
}

// Start performs a start of all functional services
func (a *App) Start(errChan chan<- error) {
	a.l.Info("Starting...",
		"addr", a.cfg.Server.Addr,
	)
	if err := a.e.Start(a.cfg.Server.Addr); err != nil && !errors.Is(err, http.ErrServerClosed) {
		errChan <- err
	}
}

func (a *App) Stop(ctx context.Context) error {
	a.l.Info("[!] Shutting down...")

	var stopErr error

	a.l.Info("Stopping http server...")
	if err := a.e.Shutdown(ctx); err != nil {
		stopErr = errors.Join(stopErr, fmt.Errorf("failed to stop http server: %w", err))
	}

	a.l.Info("Closing connection to llm gateway...")
	if err := a.llmGatewayGRPCConn.Close(); err != nil {
		stopErr = errors.Join(stopErr, fmt.Errorf("failed to close gRPC connection to llm gateway: %w", err))
	}

	if stopErr != nil {
		return stopErr
	}

	a.l.Info("Stopped gracefully!")
	return nil
}

// initEcho sets up a new Echo instance with logger
func (a *App) initEcho() {
	a.e = echo.New()
	a.e.HideBanner = true
	a.e.HidePort = true
	a.e.Pre(middleware.RemoveTrailingSlash())

	a.e.Use(middleware.CORSWithConfig(middleware.CORSConfig{
		AllowOrigins: []string{a.cfg.Server.CORSOrigin},
	}))

	a.e.Use(middleware.RequestLoggerWithConfig(middleware.RequestLoggerConfig{
		LogStatus:   true,
		LogURI:      true,
		LogError:    true,
		HandleError: true,
		LogValuesFunc: func(c echo.Context, v middleware.RequestLoggerValues) error {
			if v.Error == nil {
				a.l.LogAttrs(context.Background(), slog.LevelInfo, "REQUEST",
					slog.String("uri", v.URI),
					slog.Int("status", v.Status),
					slog.String("ip", v.RemoteIP),
					slog.String("latency", time.Now().Sub(v.StartTime).String()),
				)
			} else {
				a.l.LogAttrs(context.Background(), slog.LevelError, "REQUEST_ERROR",
					slog.String("uri", v.URI),
					slog.Int("status", v.Status),
					slog.String("ip", v.RemoteIP),
					slog.String("latency", time.Now().Sub(v.StartTime).String()),
					slog.String("err", v.Error.Error()),
				)
			}
			return nil
		},
	}))

	a.e.Use(middleware.Recover())
}

func (a *App) initLLMGatewayGRPCConn() error {
	grpcConn, err := initGRPCConn(a.cfg.LLMGateway.ServerAddress)
	if err != nil {
		return fmt.Errorf("failed to init gRPC connection to llm gateway: %w", err)
	}

	a.llmGatewayGRPCConn = grpcConn

	return nil
}

func (a *App) initUserServiceGRPCConn() error {
	grpcConn, err := initGRPCConn(a.cfg.UserService.ServerAddress)
	if err != nil {
		return fmt.Errorf("failed to init gRPC connection to user service: %w", err)
	}

	a.userServiceGRPCConn = grpcConn

	return nil
}

func initGRPCConn(addr string) (*grpc.ClientConn, error) {
	grpcConn, err := grpc.NewClient(addr,
		grpc.WithTransportCredentials(
			insecure.NewCredentials(), // TODO: change this to secure creds
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to init gRPC connection: %w", err)
	}
	return grpcConn, nil
}
