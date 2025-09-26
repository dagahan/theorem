package sessions

import (
	"context"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
)

func (s *service) Get(ctx context.Context, id uuid.UUID) (*models.Session, error) {
	return s.sessionRepo.Get(ctx, id)
}
