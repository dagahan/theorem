package auth

import (
	"context"
	"errors"

	"buf.build/go/protovalidate"
	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (h *handler) Login(ctx context.Context, req *pb.LoginRequest) (*pb.LoginResponse, error) {
	if err := protovalidate.Validate(req); err != nil {
		return nil, status.Error(codes.InvalidArgument, err.Error())
	}

	inputUser := &models.User{
		Email:    req.GetEmail(),
		Password: req.GetPassword(),
	}

	result, err := h.service.Login(ctx, inputUser)
	switch {
	case errors.Is(err, errorz.InvalidCredentials):
		return nil, status.Error(codes.Unauthenticated, err.Error())
	case err != nil:
		return nil, status.Error(codes.Internal, errorz.InternalServerError.Error())
	}

	return &pb.LoginResponse{
		AccessToken:  result.AccessToken,
		RefreshToken: result.RefreshToken,
	}, nil
}
