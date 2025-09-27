package users

import (
	"context"
	"errors"
	"testing"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestService_Create(t *testing.T) {
	tests := []struct {
		Name         string
		InputUser    *models.User
		ExceptedUser *models.User
		WantErr      bool
		SetUpMocks   func(
			inputUser *models.User,
			resultUser *models.User,
			userRepo *mockuserRepo,
			hasher *mockhasher,
		)
	}{
		{
			Name: "Success",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExceptedUser: &models.User{
				ID:             uuid.New(),
				Email:          "some@test.com",
				HashedPassword: "somepasswordhash",
			},
			WantErr: false,
			SetUpMocks: func(inputUser *models.User, resultUser *models.User, userRepo *mockuserRepo, hasher *mockhasher) {
				hasher.On("Hash", inputUser.Password).Return(resultUser.HashedPassword, nil).Once()
				userRepo.On("Create", mock.Anything, inputUser).Return(resultUser, nil).Once()
			},
		},
		{
			Name: "User already exists",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExceptedUser: nil,
			WantErr:      true,
			SetUpMocks: func(inputUser *models.User, resultUser *models.User, userRepo *mockuserRepo, hasher *mockhasher) {
				hasher.On("Hash", inputUser.Password).Return("somepasswordhash", nil).Once()
				userRepo.On("Create", mock.Anything, inputUser).Return(nil, errorz.UserAlreadyExists).Once()
			},
		},
		{
			Name: "Error hashing password",
			InputUser: &models.User{
				Password: "somepassword",
			},
			ExceptedUser: nil,
			WantErr:      true,
			SetUpMocks: func(inputUser *models.User, resultUser *models.User, userRepo *mockuserRepo, hasher *mockhasher) {
				hasher.On("Hash", inputUser.Password).Return("", errors.New("some internal error")).Once()
			},
		},
		{
			Name: "Error in repo",
			InputUser: &models.User{
				Email:    "some@test.com",
				Password: "somepassword",
			},
			ExceptedUser: nil,
			WantErr:      true,
			SetUpMocks: func(inputUser *models.User, resultUser *models.User, userRepo *mockuserRepo, hasher *mockhasher) {
				hasher.On("Hash", inputUser.Password).Return("somepasswordhash", nil).Once()
				userRepo.On("Create", mock.Anything, inputUser).Return(nil, errors.New("some repo err")).Once()
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.Name, func(t *testing.T) {
			mockHasher := &mockhasher{}
			mockUserRepo := &mockuserRepo{}

			tt.SetUpMocks(tt.InputUser, tt.ExceptedUser, mockUserRepo, mockHasher)

			svc := New(mockUserRepo, mockHasher)

			user, err := svc.Create(context.Background(), tt.InputUser)
			if tt.WantErr {
				assert.Error(t, err)
			}
			assert.Equal(t, tt.ExceptedUser, user)

			mockHasher.AssertExpectations(t)
			mockUserRepo.AssertExpectations(t)
		})
	}
}
