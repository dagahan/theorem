package llm

import (
	"net/http"

	"github.com/dagahan/theorem/gateway/internal/errorz"
	"github.com/dagahan/theorem/gateway/internal/transport/http/dto"
	"github.com/labstack/echo/v4"
)

func (h *handler) Question(c echo.Context) error {
	var req dto.QuestionRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, dto.HTTPStatus{
			Code:    http.StatusBadRequest,
			Message: err.Error(),
		})
	}

	result, err := h.service.Question(c.Request().Context(), req.Text)
	switch {
	case err != nil:
		return c.JSON(http.StatusInternalServerError, dto.HTTPStatus{
			Code:    http.StatusInternalServerError,
			Message: errorz.InternalServerError.Error(),
		})
	}

	resp := &dto.QuestionResponse{
		Response: result,
	}
	return c.JSON(http.StatusOK, resp)
}
