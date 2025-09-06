package handlers

import (
	"net/http"
	"strconv"

	"llm-gateway/internal/models"
	"llm-gateway/internal/services"
	"llm-gateway/internal/utils"
	"llm-gateway/pkg/jwt"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// UserHandler обрабатывает HTTP запросы для пользователей
type UserHandler struct {
	userService    *services.UserService
	sessionService *services.SessionService
	jwtManager     *jwt.JWTManager
}

// NewUserHandler создает новый обработчик пользователей
func NewUserHandler(userService *services.UserService, sessionService *services.SessionService, jwtManager *jwt.JWTManager) *UserHandler {
	return &UserHandler{
		userService:    userService,
		sessionService: sessionService,
		jwtManager:     jwtManager,
	}
}

// Register регистрирует нового пользователя
func (h *UserHandler) Register(c *gin.Context) {
	var dto models.UserCreateDTO
	if err := c.ShouldBindJSON(&dto); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "Invalid request data",
			Message: err.Error(),
			Code:    http.StatusBadRequest,
		})
		return
	}

	// Валидируем пароль
	if err := utils.ValidatePassword(dto.Password); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "Password validation failed",
			Message: err.Error(),
			Code:    http.StatusBadRequest,
		})
		return
	}

	// Создаем пользователя
	user, err := h.userService.CreateUser(&dto)
	if err != nil {
		logrus.WithError(err).Error("Failed to create user")
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "Failed to create user",
			Message: err.Error(),
			Code:    http.StatusBadRequest,
		})
		return
	}

	// Создаем сессию
	userAgent := c.GetHeader("User-Agent")
	clientID, _ := utils.GenerateClientID()
	timeZone := "UTC" // Можно получить из заголовков
	platform := "web" // Можно определить по User-Agent
	clientIP := c.ClientIP()

	session, err := h.sessionService.CreateSession(user.ID, userAgent, clientID, timeZone, platform, clientIP)
	if err != nil {
		logrus.WithError(err).Error("Failed to create session")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to create session",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	// Генерируем токены
	accessToken, err := h.jwtManager.GenerateAccessToken(user.ID, session.SessionID, string(user.Role))
	if err != nil {
		logrus.WithError(err).Error("Failed to generate access token")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to generate access token",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	refreshToken, err := h.jwtManager.GenerateRefreshToken(user.ID, session.SessionID, string(user.Role))
	if err != nil {
		logrus.WithError(err).Error("Failed to generate refresh token")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to generate refresh token",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	c.JSON(http.StatusCreated, models.RegisterResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		Success:      true,
	})
}

// Login выполняет вход пользователя
func (h *UserHandler) Login(c *gin.Context) {
	var dto models.LoginRequest
	if err := c.ShouldBindJSON(&dto); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "Invalid request data",
			Message: err.Error(),
			Code:    http.StatusBadRequest,
		})
		return
	}

	// Находим пользователя
	user, err := h.userService.FindUserByCredentials(&dto)
	if err != nil {
		c.JSON(http.StatusUnauthorized, models.ErrorResponse{
			Error:   "Invalid credentials",
			Message: err.Error(),
			Code:    http.StatusUnauthorized,
		})
		return
	}

	// Проверяем пароль
	if !h.userService.VerifyPassword(user, dto.Password) {
		c.JSON(http.StatusUnauthorized, models.ErrorResponse{
			Error: "Invalid credentials",
			Code:  http.StatusUnauthorized,
		})
		return
	}

	// Проверяем что пользователь активен
	if !user.IsActive {
		c.JSON(http.StatusForbidden, models.ErrorResponse{
			Error: "User is inactive",
			Code:  http.StatusForbidden,
		})
		return
	}

	// Создаем сессию
	userAgent := c.GetHeader("User-Agent")
	clientID, _ := utils.GenerateClientID()
	timeZone := "UTC"
	platform := "web"
	clientIP := c.ClientIP()

	session, err := h.sessionService.CreateSession(user.ID, userAgent, clientID, timeZone, platform, clientIP)
	if err != nil {
		logrus.WithError(err).Error("Failed to create session")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to create session",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	// Генерируем токены
	accessToken, err := h.jwtManager.GenerateAccessToken(user.ID, session.SessionID, string(user.Role))
	if err != nil {
		logrus.WithError(err).Error("Failed to generate access token")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to generate access token",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	refreshToken, err := h.jwtManager.GenerateRefreshToken(user.ID, session.SessionID, string(user.Role))
	if err != nil {
		logrus.WithError(err).Error("Failed to generate refresh token")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to generate refresh token",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	c.JSON(http.StatusOK, models.LoginResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		Success:      true,
	})
}

// Logout выполняет выход пользователя
func (h *UserHandler) Logout(c *gin.Context) {
	sessionID, exists := c.Get("sessionID")
	if !exists {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error: "Session ID not found in token",
			Code:  http.StatusBadRequest,
		})
		return
	}

	sessionIDStr, ok := sessionID.(string)
	if !ok {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error: "Invalid session ID type",
			Code:  http.StatusInternalServerError,
		})
		return
	}

	// Деактивируем сессию
	if err := h.sessionService.DeactivateSession(sessionIDStr); err != nil {
		logrus.WithError(err).Error("Failed to deactivate session")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to logout",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	c.JSON(http.StatusOK, models.LogoutResponse{
		Success: true,
	})
}

// BanUser блокирует пользователя (только для админов)
func (h *UserHandler) BanUser(c *gin.Context) {
	var dto models.BanRequest
	if err := c.ShouldBindJSON(&dto); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "Invalid request data",
			Message: err.Error(),
			Code:    http.StatusBadRequest,
		})
		return
	}

	// Блокируем пользователя
	if err := h.userService.BanUser(dto.BanUserID); err != nil {
		logrus.WithError(err).Error("Failed to ban user")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to ban user",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	// Деактивируем все сессии пользователя
	if err := h.sessionService.DeactivateAllUserSessions(dto.BanUserID); err != nil {
		logrus.WithError(err).Error("Failed to deactivate user sessions")
	}

	c.JSON(http.StatusOK, models.BanResponse{
		Success: true,
	})
}

// UnbanUser разблокирует пользователя (только для админов)
func (h *UserHandler) UnbanUser(c *gin.Context) {
	var dto models.UnbanRequest
	if err := c.ShouldBindJSON(&dto); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "Invalid request data",
			Message: err.Error(),
			Code:    http.StatusBadRequest,
		})
		return
	}

	// Разблокируем пользователя
	if err := h.userService.UnbanUser(dto.UnbanUserID); err != nil {
		logrus.WithError(err).Error("Failed to unban user")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to unban user",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	c.JSON(http.StatusOK, models.UnbanResponse{
		Success: true,
	})
}

// GetProfile получает профиль текущего пользователя
func (h *UserHandler) GetProfile(c *gin.Context) {
	user, exists := c.Get("user")
	if !exists {
		c.JSON(http.StatusUnauthorized, models.ErrorResponse{
			Error: "User not found in context",
			Code:  http.StatusUnauthorized,
		})
		return
	}

	userModel, ok := user.(*models.User)
	if !ok {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error: "Invalid user type in context",
			Code:  http.StatusInternalServerError,
		})
		return
	}

	// Убираем чувствительные данные
	userModel.HashedPassword = ""

	c.JSON(http.StatusOK, models.SuccessResponse{
		Success: true,
		Data:    userModel,
	})
}

// UpdateProfile обновляет профиль пользователя
func (h *UserHandler) UpdateProfile(c *gin.Context) {
	user, exists := c.Get("user")
	if !exists {
		c.JSON(http.StatusUnauthorized, models.ErrorResponse{
			Error: "User not found in context",
			Code:  http.StatusUnauthorized,
		})
		return
	}

	userModel, ok := user.(*models.User)
	if !ok {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error: "Invalid user type in context",
			Code:  http.StatusInternalServerError,
		})
		return
	}

	var updateData struct {
		FirstName  string `json:"first_name"`
		LastName   string `json:"last_name"`
		MiddleName string `json:"middle_name"`
		Email      string `json:"email"`
		Phone      string `json:"phone"`
	}

	if err := c.ShouldBindJSON(&updateData); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "Invalid request data",
			Message: err.Error(),
			Code:    http.StatusBadRequest,
		})
		return
	}

	// Обновляем поля если они переданы
	if updateData.FirstName != "" {
		userModel.FirstName = updateData.FirstName
	}
	if updateData.LastName != "" {
		userModel.LastName = updateData.LastName
	}
	if updateData.MiddleName != "" {
		userModel.MiddleName = updateData.MiddleName
	}
	if updateData.Email != "" {
		// Проверяем уникальность email
		unique, err := h.userService.IsAttributeUnique("email", updateData.Email, userModel.ID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:   "Failed to check email uniqueness",
				Message: err.Error(),
				Code:    http.StatusInternalServerError,
			})
			return
		}
		if !unique {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error: "Email already exists",
				Code:  http.StatusBadRequest,
			})
			return
		}
		userModel.Email = updateData.Email
	}
	if updateData.Phone != "" {
		// Проверяем уникальность phone
		unique, err := h.userService.IsAttributeUnique("phone", updateData.Phone, userModel.ID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:   "Failed to check phone uniqueness",
				Message: err.Error(),
				Code:    http.StatusInternalServerError,
			})
			return
		}
		if !unique {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error: "Phone already exists",
				Code:  http.StatusBadRequest,
			})
			return
		}
		userModel.Phone = updateData.Phone
	}

	// Сохраняем изменения
	if err := h.userService.UpdateUser(userModel); err != nil {
		logrus.WithError(err).Error("Failed to update user")
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "Failed to update profile",
			Message: err.Error(),
			Code:    http.StatusInternalServerError,
		})
		return
	}

	// Убираем чувствительные данные
	userModel.HashedPassword = ""

	c.JSON(http.StatusOK, models.SuccessResponse{
		Success: true,
		Data:    userModel,
		Message: "Profile updated successfully",
	})
}