package auth

import (
	"context"
	"errors"
	"time"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
)

type RefreshTokensResult struct {
	AccessToken  string
	RefreshToken string
}

func (s *service) RefreshTokens(ctx context.Context, oldRefreshTokenStr string) (*RefreshTokensResult, error) {
	ok, err := s.tokenService.IsRefreshInvalidated(ctx, oldRefreshTokenStr)
	if err != nil {
		s.l.Error("failed to refresh tokens: IsRefreshInvalidated", "error", err)
		return nil, err
	}
	if ok {
		return nil, errorz.InvalidToken
	}

	oldRefreshToken, err := s.tokenService.ParseRefresh(oldRefreshTokenStr)
	if err != nil {
		s.l.Warn("failed to refresh tokens: parse old refresh token", "error", err)
		return nil, errorz.InvalidToken
	}

	session, err := s.sessionService.Get(ctx, oldRefreshToken.SessionID)
	switch {
	case errors.Is(err, errorz.SessionNotFound):
		s.l.Warn("failed to refresh tokens: session not found", "session_id", oldRefreshToken.SessionID)
		return nil, errorz.SessionNotFound
	case err != nil:
		s.l.Error("failed to refresh tokens: get session", "error", err)
		return nil, err
	}
	if time.Now().After(session.MaxExpiresAt) {
		s.l.Warn("failed to refresh tokens: session expired", "session_id", oldRefreshToken.SessionID)
		return nil, errorz.SessionNotFound
	}

	err = s.sessionService.RefreshTTL(ctx, session.ID)
	if err != nil {
		s.l.Error("failed to refresh tokens: refresh ttl", "error", err)
		return nil, err
	}

	err = s.tokenService.InvalidateRefresh(ctx, oldRefreshTokenStr)
	if err != nil {
		s.l.Error("failed to refresh tokens: invalidate old refresh token", "error", err)
		return nil, err
	}

	accessToken, err := s.tokenService.CreateAccess(
		&models.TokenClaims{
			UserID:    oldRefreshToken.UserID,
			SessionID: oldRefreshToken.SessionID,
		},
	)
	if err != nil {
		s.l.Error("failed to refresh tokens: create access token", "error", err)
		return nil, err
	}

	refreshToken, err := s.tokenService.CreateRefresh(
		&models.TokenClaims{
			UserID:    oldRefreshToken.UserID,
			SessionID: oldRefreshToken.SessionID,
		},
	)
	if err != nil {
		s.l.Error("failed to refresh tokens: create refresh token", "error", err)
		return nil, err
	}

	return &RefreshTokensResult{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
	}, nil
}
