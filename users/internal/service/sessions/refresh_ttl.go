package sessions

import (
	"context"

	"github.com/google/uuid"
)

func (s *service) RefreshTTL(ctx context.Context, id uuid.UUID) error {
	return s.sessionRepo.RefreshTTL(ctx, id)
}
