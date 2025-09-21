package sessions

import (
	"context"

	"github.com/google/uuid"
)

func (s *service) IsExists(ctx context.Context, id uuid.UUID) (bool, error) {
	return s.sessionRepo.IsExists(ctx, id)
}
