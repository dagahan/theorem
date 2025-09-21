package sessions

import "github.com/valkey-io/valkey-go"

const (
	SessionKeyTemplate = "session:%s"
)

type repo struct {
	client valkey.Client
}

func New(client valkey.Client) *repo {
	return &repo{client: client}
}
