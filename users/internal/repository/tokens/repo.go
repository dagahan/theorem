package tokens

import (
	"github.com/valkey-io/valkey-go"
)

const (
	InvalidRefreshTokenKeyTemplate = "invalid_refresh_token:%s"
)

type repo struct {
	client valkey.Client
}

func New(client valkey.Client) *repo {
	return &repo{client: client}
}
