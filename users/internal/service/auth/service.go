package auth

import (
	"context"
	"log/slog"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
)

type userService interface {
	Create(ctx context.Context, user *models.User) (*models.User, error)
	GetByID(ctx context.Context, userID uuid.UUID) (*models.User, error)
	GetByEmail(ctx context.Context, email string) (*models.User, error)
	VerifyCredentials(ctx context.Context, inputUser *models.User) (bool, error)
}

type sessionService interface {
	Create(ctx context.Context, userID uuid.UUID) (*models.Session, error)
	Get(ctx context.Context, id uuid.UUID) (*models.Session, error)
	RefreshTTL(ctx context.Context, id uuid.UUID) error
	Delete(ctx context.Context, id uuid.UUID) error
}

type tokenService interface {
	CreateAccess(claims *models.TokenClaims) (string, error)
	ParseAccess(token string) (*models.TokenClaims, error)

	CreateRefresh(claims *models.TokenClaims) (string, error)
	ParseRefresh(token string) (*models.TokenClaims, error)
	InvalidateRefresh(ctx context.Context, tokenStr string) error
	IsRefreshInvalidated(ctx context.Context, token string) (bool, error)
}

type service struct {
	l              *slog.Logger
	userService    userService
	sessionService sessionService
	tokenService   tokenService
}

func New(
	l *slog.Logger,
	userService userService,
	sessionService sessionService,
	tokenService tokenService,
) *service {
	return &service{
		l:              l,
		userService:    userService,
		sessionService: sessionService,
		tokenService:   tokenService,
	}
}
