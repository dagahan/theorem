package auth

import (
	"context"
	"errors"

	"github.com/dagahan/theorem/users/internal/errorz"
)

type AuthenticateRequestResult struct {
	Ok     bool
	UserID string
}

func (s *service) AuthenticateRequest(ctx context.Context, accessTokenStr string) (*AuthenticateRequestResult, error) {
	token, err := s.tokenService.ParseAccess(accessTokenStr)
	if err != nil {
		s.l.Warn("failed to authenticate request: parse access token", "error", err)
		return nil, err
	}

	_, err = s.sessionService.Get(ctx, token.SessionID)
	switch {
	case errors.Is(err, errorz.SessionNotFound):
		s.l.Warn("failed to authenticate request: session not found")
		return &AuthenticateRequestResult{Ok: false}, err
	case err != nil:
		s.l.Error("failed to authenticate request: get session", "error", err)
		return nil, err
	}

	return &AuthenticateRequestResult{
		Ok:     true,
		UserID: token.UserID.String(),
	}, nil
}
