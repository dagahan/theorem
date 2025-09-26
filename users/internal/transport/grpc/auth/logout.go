package auth

import (
	"context"

	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/dagahan/theorem/users/internal/errorz"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (h *handler) Logout(ctx context.Context, req *pb.LogoutRequest) (*pb.LogoutResponse, error) {
	accessToken := req.AccessToken
	if accessToken == "" {
		return nil, status.Error(codes.InvalidArgument, "access token required")
	}

	err := h.service.Logout(ctx, accessToken)
	switch {
	case err != nil:
		return nil, status.Error(codes.Internal, errorz.InternalServerError.Error())
	}

	return &pb.LogoutResponse{}, nil
}
