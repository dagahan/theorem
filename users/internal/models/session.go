package models

import (
	"time"

	"github.com/google/uuid"
)

type Session struct {
	ID           uuid.UUID
	UserID       uuid.UUID
	IssuedAt     time.Time
	MaxExpiresAt time.Time
}
