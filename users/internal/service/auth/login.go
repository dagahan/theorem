package auth

import (
	"context"
	"errors"

	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
)

type LoginResult struct {
	AccessToken  string
	RefreshToken string
}

func (s *service) Login(ctx context.Context, inputUser *models.User) (*LoginResult, error) {
	ok, err := s.userService.VerifyCredentials(ctx, inputUser)
	if err != nil {
		s.l.Error("failed to login: verify credentials", "error", err)
		return nil, err
	}
	if !ok {
		s.l.Warn("failed to login: invalid credentials", "email", inputUser.Email)
		return nil, errorz.InvalidCredentials
	}

	user, err := s.userService.GetByID(ctx, inputUser.ID)
	if err != nil {
		if errors.Is(err, errorz.UserNotFound) {
			s.l.Warn("failed to login: user not found", "id", inputUser.ID)
		} else {
			s.l.Error("failed to login: get user by id", "error", err)
		}
		return nil, err
	}

	session, err := s.sessionService.Create(ctx, user.ID)
	if err != nil {
		s.l.Error("failed to login: create session", "error", err)
		return nil, err
	}

	accessToken, err := s.tokenService.CreateAccess(
		&models.AccessToken{
			UserID:    user.ID,
			SessionID: session.ID,
		},
	)
	if err != nil {
		s.l.Error("failed to login: create access token", "error", err)
		return nil, err
	}

	refreshToken, err := s.tokenService.CreateRefresh(
		&models.RefreshToken{
			UserID:    user.ID,
			SessionID: session.ID,
		},
	)
	if err != nil {
		s.l.Error("failed to login: create refresh token", "error", err)
		return nil, err
	}

	return &LoginResult{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
	}, nil
}
