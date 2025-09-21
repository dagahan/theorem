package auth

import "context"

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

	ok, err := s.sessionService.IsExists(ctx, token.SessionID)
	if err != nil {
		s.l.Error("failed to authenticate request: check session", "error", err)
		return nil, err
	}
	if !ok {
		s.l.Warn("failed to authenticate request: session not found")
		return &AuthenticateRequestResult{Ok: false}, nil
	}

	return &AuthenticateRequestResult{
		Ok:     true,
		UserID: token.UserID.String(),
	}, nil
}
