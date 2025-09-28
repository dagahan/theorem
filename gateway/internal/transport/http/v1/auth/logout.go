package auth

import (
	"net/http"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	"github.com/dagahan/theorem/gateway/internal/transport/http/dto"
	"github.com/dagahan/theorem/gateway/internal/transport/http/headers"
	"github.com/labstack/echo/v4"
)

func (h *handler) Logout(c echo.Context) error {
	accessToken := headers.GetTokenFromHeader(c)
	if accessToken == "" {
		return c.JSON(http.StatusUnauthorized, dto.HTTPStatus{
			Code:    http.StatusUnauthorized,
			Message: errorz.Unauthorized.Error(),
		})
	}

	err := h.service.Logout(c.Request().Context(), accessToken)
	switch {
	case err != nil:
		return c.JSON(http.StatusInternalServerError, dto.HTTPStatus{
			Code:    http.StatusInternalServerError,
			Message: errorz.InternalServerError.Error(),
		})
	}

	return c.NoContent(http.StatusNoContent)
}
