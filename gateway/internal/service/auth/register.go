package auth

import (
	"context"
	"fmt"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	"github.com/dagahan/theorem/gateway/internal/models"
	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/google/uuid"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type RegisterResult struct {
	UserID       uuid.UUID
	AccessToken  string
	RefreshToken string
}

func (s *service) Register(ctx context.Context, user *models.User) (*RegisterResult, error) {
	req := &pb.RegisterRequest{
		Email:    user.Email,
		Password: user.Password,
	}
	resp, err := s.authClient.Register(ctx, req)
	st, ok := status.FromError(err)
	if !ok {
		s.l.Error("failed to register: get status from error", "error", err)
		return nil, err
	}

	switch st.Code() {
	case codes.OK:
		break
	case codes.InvalidArgument:
		s.l.Error("failed to register: invalid argument", "error", err)
		return nil, fmt.Errorf("%w: %s", errorz.BadRequest, st.Message())
	case codes.AlreadyExists:
		s.l.Error("failed to register: already exists", "error", err)
		return nil, errorz.UserAlreadyExists
	case codes.Internal:
		s.l.Error("failed to register: internal error", "error", err)
		return nil, err
	default:
		s.l.Error("failed to register: unknown code", "error", err)
		return nil, err
	}

	userID, err := uuid.Parse(resp.UserId)
	if err != nil {
		s.l.Error("failed to register: parse user id", "error", err)
		return nil, err
	}

	return &RegisterResult{
		UserID:       userID,
		AccessToken:  resp.AccessToken,
		RefreshToken: resp.RefreshToken,
	}, nil
}
