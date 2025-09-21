package errorz

import "errors"

var (
	UserAlreadyExists  = errors.New("user already exists")
	UserNotFound       = errors.New("user not found")
	EmailAlreadyInUse  = errors.New("email already in use")
	InvalidCredentials = errors.New("invalid credentials")
)
