package users

import (
	"context"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
)

type userRepo interface {
	Create(ctx context.Context, user *models.User) (*models.User, error)
	GetByID(ctx context.Context, id uuid.UUID) (*models.User, error)
}

type hasher interface {
	Hash(password string) (string, error)
	Compare(hash, password string) (bool, error)
}

type service struct {
	userRepo userRepo
	hasher   hasher
}

func New(
	userRepo userRepo,
	hasher hasher,
) *service {
	return &service{
		userRepo: userRepo,
		hasher:   hasher,
	}
}
