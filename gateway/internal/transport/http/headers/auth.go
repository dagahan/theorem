package headers

import (
	"strings"

	"github.com/labstack/echo/v4"
)

func GetTokenFromHeader(c echo.Context) string {
	authHeader := c.Request().Header.Get("Authorization")
	if !strings.HasPrefix(authHeader, "Bearer ") {
		return ""
	}

	return strings.TrimSpace(strings.TrimPrefix(authHeader, "Bearer "))
}
