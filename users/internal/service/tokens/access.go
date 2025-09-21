package tokens

import (
	"fmt"
	"time"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/golang-jwt/jwt/v5"
)

// CreateAccess creates access token and returns its string representation (JWT)
func (s *service) CreateAccess(claims *models.AccessToken) (string, error) {
	claims.IssuedAt = jwt.NewNumericDate(time.Now())
	claims.ExpiresAt = jwt.NewNumericDate(claims.IssuedAt.Add(s.params.AccessTTL))

	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString(s.params.JWTSecret)
	if err != nil {
		return "", fmt.Errorf("failed to create access token: %w", err)
	}
	return token, nil
}

func (s *service) ParseAccess(token string) (*models.AccessToken, error) {
	claims := &models.AccessToken{}
	_, err := jwt.ParseWithClaims(token, claims, func(token *jwt.Token) (interface{}, error) {
		return s.params.JWTSecret, nil
	})
	if err != nil {
		return nil, errorz.InvalidToken
	}

	return claims, nil
}
