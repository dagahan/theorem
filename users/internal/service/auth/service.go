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
	IsExists(ctx context.Context, id uuid.UUID) (bool, error)
}

type tokenService interface {
	CreateAccess(claims *models.AccessToken) (string, error)
	ParseAccess(token string) (*models.AccessToken, error)

	CreateRefresh(claims *models.RefreshToken) (string, error)
	ParseRefresh(token string) (*models.RefreshToken, error)
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
