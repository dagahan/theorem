package auth

import (
	"context"

	"github.com/dagahan/theorem/gateway/internal/models"
	authservice "github.com/dagahan/theorem/gateway/internal/service/auth"
	"github.com/go-playground/validator/v10"
	"github.com/labstack/echo/v4"
)

type service interface {
	Register(ctx context.Context, user *models.User) (*authservice.RegisterResult, error)
	Login(ctx context.Context, user *models.User) (*authservice.LoginResult, error)
	Logout(ctx context.Context, accessToken string) error
}

type handler struct {
	service   service
	validator *validator.Validate
}

func New(
	service service,
) *handler {
	return &handler{
		service:   service,
		validator: validator.New(),
	}
}

func (h *handler) Setup(router *echo.Group) {
	router.POST("/register", h.Register)
	router.POST("/login", h.Login)
	router.POST("/logout", h.Logout)
}
