package errorz

import "errors"

var (
	TokenNotFound = errors.New("token not found")
	InvalidToken  = errors.New("invalid token")
)
