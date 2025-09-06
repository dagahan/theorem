package models

// UserCreateDTO представляет данные для создания пользователя
type UserCreateDTO struct {
	UserName   string  `json:"user_name" binding:"required,min=3,max=50"`
	Email      string  `json:"email" binding:"omitempty,email"`
	Phone      string  `json:"phone" binding:"omitempty,len=10"`
	FirstName  string  `json:"first_name" binding:"required,min=2,max=50"`
	LastName   string  `json:"last_name" binding:"required,min=2,max=50"`
	MiddleName string  `json:"middle_name" binding:"omitempty,min=2,max=50"`
	Password   string  `json:"password" binding:"required,min=8"`
	Role       UserRole `json:"role" binding:"omitempty,oneof=user admin god"`
}

// LoginRequest представляет данные для входа
type LoginRequest struct {
	UserName string `json:"user_name" binding:"omitempty"`
	Email    string `json:"email" binding:"omitempty,email"`
	Phone    string `json:"phone" binding:"omitempty"`
	Password string `json:"password" binding:"required"`
}

// RegisterResponse представляет ответ при регистрации
type RegisterResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	Success      bool   `json:"success"`
}

// LoginResponse представляет ответ при входе
type LoginResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	Success      bool   `json:"success"`
}

// LogoutResponse представляет ответ при выходе
type LogoutResponse struct {
	Success bool `json:"success"`
}

// BanRequest представляет запрос на блокировку пользователя
type BanRequest struct {
	BanUserID uint `json:"ban_user_id" binding:"required"`
}

// UnbanRequest представляет запрос на разблокировку пользователя
type UnbanRequest struct {
	UnbanUserID uint `json:"unban_user_id" binding:"required"`
}

// BanResponse представляет ответ при блокировке
type BanResponse struct {
	Success bool `json:"success"`
}

// UnbanResponse представляет ответ при разблокировке
type UnbanResponse struct {
	Success bool `json:"success"`
}

// UploadAvatarResponse представляет ответ при загрузке аватара
type UploadAvatarResponse struct {
	Success bool `json:"success"`
}

// ErrorResponse представляет ответ с ошибкой
type ErrorResponse struct {
	Error   string `json:"error"`
	Message string `json:"message,omitempty"`
	Code    int    `json:"code"`
}

// SuccessResponse представляет успешный ответ
type SuccessResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Message string      `json:"message,omitempty"`
}