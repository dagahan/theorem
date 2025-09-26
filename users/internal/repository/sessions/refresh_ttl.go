package sessions

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"

	"github.com/google/uuid"
)

func (r *repo) RefreshTTL(ctx context.Context, id uuid.UUID) error {
	idHash := sha256.Sum256([]byte(id.String()))
	key := fmt.Sprintf(SessionKeyTemplate, hex.EncodeToString(idHash[:]))
	return r.client.Do(ctx,
		r.client.B().
			Expire().
			Key(key).
			Seconds(int64(r.params.InactiveTTL.Seconds())).
			Build(),
	).Error()
}
