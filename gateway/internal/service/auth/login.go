package auth

import (
	"context"
	"fmt"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	"github.com/dagahan/theorem/gateway/internal/models"
	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type LoginResult struct {
	AccessToken  string
	RefreshToken string
}

func (s *service) Login(ctx context.Context, user *models.User) (*LoginResult, error) {
	req := &pb.LoginRequest{
		Email:    user.Email,
		Password: user.Password,
	}
	res, err := s.authClient.Login(ctx, req)
	st, ok := status.FromError(err)
	if !ok {
		s.l.Error("failed to login: get status from error", "error", err)
		return nil, err
	}

	switch st.Code() {
	case codes.OK:
		break
	case codes.InvalidArgument:
		s.l.Error("failed to login: invalid argument", "error", err)
		return nil, fmt.Errorf("%w: %s", errorz.BadRequest, st.Message())
	case codes.Unauthenticated:
		s.l.Error("failed to login: unauthenticated", "error", err)
		return nil, errorz.InvalidCredentials
	case codes.Internal:
		s.l.Error("failed to login: internal error", "error", err)
		return nil, err
	default:
		s.l.Error("failed to register: unknown code", "error", err)
		return nil, err
	}

	return &LoginResult{
		AccessToken:  res.AccessToken,
		RefreshToken: res.RefreshToken,
	}, nil
}
