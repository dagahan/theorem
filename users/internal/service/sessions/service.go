package sessions

import (
	"context"
	"time"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
)

type sessionRepo interface {
	Create(ctx context.Context, session *models.Session) error
	IsExists(ctx context.Context, id uuid.UUID) (bool, error)
}

type Params struct {
	MaxTTL      time.Duration
	InactiveTTL time.Duration
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
