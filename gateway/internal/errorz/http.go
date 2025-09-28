package errorz

import "errors"

var (
	InternalServerError = errors.New("internal server error")
	Unauthorized        = errors.New("unauthorized")
	BadRequest          = errors.New("bad request")
)
