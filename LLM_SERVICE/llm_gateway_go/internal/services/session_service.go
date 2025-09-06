package services

import (
	"errors"
	"fmt"
	"time"

	"llm-gateway/internal/models"
	"llm-gateway/internal/utils"
	"llm-gateway/pkg/database"

	"gorm.io/gorm"
)

// SessionService предоставляет методы для работы с сессиями
type SessionService struct {
	db *database.Database
}

// NewSessionService создает новый сервис сессий
func NewSessionService(db *database.Database) *SessionService {
	return &SessionService{db: db}
}

// CreateSession создает новую сессию
func (s *SessionService) CreateSession(userID uint, userAgent, clientID, timeZone, platform, ip string) (*models.Session, error) {
	sessionID, err := utils.GenerateSessionID()
	if err != nil {
		return nil, fmt.Errorf("failed to generate session ID: %w", err)
	}

	session := &models.Session{
		UserID:              userID,
		SessionID:           sessionID,
		UserAgent:           userAgent,
		ClientID:            clientID,
		LocalSystemTimeZone: timeZone,
		Platform:            platform,
		IP:                  utils.HashString(ip), // Хешируем IP для безопасности
		IsActive:            true,
		ExpiresAt:           time.Now().Add(7 * 24 * time.Hour), // 7 дней
	}

	if err := s.db.DB.Create(session).Error; err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	return session, nil
}

// GetSessionByID получает сессию по ID
func (s *SessionService) GetSessionByID(sessionID string) (*models.Session, error) {
	var session models.Session
	if err := s.db.DB.Where("session_id = ? AND is_active = ?", sessionID, true).First(&session).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, errors.New("session not found")
		}
		return nil, fmt.Errorf("failed to get session: %w", err)
	}

	// Проверяем не истекла ли сессия
	if time.Now().After(session.ExpiresAt) {
		// Деактивируем истекшую сессию
		s.DeactivateSession(sessionID)
		return nil, errors.New("session expired")
	}

	return &session, nil
}

// DeactivateSession деактивирует сессию
func (s *SessionService) DeactivateSession(sessionID string) error {
	return s.db.DB.Model(&models.Session{}).Where("session_id = ?", sessionID).Update("is_active", false).Error
}

// DeactivateAllUserSessions деактивирует все сессии пользователя
func (s *SessionService) DeactivateAllUserSessions(userID uint) error {
	return s.db.DB.Model(&models.Session{}).Where("user_id = ?", userID).Update("is_active", false).Error
}

// IsSessionActive проверяет активна ли сессия
func (s *SessionService) IsSessionActive(sessionID string) (bool, error) {
	var count int64
	err := s.db.DB.Model(&models.Session{}).Where("session_id = ? AND is_active = ?", sessionID, true).Count(&count).Error
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

// CleanupExpiredSessions удаляет истекшие сессии
func (s *SessionService) CleanupExpiredSessions() error {
	return s.db.DB.Where("expires_at < ?", time.Now()).Delete(&models.Session{}).Error
}

// GetUserSessions получает все активные сессии пользователя
func (s *SessionService) GetUserSessions(userID uint) ([]models.Session, error) {
	var sessions []models.Session
	err := s.db.DB.Where("user_id = ? AND is_active = ?", userID, true).Find(&sessions).Error
	return sessions, err
}

// UpdateSessionActivity обновляет время последней активности сессии
func (s *SessionService) UpdateSessionActivity(sessionID string) error {
	return s.db.DB.Model(&models.Session{}).Where("session_id = ?", sessionID).Update("updated_at", time.Now()).Error
}