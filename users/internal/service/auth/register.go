package auth

import (
	"context"
	"errors"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
)

type RegisterResult struct {
	User         *models.User
	AccessToken  string
	RefreshToken string
}

func (s *service) Register(ctx context.Context, inputUser *models.User) (*RegisterResult, error) {
	user, err := s.userService.Create(ctx, inputUser)
	if err != nil {
		if errors.Is(err, errorz.UserAlreadyExists) {
			s.l.Warn("user already exists", "email", inputUser.Email)
		} else {
			s.l.Error("failed to create user", "email", inputUser.Email, "error", err)
		}
		return nil, err
	}

	session, err := s.sessionService.Create(ctx, user.ID)
	if err != nil {
		s.l.Error("failed to create session", "user_id", user.ID, "error", err)
		return nil, err
	}

	accessToken, err := s.tokenService.CreateAccess(
		&models.TokenClaims{
			UserID:    user.ID,
			SessionID: session.ID,
		},
	)
	if err != nil {
		s.l.Error("failed to create access token", "user_id", user.ID, "error", err)
		return nil, err
	}

	refreshToken, err := s.tokenService.CreateRefresh(
		&models.TokenClaims{
			UserID:    user.ID,
			SessionID: session.ID,
		},
	)
	if err != nil {
		s.l.Error("failed to create refresh token", "user_id", user.ID, "error", err)
		return nil, err
	}

	s.l.Info("registered user", "user_id", user.ID)

	return &RegisterResult{
		User: &models.User{
			ID:    user.ID,
			Email: user.Email,
		},
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
	}, nil
}
