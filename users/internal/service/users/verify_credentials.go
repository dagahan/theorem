package users

import (
	"context"
	"fmt"

	"github.com/dagahan/theorem/users/internal/models"
)

func (s *service) VerifyCredentials(ctx context.Context, inputUser *models.User) (bool, error) {
	user, err := s.userRepo.GetByID(ctx, inputUser.ID)
	if err != nil {
		return false, fmt.Errorf("failed to find user: %w", err)
	}

	ok, err := s.hasher.Compare(user.HashedPassword, inputUser.Password)
	if err != nil {
		return false, fmt.Errorf("failed to compare password: %w", err)
	}
	if !ok {
		return false, nil
	}

	return true, nil
}
