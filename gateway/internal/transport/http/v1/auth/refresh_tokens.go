package auth

import (
	"errors"
	"net/http"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	"github.com/dagahan/theorem/gateway/internal/transport/http/dto"
	"github.com/labstack/echo/v4"
)

func (h *handler) RefreshTokens(c echo.Context) error {
	var req dto.RefreshTokensRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, dto.HTTPStatus{
			Code:    http.StatusBadRequest,
			Message: err.Error(),
		})
	}

	result, err := h.service.RefreshTokens(c.Request().Context(), req.RefreshToken)
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

	resp := &dto.RefreshTokensResponse{
		AccessToken:  result.AccessToken,
		RefreshToken: result.RefreshToken,
	}
	return c.JSON(http.StatusOK, resp)
}
