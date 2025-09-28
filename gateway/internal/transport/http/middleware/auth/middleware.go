package auth

import (
	"context"

	"github.com/google/uuid"
)

type authService interface {
	AuthenticateRequest(ctx context.Context, accessToken string) (uuid.UUID, error)
}

type middleware struct {
	authService authService
}

func New(authService authService) *middleware {
	return &middleware{
		authService: authService,
	}
}
