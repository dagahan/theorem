package jwt

import (
	"errors"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// Claims представляет JWT claims
type Claims struct {
	UserID    uint   `json:"sub"`
	SessionID string `json:"sid"`
	Role      string `json:"role"`
	Type      string `json:"type"` // "access" или "refresh"
	jwt.RegisteredClaims
}

// JWTManager управляет JWT токенами
type JWTManager struct {
	secret                string
	accessTokenExpire     time.Duration
	refreshTokenExpire    time.Duration
}

// NewJWTManager создает новый JWT менеджер
func NewJWTManager(secret string, accessExpire, refreshExpire time.Duration) *JWTManager {
	return &JWTManager{
		secret:             secret,
		accessTokenExpire:  accessExpire,
		refreshTokenExpire: refreshExpire,
	}
}

// GenerateAccessToken генерирует access токен
func (j *JWTManager) GenerateAccessToken(userID uint, sessionID, role string) (string, error) {
	claims := &Claims{
		UserID:    userID,
		SessionID: sessionID,
		Role:      role,
		Type:      "access",
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(j.accessTokenExpire)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			NotBefore: jwt.NewNumericDate(time.Now()),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(j.secret))
}

// GenerateRefreshToken генерирует refresh токен
func (j *JWTManager) GenerateRefreshToken(userID uint, sessionID, role string) (string, error) {
	claims := &Claims{
		UserID:    userID,
		SessionID: sessionID,
		Role:      role,
		Type:      "refresh",
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(j.refreshTokenExpire)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			NotBefore: jwt.NewNumericDate(time.Now()),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(j.secret))
}

// ValidateToken валидирует JWT токен
func (j *JWTManager) ValidateToken(tokenString string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return []byte(j.secret), nil
	})

	if err != nil {
		return nil, err
	}

	if claims, ok := token.Claims.(*Claims); ok && token.Valid {
		return claims, nil
	}

	return nil, errors.New("invalid token")
}

// ExtractTokenFromHeader извлекает токен из заголовка Authorization
func ExtractTokenFromHeader(authHeader string) (string, error) {
	if authHeader == "" {
		return "", errors.New("authorization header is required")
	}

	const bearerPrefix = "Bearer "
	if len(authHeader) < len(bearerPrefix) || authHeader[:len(bearerPrefix)] != bearerPrefix {
		return "", errors.New("authorization header must start with 'Bearer '")
	}

	return authHeader[len(bearerPrefix):], nil
}