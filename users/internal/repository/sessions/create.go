package sessions

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strconv"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/valkey-io/valkey-go"
)

func (r *repo) Create(ctx context.Context, session *models.Session) error {
	idHash := sha256.Sum256([]byte(session.ID.String()))
	key := fmt.Sprintf(SessionKeyTemplate, hex.EncodeToString(idHash[:]))

	return r.client.Dedicated(func(c valkey.DedicatedClient) error {
		cmdCreate := c.B().
			Hset().Key(key).FieldValue().
			FieldValue("user_id", session.UserID.String()).
			FieldValue("iat", strconv.FormatInt(session.IssuedAt.Unix(), 10)).
			FieldValue("mtl", strconv.FormatInt(session.IssuedAt.Add(session.MaxTTL).Unix(), 10)).
			Build()

		cmdExp := c.B().
			Expire().
			Key(key).
			Seconds(int64(session.InactiveTTL.Seconds())).
			Build()

		for _, resp := range c.DoMulti(ctx,
			c.B().Multi().Build(),
			cmdCreate, cmdExp,
			c.B().Exec().Build(),
		) {
			if resp.Error() != nil {
				return fmt.Errorf("failed to execute command: %w", resp.Error())
			}
		}

		return nil
	})
}
