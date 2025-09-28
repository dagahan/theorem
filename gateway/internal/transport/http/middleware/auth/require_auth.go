package auth

import (
	"errors"
	"net/http"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	"github.com/dagahan/theorem/gateway/internal/transport/http/dto"
	"github.com/dagahan/theorem/gateway/internal/transport/http/headers"
	"github.com/labstack/echo/v4"
)

func (m *middleware) RequireAuth(next echo.HandlerFunc) echo.HandlerFunc {
	return func(c echo.Context) error {
		accessToken := headers.GetTokenFromHeader(c)
		if accessToken == "" {
			return c.JSON(http.StatusUnauthorized, dto.HTTPStatus{
				Code:    http.StatusUnauthorized,
				Message: errorz.Unauthorized.Error(),
			})
		}

		userID, err := m.authService.AuthenticateRequest(c.Request().Context(), accessToken)
		switch {
		case errors.Is(err, errorz.Unauthorized):
			return c.JSON(http.StatusUnauthorized, dto.HTTPStatus{
				Code:    http.StatusUnauthorized,
				Message: err.Error(),
			})
		case err != nil:
			return c.JSON(http.StatusInternalServerError, dto.HTTPStatus{
				Code:    http.StatusInternalServerError,
				Message: errorz.InternalServerError.Error(),
			})
		}

		c.Set("user_id", userID)

		return next(c)
	}
}
