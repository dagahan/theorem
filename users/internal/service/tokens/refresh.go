package tokens

import (
	"context"
	"fmt"
	"time"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/golang-jwt/jwt/v5"
)

// CreateRefresh creates refresh token and returns its string representation (JWT)
func (s *service) CreateRefresh(claims *models.RefreshToken) (string, error) {
	claims.IssuedAt = jwt.NewNumericDate(time.Now())
	claims.ExpiresAt = jwt.NewNumericDate(claims.IssuedAt.Add(s.params.RefreshTTL))

	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString(s.params.JWTSecret)
	if err != nil {
		return "", fmt.Errorf("failed to create refresh token: %w", err)
	}
	return token, nil
}

func (s *service) ParseRefresh(token string) (*models.RefreshToken, error) {
	claims := &models.RefreshToken{}
	_, err := jwt.ParseWithClaims(token, claims, func(token *jwt.Token) (interface{}, error) {
		return s.params.JWTSecret, nil
	})
	if err != nil {
		return nil, errorz.InvalidToken
	}

	return claims, nil
}

func (s *service) InvalidateRefresh(ctx context.Context, tokenStr string) error {
	token, err := s.ParseRefresh(tokenStr)
	if err != nil {
		return err
	}

	return s.tokenRepo.InvalidateRefresh(ctx, tokenStr, token.ExpiresAt.Sub(time.Now()))
}

func (s *service) IsRefreshInvalidated(ctx context.Context, token string) (bool, error) {
	return s.tokenRepo.IsRefreshInvalidated(ctx, token)
}
