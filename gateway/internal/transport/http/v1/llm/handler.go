package llm

import (
	"context"

	"github.com/labstack/echo/v4"
)

type service interface {
	Question(ctx context.Context, text string) (string, error)
}

type handler struct {
	service service
}

func New(
	service service,
) *handler {
	return &handler{
		service: service,
	}
}

func (h *handler) Setup(router *echo.Group) {
	router.POST("/question", h.Question)
}
