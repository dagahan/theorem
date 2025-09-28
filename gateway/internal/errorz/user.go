package errorz

import "errors"

var (
	UserAlreadyExists  = errors.New("user already exists")
	InvalidCredentials = errors.New("invalid credentials")
)
