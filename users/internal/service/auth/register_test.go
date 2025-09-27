package auth

import (
	"context"
	"errors"
	"log/slog"
	"os"
	"testing"
	"time"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestService_Register(t *testing.T) {
	tests := []struct {
		Name           string
		InputUser      *models.User
		ExpectedResult *RegisterResult
		WantErr        bool
		SetUpMocks     func(
			inputUser *models.User,
			result *RegisterResult,
			userService *mockuserService,
			sessionService *mocksessionService,
			tokenService *mocktokenService,
		)
	}{
		{
			Name: "Success",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExpectedResult: &RegisterResult{
				User: &models.User{
					ID:    uuid.New(),
					Email: "some@test.com",
				},
				AccessToken:  "abracadabra",
				RefreshToken: "abracadabracadabra",
			},
			WantErr: false,
			SetUpMocks: func(
				inputUser *models.User,
				result *RegisterResult,
				userService *mockuserService,
				sessionService *mocksessionService,
				tokenService *mocktokenService,
			) {
				userService.On("Create", mock.Anything, inputUser).
					Return(result.User, nil).
					Once()

				session := &models.Session{
					ID:           uuid.New(),
					UserID:       result.User.ID,
					IssuedAt:     time.Now(),
					MaxExpiresAt: time.Now().Add(time.Hour),
				}
				sessionService.On("Create", mock.Anything, result.User.ID).
					Return(session, nil).
					Once()

				tokenService.On("CreateAccess", &models.TokenClaims{
					UserID:    result.User.ID,
					SessionID: session.ID,
				}).
					Return(result.AccessToken, nil).
					Once()

				tokenService.On("CreateRefresh", &models.TokenClaims{
					UserID:    result.User.ID,
					SessionID: session.ID,
				}).
					Return(result.RefreshToken, nil).
					Once()
			},
		},
		{
			Name: "Failed to create user",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExpectedResult: nil,
			WantErr:        true,
			SetUpMocks: func(
				inputUser *models.User,
				result *RegisterResult,
				userService *mockuserService,
				sessionService *mocksessionService,
				tokenService *mocktokenService,
			) {
				userService.On("Create", mock.Anything, inputUser).
					Return(nil, errors.New("some error")).
					Once()
			},
		},
		{
			Name: "Failed to create session",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExpectedResult: nil,
			WantErr:        true,
			SetUpMocks: func(
				inputUser *models.User,
				result *RegisterResult,
				userService *mockuserService,
				sessionService *mocksessionService,
				tokenService *mocktokenService,
			) {
				user := &models.User{
					ID:    uuid.New(),
					Email: inputUser.Email,
				}
				userService.On("Create", mock.Anything, inputUser).
					Return(user, nil).
					Once()

				sessionService.On("Create", mock.Anything, user.ID).
					Return(nil, errors.New("some error")).
					Once()
			},
		},
		{
			Name: "Failed to create access token",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExpectedResult: nil,
			WantErr:        true,
			SetUpMocks: func(
				inputUser *models.User,
				result *RegisterResult,
				userService *mockuserService,
				sessionService *mocksessionService,
				tokenService *mocktokenService,
			) {
				user := &models.User{
					ID:    uuid.New(),
					Email: inputUser.Email,
				}
				userService.On("Create", mock.Anything, inputUser).
					Return(user, nil).
					Once()

				session := &models.Session{
					ID:           uuid.New(),
					UserID:       user.ID,
					IssuedAt:     time.Now(),
					MaxExpiresAt: time.Now().Add(time.Hour),
				}
				sessionService.On("Create", mock.Anything, user.ID).
					Return(session, nil).
					Once()

				tokenService.On("CreateAccess", &models.TokenClaims{
					UserID:    user.ID,
					SessionID: session.ID,
				}).
					Return("", errors.New("some error")).
					Once()
			},
		},
		{

			Name: "Failed to create refresh token",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExpectedResult: nil,
			WantErr:        true,
			SetUpMocks: func(
				inputUser *models.User,
				result *RegisterResult,
				userService *mockuserService,
				sessionService *mocksessionService,
				tokenService *mocktokenService,
			) {
				user := &models.User{
					ID:    uuid.New(),
					Email: inputUser.Email,
				}
				userService.On("Create", mock.Anything, inputUser).
					Return(user, nil).
					Once()

				session := &models.Session{
					ID:           uuid.New(),
					UserID:       user.ID,
					IssuedAt:     time.Now(),
					MaxExpiresAt: time.Now().Add(time.Hour),
				}
				sessionService.On("Create", mock.Anything, user.ID).
					Return(session, nil).
					Once()

				tokenService.On("CreateAccess", &models.TokenClaims{
					UserID:    user.ID,
					SessionID: session.ID,
				}).
					Return("blahblahblah", nil).
					Once()

				tokenService.On("CreateRefresh", &models.TokenClaims{
					UserID:    user.ID,
					SessionID: session.ID,
				}).
					Return("", errors.New("some error")).
					Once()
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.Name, func(t *testing.T) {
			mockUserService := &mockuserService{}
			mockSessionService := &mocksessionService{}
			mockTokenService := &mocktokenService{}

			tt.SetUpMocks(
				tt.InputUser,
				tt.ExpectedResult,
				mockUserService,
				mockSessionService,
				mockTokenService,
			)

			svc := New(
				slog.New(
					slog.NewTextHandler(
						os.Stdout,
						&slog.HandlerOptions{},
					),
				),
				mockUserService,
				mockSessionService,
				mockTokenService,
			)

			res, err := svc.Register(context.Background(), tt.InputUser)
			if tt.WantErr {
				assert.Error(t, err)
			}
			assert.Equal(t, tt.ExpectedResult, res)

			mockUserService.AssertExpectations(t)
			mockSessionService.AssertExpectations(t)
			mockTokenService.AssertExpectations(t)
		})
	}
}
