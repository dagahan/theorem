package services

import (
	"errors"
	"fmt"

	"llm-gateway/internal/models"
	"llm-gateway/internal/utils"
	"llm-gateway/pkg/database"

	"gorm.io/gorm"
)

// UserService предоставляет методы для работы с пользователями
type UserService struct {
	db *database.Database
}

// NewUserService создает новый сервис пользователей
func NewUserService(db *database.Database) *UserService {
	return &UserService{db: db}
}

// CreateUser создает нового пользователя
func (s *UserService) CreateUser(dto *models.UserCreateDTO) (*models.User, error) {
	// Проверяем уникальность username
	if dto.UserName != "" {
		var existingUser models.User
		if err := s.db.DB.Where("user_name = ?", dto.UserName).First(&existingUser).Error; err == nil {
			return nil, errors.New("username already exists")
		}
	}

	// Проверяем уникальность email
	if dto.Email != "" {
		var existingUser models.User
		if err := s.db.DB.Where("email = ?", dto.Email).First(&existingUser).Error; err == nil {
			return nil, errors.New("email already exists")
		}
	}

	// Проверяем уникальность phone
	if dto.Phone != "" && dto.Phone != "0000000000" {
		var existingUser models.User
		if err := s.db.DB.Where("phone = ?", dto.Phone).First(&existingUser).Error; err == nil {
			return nil, errors.New("phone already exists")
		}
	}

	// Хешируем пароль
	hashedPassword, err := utils.HashPassword(dto.Password)
	if err != nil {
		return nil, fmt.Errorf("failed to hash password: %w", err)
	}

	// Создаем пользователя
	user := &models.User{
		UserName:       dto.UserName,
		Email:          dto.Email,
		Phone:          dto.Phone,
		FirstName:      dto.FirstName,
		LastName:       dto.LastName,
		MiddleName:     dto.MiddleName,
		HashedPassword: hashedPassword,
		Role:           dto.Role,
		IsActive:       true,
	}

	// Устанавливаем роль по умолчанию если не указана
	if user.Role == "" {
		user.Role = models.RoleUser
	}

	if err := s.db.DB.Create(user).Error; err != nil {
		return nil, fmt.Errorf("failed to create user: %w", err)
	}

	return user, nil
}

// FindUserByCredentials находит пользователя по любым учетным данным
func (s *UserService) FindUserByCredentials(dto *models.LoginRequest) (*models.User, error) {
	var user models.User
	var query *gorm.DB

	// Определяем по какому полю искать
	if dto.UserName != "" {
		query = s.db.DB.Where("user_name = ?", dto.UserName)
	} else if dto.Email != "" {
		query = s.db.DB.Where("email = ?", dto.Email)
	} else if dto.Phone != "" {
		query = s.db.DB.Where("phone = ?", dto.Phone)
	} else {
		return nil, errors.New("no login credential provided")
	}

	if err := query.First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, errors.New("invalid credentials")
		}
		return nil, fmt.Errorf("failed to find user: %w", err)
	}

	return &user, nil
}

// VerifyPassword проверяет пароль пользователя
func (s *UserService) VerifyPassword(user *models.User, password string) bool {
	return utils.CheckPassword(password, user.HashedPassword)
}

// GetUserByID получает пользователя по ID
func (s *UserService) GetUserByID(id uint) (*models.User, error) {
	var user models.User
	if err := s.db.DB.First(&user, id).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, errors.New("user not found")
		}
		return nil, fmt.Errorf("failed to get user: %w", err)
	}
	return &user, nil
}

// BanUser блокирует пользователя
func (s *UserService) BanUser(userID uint) error {
	return s.db.DB.Model(&models.User{}).Where("id = ?", userID).Update("is_active", false).Error
}

// UnbanUser разблокирует пользователя
func (s *UserService) UnbanUser(userID uint) error {
	return s.db.DB.Model(&models.User{}).Where("id = ?", userID).Update("is_active", true).Error
}

// UpdateUser обновляет данные пользователя
func (s *UserService) UpdateUser(user *models.User) error {
	return s.db.DB.Save(user).Error
}

// DeleteUser удаляет пользователя (мягкое удаление)
func (s *UserService) DeleteUser(userID uint) error {
	return s.db.DB.Delete(&models.User{}, userID).Error
}

// IsAttributeUnique проверяет уникальность атрибута
func (s *UserService) IsAttributeUnique(field, value string, excludeID uint) (bool, error) {
	var count int64
	query := s.db.DB.Model(&models.User{}).Where(field+" = ?", value)
	
	if excludeID != 0 {
		query = query.Where("id != ?", excludeID)
	}
	
	if err := query.Count(&count).Error; err != nil {
		return false, err
	}
	
	return count == 0, nil
}