package auth

import (
	"context"
	"log/slog"

	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"google.golang.org/grpc"
)

type authClient interface {
	Register(ctx context.Context, in *pb.RegisterRequest, opts ...grpc.CallOption) (*pb.RegisterResponse, error)
	Login(ctx context.Context, in *pb.LoginRequest, opts ...grpc.CallOption) (*pb.LoginResponse, error)
	AuthenticateRequest(ctx context.Context, in *pb.AuthenticateRequestRequest, opts ...grpc.CallOption) (*pb.AuthenticateRequestResponse, error)
	RefreshTokens(ctx context.Context, in *pb.RefreshTokensRequest, opts ...grpc.CallOption) (*pb.RefreshTokensResponse, error)
	Logout(ctx context.Context, in *pb.LogoutRequest, opts ...grpc.CallOption) (*pb.LogoutResponse, error)
}

type service struct {
	l          *slog.Logger
	authClient authClient
}

func New(
	l *slog.Logger,
	usersClient authClient,
) *service {
	return &service{
		l:          l,
		authClient: usersClient,
	}
}
