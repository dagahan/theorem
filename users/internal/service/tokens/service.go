package tokens

import (
	"context"
	"time"
)

type tokenRepo interface {
	InvalidateRefresh(ctx context.Context, token string, ttl time.Duration) error
	IsRefreshInvalidated(ctx context.Context, token string) (bool, error)
}

type Params struct {
	AccessTTL  time.Duration
	RefreshTTL time.Duration
	JWTSecret  []byte
}

type service struct {
	tokenRepo tokenRepo
	params    Params
}

func New(
	tokenRepo tokenRepo,
	params Params,
) *service {
	return &service{
		tokenRepo: tokenRepo,
		params:    params,
	}
}
