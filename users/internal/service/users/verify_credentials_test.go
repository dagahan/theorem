package users

import (
	"context"
	"errors"
	"testing"

	"github.com/dagahan/theorem/users/internal/models"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestService_VerifyCredentials(t *testing.T) {
	tests := []struct {
		Name       string
		InputUser  *models.User
		ExceptedOK bool
		WantErr    bool
		SetUpMocks func(inputUser *models.User, userRepo *mockuserRepo, hasher *mockhasher)
	}{
		{
			Name: "Success",
			InputUser: &models.User{
				Email:          "some@test.com",
				Password:       "somepassword",
				HashedPassword: "somepasswordhash",
			},
			ExceptedOK: true,
			WantErr:    false,
			SetUpMocks: func(inputUser *models.User, userRepo *mockuserRepo, hasher *mockhasher) {
				userRepo.On("GetByEmail", mock.Anything, inputUser.Email).
					Return(inputUser, nil).
					Once()
				hasher.On("Compare", inputUser.HashedPassword, inputUser.Password).
					Return(true, nil).
					Once()
			},
		},
		{
			Name: "Failed to find user",
			InputUser: &models.User{
				Email:          "some@test.com",
				Password:       "somepassword",
				HashedPassword: "somepasswordhash",
			},
			ExceptedOK: false,
			WantErr:    true,
			SetUpMocks: func(inputUser *models.User, userRepo *mockuserRepo, hasher *mockhasher) {
				userRepo.On("GetByEmail", mock.Anything, inputUser.Email).
					Return(nil, errors.New("some err")).
					Once()
			},
		},
		{
			Name: "Failed to compare password and hash",
			InputUser: &models.User{
				Email:          "some@test.com",
				Password:       "somepassword",
				HashedPassword: "somepasswordhash",
			},
			ExceptedOK: false,
			WantErr:    true,
			SetUpMocks: func(inputUser *models.User, userRepo *mockuserRepo, hasher *mockhasher) {
				userRepo.On("GetByEmail", mock.Anything, inputUser.Email).
					Return(inputUser, nil).
					Once()
				hasher.On("Compare", inputUser.HashedPassword, inputUser.Password).
					Return(false, errors.New("some err")).
					Once()
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.Name, func(t *testing.T) {
			mockUserRepo := &mockuserRepo{}
			mockHasher := &mockhasher{}

			tt.SetUpMocks(tt.InputUser, mockUserRepo, mockHasher)

			svc := New(mockUserRepo, mockHasher)

			ok, err := svc.VerifyCredentials(context.Background(), tt.InputUser)
			if tt.WantErr {
				assert.Error(t, err)
			}
			assert.Equal(t, tt.ExceptedOK, ok)

			mockUserRepo.AssertExpectations(t)
			mockHasher.AssertExpectations(t)
		})
	}
}
