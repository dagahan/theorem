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

func TestService_GetByEmail(t *testing.T) {
	tests := []struct {
		Name       string
		User       *models.User
		WantErr    bool
		SetUpMocks func(inputEmail string, resultUser *models.User, userRepo *mockuserRepo)
	}{
		{
			Name: "Success",
			User: &models.User{
				ID:             uuid.New(),
				Email:          "some@test.com",
				HashedPassword: "somepasswordhash",
			},
			WantErr: false,
			SetUpMocks: func(inputEmail string, resultUser *models.User, userRepo *mockuserRepo) {
				userRepo.On("GetByEmail", mock.Anything, inputEmail).Return(resultUser, nil).Once()
			},
		},
		{
			Name: "User not found",
			User: &models.User{
				Email: "some@test.com",
			},
			WantErr: true,
			SetUpMocks: func(inputEmail string, resultUser *models.User, userRepo *mockuserRepo) {
				userRepo.On("GetByEmail", mock.Anything, inputEmail).Return(nil, errorz.UserNotFound).Once()
			},
		},
		{
			Name: "User repository error",
			User: &models.User{
				Email: "some@test.com",
			},
			WantErr: true,
			SetUpMocks: func(inputEmail string, resultUser *models.User, userRepo *mockuserRepo) {
				userRepo.On("GetByEmail", mock.Anything, inputEmail).Return(nil, errors.New("some err")).Once()
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.Name, func(t *testing.T) {
			mockUserRepo := &mockuserRepo{}

			tt.SetUpMocks(tt.User.Email, tt.User, mockUserRepo)

			svc := New(mockUserRepo, nil)

			user, err := svc.GetByEmail(context.Background(), tt.User.Email)
			if tt.WantErr {
				assert.Error(t, err)
			} else {
				assert.Equal(t, tt.User, user)
			}

			mockUserRepo.AssertExpectations(t)
		})
	}
}
