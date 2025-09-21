package auth

import (
	"context"
	"errors"

	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/dagahan/theorem/users/internal/errorz"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (h *handler) RefreshTokens(ctx context.Context, req *pb.RefreshTokensRequest) (*pb.RefreshTokensResponse, error) {
	refreshToken := req.GetRefreshToken()

	result, err := h.service.RefreshTokens(ctx, refreshToken)
	switch {
	case errors.Is(err, errorz.SessionNotFound), errors.Is(err, errorz.InvalidToken):
		return nil, status.Error(codes.Unauthenticated, err.Error())
	case err != nil:
		return nil, status.Error(codes.Internal, errorz.InternalServerError.Error())
	}

	return &pb.RefreshTokensResponse{
		AccessToken:  result.AccessToken,
		RefreshToken: result.RefreshToken,
	}, nil
}
