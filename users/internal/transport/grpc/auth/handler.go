package auth

import (
	pb "github.com/dagahan/theorem/gen/go/users/v1"
	"github.com/dagahan/theorem/users/internal/models"
	authservice "github.com/dagahan/theorem/users/internal/service/auth"
)

import "context"

type service interface {
	Register(ctx context.Context, inputUser *models.User) (*authservice.RegisterResult, error)
	Login(ctx context.Context, inputUser *models.User) (*authservice.LoginResult, error)
	AuthenticateRequest(ctx context.Context, accessTokenStr string) (*authservice.AuthenticateRequestResult, error)
	RefreshTokens(ctx context.Context, oldRefreshToken string) (*authservice.RefreshTokensResult, error)
}

type handler struct {
	service service
	pb.UnimplementedAuthServiceServer
}

func New(s service) *handler {
	return &handler{
		service: s,
	}
}
