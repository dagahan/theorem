package auth

import (
	"errors"
	"net/http"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	"github.com/dagahan/theorem/gateway/internal/models"
	"github.com/dagahan/theorem/gateway/internal/transport/http/dto"
	"github.com/labstack/echo/v4"
)

func (h *handler) Register(c echo.Context) error {
	var req dto.RegisterRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, dto.HTTPStatus{
			Code:    http.StatusBadRequest,
			Message: err.Error(),
		})
	}

	if err := h.validator.Struct(req); err != nil {
		return c.JSON(http.StatusBadRequest, dto.HTTPStatus{
			Code:    http.StatusBadRequest,
			Message: err.Error(),
		})
	}

	user := &models.User{
		Email:    req.Email,
		Password: req.Password,
	}
	result, err := h.service.Register(c.Request().Context(), user)
	switch {
	case errors.Is(err, errorz.BadRequest):
		return c.JSON(http.StatusBadRequest, dto.HTTPStatus{
			Code:    http.StatusBadRequest,
			Message: err.Error(),
		})
	case errors.Is(err, errorz.UserAlreadyExists):
		return c.JSON(http.StatusConflict, dto.HTTPStatus{
			Code:    http.StatusConflict,
			Message: err.Error(),
		})
	case err != nil:
		return c.JSON(http.StatusInternalServerError, dto.HTTPStatus{
			Code:    http.StatusInternalServerError,
			Message: errorz.InternalServerError.Error(),
		})
	}

	resp := &dto.RegisterResponse{
		UserID:       result.UserID.String(),
		AccessToken:  result.AccessToken,
		RefreshToken: result.RefreshToken,
	}
	return c.JSON(http.StatusCreated, resp)
}
