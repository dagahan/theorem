package auth

import (
	"context"
	"errors"

	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (h *handler) Register(ctx context.Context, req *pb.RegisterRequest) (*pb.RegisterResponse, error) {
	inputUser := &models.User{
		Email:    req.GetEmail(),
		Password: req.GetPassword(),
	}

	result, err := h.service.Register(ctx, inputUser)
	switch {
	case errors.Is(err, errorz.UserAlreadyExists):
		return nil, status.Error(codes.AlreadyExists, err.Error())
	case err != nil:
		return nil, status.Error(codes.Internal, errorz.InternalServerError.Error())
	}

	return &pb.RegisterResponse{
		UserId:       result.User.ID.String(),
		AccessToken:  result.AccessToken,
		RefreshToken: result.RefreshToken,
	}, nil
}
