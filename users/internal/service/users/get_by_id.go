package users

import (
	"context"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
)

func (s *service) GetByID(ctx context.Context, userID uuid.UUID) (*models.User, error) {
	return s.userRepo.GetByID(ctx, userID)
}
