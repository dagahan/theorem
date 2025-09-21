package auth

import (
	"context"

	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/dagahan/theorem/users/internal/errorz"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (h *handler) AuthenticateRequest(ctx context.Context, req *pb.AuthenticateRequestRequest) (*pb.AuthenticateRequestResponse, error) {
	accessToken := req.GetAccessToken()

	result, err := h.service.AuthenticateRequest(ctx, accessToken)
	switch {
	case err != nil:
		return nil, status.Error(codes.Internal, errorz.InternalServerError.Error())
	}
	if !result.Ok {
		return nil, status.Error(codes.Unauthenticated, errorz.InvalidToken.Error())
	}

	return &pb.AuthenticateRequestResponse{
		Ok:     result.Ok,
		UserId: result.UserID,
	}, nil
}
