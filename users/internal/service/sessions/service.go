package sessions

import (
	"context"
	"time"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
)

type sessionRepo interface {
	Create(ctx context.Context, session *models.Session) error
	Get(ctx context.Context, id uuid.UUID) (*models.Session, error)
	RefreshTTL(ctx context.Context, id uuid.UUID) error
	Delete(ctx context.Context, id uuid.UUID) error
}

type Params struct {
	MaxTTL time.Duration
}

type service struct {
	sessionRepo sessionRepo
	params      Params
}

func New(
	sessionRepo sessionRepo,
	params Params,
) *service {
	return &service{
		sessionRepo: sessionRepo,
		params:      params,
	}
}
