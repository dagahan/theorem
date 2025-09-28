package auth

import (
	"context"
	"errors"
	"log/slog"
	"os"
	"testing"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestService_AuthenticateRequest(t *testing.T) {
	tests := []struct {
		Name             string
		InputAccessToken string
		SessionID        uuid.UUID
		ExpectedResult   *AuthenticateRequestResult
		WantErr          bool
		SetUpMocks       func(
			accessToken string,
			sessionID uuid.UUID,
			userID uuid.UUID,
			tokenService *mocktokenService,
			sessionService *mocksessionService,
		)
	}{
		{
			Name:             "Success",
			InputAccessToken: "test-access-token",
			SessionID:        uuid.New(),
			ExpectedResult: &AuthenticateRequestResult{
				Ok:     true,
				UserID: uuid.New().String(),
			},
			WantErr: false,
			SetUpMocks: func(
				accessToken string,
				sessionID uuid.UUID,
				userID uuid.UUID,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("ParseAccess", accessToken).
					Return(&models.TokenClaims{
						UserID:    userID,
						SessionID: sessionID,
					}, nil).Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(&models.Session{ID: sessionID}, nil).
					Once()
			},
		},
		{
			Name:             "Failed to parse access token",
			InputAccessToken: "test-access-token",
			SessionID:        uuid.New(),
			ExpectedResult:   nil,
			WantErr:          true,
			SetUpMocks: func(
				accessToken string,
				sessionID uuid.UUID,
				userID uuid.UUID,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("ParseAccess", accessToken).
					Return(nil, errors.New("some error")).
					Once()
			},
		},
		{
			Name:             "Session not found",
			InputAccessToken: "test-access-token",
			SessionID:        uuid.New(),
			ExpectedResult:   &AuthenticateRequestResult{Ok: false},
			WantErr:          true,
			SetUpMocks: func(
				accessToken string,
				sessionID uuid.UUID,
				userID uuid.UUID,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("ParseAccess", accessToken).
					Return(&models.TokenClaims{
						UserID:    userID,
						SessionID: sessionID,
					}, nil).Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(nil, errorz.SessionNotFound).
					Once()
			},
		},
		{
			Name:             "Failed to get session",
			InputAccessToken: "test-access-token",
			SessionID:        uuid.New(),
			ExpectedResult:   nil,
			WantErr:          true,
			SetUpMocks: func(
				accessToken string,
				sessionID uuid.UUID,
				userID uuid.UUID,
				tokenService *mocktokenService,
				sessionService *mocksessionService,
			) {
				tokenService.On("ParseAccess", accessToken).
					Return(&models.TokenClaims{
						UserID:    userID,
						SessionID: sessionID,
					}, nil).Once()

				sessionService.On("Get", mock.Anything, sessionID).
					Return(nil, errors.New("some error")).
					Once()
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.Name, func(t *testing.T) {
			mockTokenService := &mocktokenService{}
			mockSessionService := &mocksessionService{}

			userID := uuid.Nil
			if tt.ExpectedResult != nil && tt.ExpectedResult.UserID != "" {
				userID = uuid.MustParse(tt.ExpectedResult.UserID)
			}

			tt.SetUpMocks(
				tt.InputAccessToken,
				tt.SessionID,
				userID,
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

			result, err := svc.AuthenticateRequest(context.Background(), tt.InputAccessToken)
			if tt.WantErr {
				assert.Error(t, err)
			}
			assert.Equal(t, tt.ExpectedResult, result)

			mockTokenService.AssertExpectations(t)
			mockSessionService.AssertExpectations(t)
		})
	}
}
