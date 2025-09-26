package users

import (
	"context"

	"github.com/dagahan/theorem/users/internal/models"
)

func (s *service) GetByEmail(ctx context.Context, email string) (*models.User, error) {
	return s.userRepo.GetByEmail(ctx, email)
}
