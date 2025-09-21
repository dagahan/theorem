package sessions

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/valkey-io/valkey-go"
)

func (r *repo) IsExists(ctx context.Context, id uuid.UUID) (bool, error) {
	idHash := sha256.Sum256([]byte(id.String()))
	key := fmt.Sprintf(SessionKeyTemplate, hex.EncodeToString(idHash[:]))

	sessionExp, err := r.client.Do(ctx,
		r.client.B().
			Hget().
			Key(key).
			Field("mtl").
			Build(),
	).AsInt64()
	if err != nil {
		if valkey.IsValkeyNil(err) {
			return false, nil
		}
		return false, fmt.Errorf("failed to execute command: %w", err)
	}

	currentTime := time.Now().Unix()

	if sessionExp < currentTime {
		return false, nil
	}

	return true, nil
}
