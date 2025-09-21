package users

import (
	"context"
	"fmt"

	"github.com/dagahan/theorem/users/internal/models"
)

func (s *service) Create(ctx context.Context, user *models.User) (*models.User, error) {
	hashedPassword, err := s.hasher.Hash(user.Password)
	if err != nil {
		return nil, fmt.Errorf("failed to hash password: %w", err)
	}
	user.HashedPassword = hashedPassword

	user, err = s.userRepo.Create(ctx, user)
	if err != nil {
		return nil, fmt.Errorf("failed to create user: %w", err)
	}

	return user, nil
}
