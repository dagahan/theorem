package tokens

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/valkey-io/valkey-go"
)

func (r *repo) InvalidateRefresh(ctx context.Context, token string, ttl time.Duration) error {
	return r.client.Do(ctx,
		r.client.B().
			Set().
			Key(fmt.Sprintf(InvalidRefreshTokenKeyTemplate, token)).
			Value("1").
			Ex(ttl).
			Build(),
	).Error()
}

func (r *repo) IsRefreshInvalidated(ctx context.Context, token string) (bool, error) {
	err := r.client.Do(ctx,
		r.client.B().
			Get().
			Key(fmt.Sprintf(InvalidRefreshTokenKeyTemplate, token)).
			Build(),
	).Error()
	if errors.Is(err, valkey.Nil) {
		return false, nil
	} else if err != nil {
		return false, err
	}
	return true, nil
}
