package auth

import (
	"context"
	"fmt"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type RefreshTokensResult struct {
	AccessToken  string
	RefreshToken string
}

func (s *service) RefreshTokens(ctx context.Context, refreshToken string) (*RefreshTokensResult, error) {
	req := &pb.RefreshTokensRequest{
		RefreshToken: refreshToken,
	}
	resp, err := s.authClient.RefreshTokens(ctx, req)
	st, ok := status.FromError(err)
	if !ok {
		s.l.Error("failed to refresh tokens", "error", err)
		return nil, err
	}

	switch st.Code() {
	case codes.OK:
		break
	case codes.Unauthenticated:
		s.l.Warn("failed to refresh tokens: unauthenticated", "error", err)
		return nil, fmt.Errorf("%w: %s", errorz.Unauthorized, st.Message())
	case codes.Internal:
		s.l.Error("failed to refresh tokens: internal", "error", err)
		return nil, err
	default:
		s.l.Error("failed to refresh tokens: unknown code", "error", err)
		return nil, err
	}

	return &RefreshTokensResult{
		AccessToken:  resp.AccessToken,
		RefreshToken: resp.RefreshToken,
	}, nil
}
