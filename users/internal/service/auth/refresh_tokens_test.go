package auth

import (
	"context"
	"errors"
	"log/slog"
	"os"
	"testing"
	"time"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestService_RefreshTokens(t *testing.T) {
	tests := []struct {
		Name              string
		InputRefreshToken string
		ExpectedResult    *RefreshTokensResult
		WantErr           bool
		SetUpMocks        func(
			refreshTokenStr string,
			userID uuid.UUID,
			sessionID uuid.UUID,
			newAccessTokenStr string,
			newRefreshTokenStr string,
			tokenService *mocktokenService,
			sessionService *mocksessionService,
		)
	}{
		{
			Name:              "Success",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult: &RefreshTokensResult{
				AccessToken:  "test-access-token",
				RefreshToken: "test-refresh-token",
			},
			WantErr: false,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						UserID:    userID,
						SessionID: sessionID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(&models.Session{
						ID:           sessionID,
						UserID:       userID,
						MaxExpiresAt: time.Now().Add(30 * 24 * time.Hour),
					}, nil).
					Once()

				sessionService.On("RefreshTTL", mock.Anything, sessionID).
					Return(nil).
					Once()

				tokenService.On("InvalidateRefresh", mock.Anything, refreshTokenStr).
					Return(nil).
					Once()

				tokenService.On("CreateAccess", &models.TokenClaims{
					UserID:    userID,
					SessionID: sessionID,
				}).
					Return(newAccessTokenStr, nil).
					Once()

				tokenService.On("CreateRefresh", &models.TokenClaims{
					UserID:    userID,
					SessionID: sessionID,
				}).
					Return(newRefreshTokenStr, nil).
					Once()
			},
		},
		{
			Name:              "Refresh token is invalidated",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(true, nil).
					Once()
			},
		},
		{
			Name:              "Failed to check if refresh token is invalidated",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, errors.New("some error")).
					Once()
			},
		},
		{
			Name:              "Failed to parse refresh token",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(nil, errors.New("some error")).
					Once()
			},
		},
		{
			Name:              "Session not found",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						SessionID: sessionID,
						UserID:    userID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(nil, errorz.SessionNotFound).
					Once()
			},
		},
		{
			Name:              "Session expired",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						SessionID: sessionID,
						UserID:    userID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(&models.Session{
						ID:           sessionID,
						UserID:       userID,
						MaxExpiresAt: time.Now().Add(-24 * time.Hour),
					}, nil).
					Once()
			},
		},
		{
			Name:              "Failed to get session",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						SessionID: sessionID,
						UserID:    userID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(nil, errors.New("some error")).
					Once()
			},
		},
		{
			Name:              "Failed to refresh ttl of session",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						SessionID: sessionID,
						UserID:    userID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(&models.Session{
						ID:           sessionID,
						UserID:       userID,
						MaxExpiresAt: time.Now().Add(30 * 24 * time.Hour),
					}, nil).
					Once()

				sessionService.On("RefreshTTL", mock.Anything, sessionID).
					Return(errors.New("some error")).
					Once()
			},
		},
		{
			Name:              "Failed to invalidate refresh token",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						SessionID: sessionID,
						UserID:    userID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(&models.Session{
						ID:           sessionID,
						UserID:       userID,
						MaxExpiresAt: time.Now().Add(30 * 24 * time.Hour),
					}, nil).
					Once()

				sessionService.On("RefreshTTL", mock.Anything, sessionID).
					Return(nil).
					Once()

				tokenService.On("InvalidateRefresh", mock.Anything, refreshTokenStr).
					Return(errors.New("some error")).
					Once()
			},
		},
		{
			Name:              "Failed to create access token",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						SessionID: sessionID,
						UserID:    userID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(&models.Session{
						ID:           sessionID,
						UserID:       userID,
						MaxExpiresAt: time.Now().Add(30 * 24 * time.Hour),
					}, nil).
					Once()

				sessionService.On("RefreshTTL", mock.Anything, sessionID).
					Return(nil).
					Once()

				tokenService.On("InvalidateRefresh", mock.Anything, refreshTokenStr).
					Return(nil).
					Once()

				tokenService.On("CreateAccess", &models.TokenClaims{
					UserID:    userID,
					SessionID: sessionID,
				}).
					Return("", errors.New("some error")).
					Once()
			},
		},
		{
			Name:              "Failed to create refresh token",
			InputRefreshToken: "test-refresh-token",
			ExpectedResult:    nil,
			WantErr:           true,
			SetUpMocks: func(
				refreshTokenStr string,
				userID uuid.UUID,
				sessionID uuid.UUID,
				newAccessTokenStr string,
				newRefreshTokenStr string,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("IsRefreshInvalidated", mock.Anything, refreshTokenStr).
					Return(false, nil).
					Once()

				tokenService.On("ParseRefresh", refreshTokenStr).
					Return(&models.TokenClaims{
						SessionID: sessionID,
						UserID:    userID,
					}, nil).
					Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(&models.Session{
						ID:           sessionID,
						UserID:       userID,
						MaxExpiresAt: time.Now().Add(30 * 24 * time.Hour),
					}, nil).
					Once()

				sessionService.On("RefreshTTL", mock.Anything, sessionID).
					Return(nil).
					Once()

				tokenService.On("InvalidateRefresh", mock.Anything, refreshTokenStr).
					Return(nil).
					Once()

				tokenService.On("CreateAccess", &models.TokenClaims{
					UserID:    userID,
					SessionID: sessionID,
				}).
					Return(newAccessTokenStr, nil).
					Once()

				tokenService.On("CreateRefresh", &models.TokenClaims{
					UserID:    userID,
					SessionID: sessionID,
				}).
					Return("", errors.New("some error")).
					Once()
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.Name, func(t *testing.T) {
			mockTokenService := &mocktokenService{}
			mockSessionService := &mocksessionService{}

			var newAccessToken, newRefreshToken string
			if tt.ExpectedResult != nil {
				newAccessToken = tt.ExpectedResult.AccessToken
				newRefreshToken = tt.ExpectedResult.RefreshToken
			}

			userID := uuid.New()
			sessionID := uuid.New()

			tt.SetUpMocks(
				tt.InputRefreshToken,
				userID,
				sessionID,
				newAccessToken,
				newRefreshToken,
				mockTokenService,
				mockSessionService,
			)

			svc := New(
				slog.New(
					slog.NewTextHandler(
						os.Stdout,
						&slog.HandlerOptions{},
					),
				),
				nil,
				mockSessionService,
				mockTokenService,
			)

			result, err := svc.RefreshTokens(context.Background(), tt.InputRefreshToken)
			if tt.WantErr {
				assert.Error(t, err)
			}
			assert.Equal(t, tt.ExpectedResult, result)

			mockTokenService.AssertExpectations(t)
			mockSessionService.AssertExpectations(t)
		})
	}
}
