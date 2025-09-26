package sessions

import (
	"context"
	"fmt"
	"time"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
)

func (s *service) Create(ctx context.Context, userID uuid.UUID) (*models.Session, error) {
	now := time.Now()
	session := &models.Session{
		ID:           uuid.New(),
		UserID:       userID,
		IssuedAt:     now,
		MaxExpiresAt: now.Add(s.params.MaxTTL),
	}

	err := s.sessionRepo.Create(ctx, session)
	if err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	return session, nil
}
