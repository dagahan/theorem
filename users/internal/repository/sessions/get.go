package sessions

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strconv"
	"time"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
	"github.com/valkey-io/valkey-go"
)

func (r *repo) Get(ctx context.Context, id uuid.UUID) (*models.Session, error) {
	idHash := sha256.Sum256([]byte(id.String()))
	key := fmt.Sprintf(SessionKeyTemplate, hex.EncodeToString(idHash[:]))

	data, err := r.client.Do(ctx,
		r.client.B().
			Hgetall().
			Key(key).
			Build(),
	).AsStrMap()
	if err != nil {
		if valkey.IsValkeyNil(err) {
			return nil, errorz.SessionNotFound
		}
		return nil, fmt.Errorf("failed to execute command: %w", err)
	}

	if len(data) == 0 {
		return nil, errorz.SessionNotFound
	}

	session := &models.Session{
		ID: id,
	}

	userID, err := uuid.Parse(data["user_id"])
	if err != nil {
		return nil, fmt.Errorf("failed to parse user id: %w", err)
	}
	session.UserID = userID

	issuedAtUnix, err := strconv.ParseInt(data["iat"], 10, 64)
	if err != nil {
		return nil, fmt.Errorf("failed to parse iat: %w", err)
	}
	session.IssuedAt = time.Unix(issuedAtUnix, 0)

	maxExpiresAtUnix, err := strconv.ParseInt(data["max_exp_at"], 10, 64)
	if err != nil {
		return nil, fmt.Errorf("failed to parse max_exp_at: %w", err)
	}
	session.MaxExpiresAt = time.Unix(maxExpiresAtUnix, 0)

	return session, nil
}
