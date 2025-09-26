package auth

import (
	"context"

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

	ok, err = s.sessionService.IsExists(ctx, oldRefreshToken.SessionID)
	if err != nil {
		s.l.Error("failed to refresh tokens: check session", "error", err)
		return nil, err
	}
	if !ok {
		s.l.Warn("failed to refresh tokens: session not found")
		return nil, errorz.SessionNotFound
	}

	// TODO: update session ttl

	err = s.tokenService.InvalidateRefresh(ctx, oldRefreshTokenStr)
	if err != nil {
		s.l.Error("failed to refresh tokens: invalidate old refresh token", "error", err)
		return nil, err
	}

	accessToken, err := s.tokenService.CreateAccess(
		&models.AccessToken{
			UserID:    oldRefreshToken.UserID,
			SessionID: oldRefreshToken.SessionID,
		},
	)
	if err != nil {
		s.l.Error("failed to refresh tokens: create access token", "error", err)
		return nil, err
	}

	refreshToken, err := s.tokenService.CreateRefresh(
		&models.RefreshToken{
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
