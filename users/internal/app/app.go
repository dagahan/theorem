package app

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log/slog"
	"net"

	"entgo.io/ent/dialect"
	entsql "entgo.io/ent/dialect/sql"
	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/dagahan/theorem/users/internal/config"
	"github.com/dagahan/theorem/users/internal/db/ent"
	sessionrepo "github.com/dagahan/theorem/users/internal/repository/sessions"
	tokenrepo "github.com/dagahan/theorem/users/internal/repository/tokens"
	userrepo "github.com/dagahan/theorem/users/internal/repository/users"
	authservice "github.com/dagahan/theorem/users/internal/service/auth"
	sessionservice "github.com/dagahan/theorem/users/internal/service/sessions"
	tokenservice "github.com/dagahan/theorem/users/internal/service/tokens"
	userservice "github.com/dagahan/theorem/users/internal/service/users"
	authhandler "github.com/dagahan/theorem/users/internal/transport/grpc/auth"
	"github.com/dagahan/theorem/users/pkg/crypto"
	"github.com/grpc-ecosystem/go-grpc-middleware/v2/interceptors/logging"
	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/valkey-io/valkey-go"
	"google.golang.org/grpc"
)

type App struct {
	cfg          *config.Config
	l            *slog.Logger
	lis          *net.Listener
	entClient    *ent.Client
	grpcSrv      *grpc.Server
	valkeyClient valkey.Client
}

// InterceptorLogger adapts slog logger to interceptor logger.
func InterceptorLogger(l *slog.Logger) logging.Logger {
	return logging.LoggerFunc(func(ctx context.Context, lvl logging.Level, msg string, fields ...any) {
		l.Log(ctx, slog.Level(lvl), msg, fields...)
	})
}

// New creates and initializes a new instance of App
func New(ctx context.Context, cfg *config.Config, l *slog.Logger) (*App, error) {
	a := &App{
		cfg: cfg,
		l:   l,
	}

	if err := a.initListener(); err != nil {
		return nil, err
	}

	if err := a.initDB(); err != nil {
		return nil, err
	}

	if err := a.initValkey(); err != nil {
		return nil, err
	}

	if err := a.migrateDB(ctx); err != nil {
		return nil, err
	}

	a.initGRPCServer()

	sessionRepo := sessionrepo.New(a.valkeyClient)
	tokenRepo := tokenrepo.New(a.valkeyClient)
	userRepo := userrepo.NewUserRepo(a.entClient)

	hasher := crypto.NewHasher(a.cfg.Hasher.Cost)

	sessionService := sessionservice.New(
		sessionRepo,
		sessionservice.Params{
			MaxTTL:      a.cfg.Session.MaxTTL,
			InactiveTTL: a.cfg.Session.InactiveTTL,
		},
	)
	tokenService := tokenservice.New(
		tokenRepo,
		tokenservice.Params{
			AccessTTL:  a.cfg.Token.AccessTTL,
			RefreshTTL: a.cfg.Token.RefreshTTL,
			JWTSecret:  []byte(a.cfg.Token.JWTSecret),
		},
	)
	userService := userservice.New(
		userRepo,
		hasher,
	)
	authService := authservice.New(
		a.l,
		userService,
		sessionService,
		tokenService,
	)

	authHandler := authhandler.New(authService)
	pb.RegisterAuthServiceServer(a.grpcSrv, authHandler)

	return a, nil
}

// Start performs a start of all functional services
func (a *App) Start(errChan chan<- error) {
	a.l.Info("starting server",
		"addr", a.cfg.Server.Addr,
	)
	if err := a.grpcSrv.Serve(*a.lis); err != nil {
		errChan <- err
	}
}

// Stop performs a graceful shutdown for all components
func (a *App) Stop(ctx context.Context) error {
	a.l.Info("[!] Shutting down...")

	var stopErr error

	a.l.Info("Stopping gRPC server...")
	a.grpcSrv.GracefulStop()

	a.l.Info("Closing database client...")
	if err := a.entClient.Close(); err != nil {
		stopErr = errors.Join(stopErr, fmt.Errorf("failed to close ent client: %w", err))
	}

	a.l.Info("Closing Valkey connection...")
	a.valkeyClient.Close()

	if stopErr != nil {
		return stopErr
	}

	a.l.Info("Stopped gracefully!")
	return nil
}

// initDB sets up PostgreSQL db
func (a *App) initDB() error {
	db, err := sql.Open("pgx", a.cfg.Postgres.URL)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}

	drv := entsql.OpenDB(dialect.Postgres, db)
	a.entClient = ent.NewClient(ent.Driver(drv))

	return nil
}

// initListener sets up a tcp listener ready for gRPC
func (a *App) initListener() error {
	lis, err := net.Listen("tcp", a.cfg.Server.Addr)
	if err != nil {
		return fmt.Errorf("failed to listen: %w", err)
	}
	a.lis = &lis
	return nil
}

// migrateDB performs a migration to ensure the schema is up to date
func (a *App) migrateDB(ctx context.Context) error {
	return a.entClient.Schema.Create(ctx)
}

// initValkey sets up a connection to cache
func (a *App) initValkey() error {
	client, err := valkey.NewClient(valkey.ClientOption{
		InitAddress: []string{a.cfg.Valkey.Addr},
		Password:    a.cfg.Valkey.Password,
	})
	if err != nil {
		return fmt.Errorf("failed to init Valkey connection: %w", err)
	}
	a.valkeyClient = client
	return nil
}

// initGRPCServer sets up a gRPC server with interceptor logger
func (a *App) initGRPCServer() {
	opts := []logging.Option{
		logging.WithLogOnEvents(logging.StartCall, logging.FinishCall),
	}

	a.grpcSrv = grpc.NewServer(
		grpc.ChainUnaryInterceptor(
			logging.UnaryServerInterceptor(InterceptorLogger(a.l), opts...),
		),
	)
}
