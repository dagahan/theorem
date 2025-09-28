package llm

import (
	"context"

	"github.com/labstack/echo/v4"
)

type service interface {
	Question(ctx context.Context, text string) (string, error)
}

type authMiddleware interface {
	RequireAuth(next echo.HandlerFunc) echo.HandlerFunc
}

type handler struct {
	service        service
	authMiddleware authMiddleware
}

func New(
	service service,
	authMiddleware authMiddleware,
) *handler {
	return &handler{
		service:        service,
		authMiddleware: authMiddleware,
	}
}

func (h *handler) Setup(router *echo.Group) {
	router.POST("/question", h.Question, h.authMiddleware.RequireAuth)
}
