package tokens

import (
	"fmt"
	"time"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/golang-jwt/jwt/v5"
)

// CreateAccess creates access token and returns its string representation (JWT)
func (s *service) CreateAccess(claims *models.TokenClaims) (string, error) {
	claims.IssuedAt = jwt.NewNumericDate(time.Now())
	claims.ExpiresAt = jwt.NewNumericDate(claims.IssuedAt.Add(s.params.AccessTTL))
	claims.Type = "access"

	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString(s.params.JWTSecret)
	if err != nil {
		return "", fmt.Errorf("failed to create access token: %w", err)
	}
	return token, nil
}

func (s *service) ParseAccess(token string) (*models.TokenClaims, error) {
	claims := &models.TokenClaims{}
	_, err := jwt.ParseWithClaims(token, claims, func(token *jwt.Token) (interface{}, error) {
		return s.params.JWTSecret, nil
	})
	if err != nil || claims.Type != "access" {
		return nil, errorz.InvalidToken
	}

	return claims, nil
}
