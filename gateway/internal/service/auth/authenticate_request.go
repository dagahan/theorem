package auth

import (
	"context"
	"fmt"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/google/uuid"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (s *service) AuthenticateRequest(ctx context.Context, accessToken string) (uuid.UUID, error) {
	req := &pb.AuthenticateRequestRequest{
		AccessToken: accessToken,
	}
	res, err := s.authClient.AuthenticateRequest(ctx, req)
	st, ok := status.FromError(err)
	if !ok {
		s.l.Error("failed to authenticate request: get status from error", "error", err)
		return uuid.Nil, err
	}

	switch st.Code() {
	case codes.OK:
		break
	case codes.Unauthenticated:
		s.l.Warn("failed to authenticate: unauthenticated", "error", err)
		return uuid.Nil, fmt.Errorf("%w: %s", errorz.Unauthorized, st.Message())
	case codes.Internal:
		s.l.Error("failed to authenticate: internal", "error", err)
		return uuid.Nil, err
	default:
		s.l.Error("failed to authenticate: unknown code", "error", err)
		return uuid.Nil, err
	}

	userID, err := uuid.Parse(res.GetUserId())
	if err != nil {
		s.l.Error("failed to authenticate: invalid user id", "error", err)
		return uuid.Nil, err
	}

	return userID, nil
}
