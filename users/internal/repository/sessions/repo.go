package sessions

import (
	"time"

	"github.com/valkey-io/valkey-go"
)

const (
	SessionKeyTemplate = "session:%s"
)

type repo struct {
	client valkey.Client
	params Params
}

type Params struct {
	InactiveTTL time.Duration
}

func New(client valkey.Client, params Params) *repo {
	return &repo{client: client, params: params}
}
