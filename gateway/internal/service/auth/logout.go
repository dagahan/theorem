package auth

import (
	"context"

	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func (s *service) Logout(ctx context.Context, accessToken string) error {
	req := &pb.LogoutRequest{
		AccessToken: accessToken,
	}
	_, err := s.authClient.Logout(ctx, req)
	st, ok := status.FromError(err)
	if !ok {
		s.l.Error("failed to logout: get status from error", "error", err)
		return err
	}

	switch st.Code() {
	case codes.OK:
		return nil
	case codes.Internal:
		s.l.Error("failed to logout: internal error", "error", err)
		return err
	default:
		s.l.Error("failed to logout: unknown code", "error", err)
		return err
	}
}
