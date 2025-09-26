package auth

import (
	"context"
)

func (s *service) Logout(ctx context.Context, accessTokenStr string) error {
	accessToken, err := s.tokenService.ParseAccess(accessTokenStr)
	if err != nil {
		s.l.Warn("failed to logout: parse access token", "error", err)
		return err
	}

	if err := s.sessionService.Delete(ctx, accessToken.SessionID); err != nil {
		s.l.Error("failed to logout: delete session", "error", err)
		return err
	}

	return nil
}
