package models

import (
	"time"

	"gorm.io/gorm"
)

// UserRole определяет роли пользователей
type UserRole string

const (
	RoleUser  UserRole = "user"
	RoleAdmin UserRole = "admin"
	RoleGod   UserRole = "god"
)

// User представляет пользователя в системе
type User struct {
	ID             uint      `json:"id" gorm:"primaryKey"`
	UserName       string    `json:"user_name" gorm:"uniqueIndex;not null"`
	Email          string    `json:"email" gorm:"uniqueIndex"`
	Phone          string    `json:"phone" gorm:"uniqueIndex"`
	FirstName      string    `json:"first_name" gorm:"not null"`
	LastName       string    `json:"last_name" gorm:"not null"`
	MiddleName     string    `json:"middle_name"`
	HashedPassword string    `json:"-" gorm:"not null"`
	Role           UserRole  `json:"role" gorm:"default:'user'"`
	IsActive       bool      `json:"is_active" gorm:"default:true"`
	ProfileImageID *uint     `json:"profile_image_id"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
	DeletedAt      gorm.DeletedAt `json:"-" gorm:"index"`

	// Связи
	ProfileImage *Image `json:"profile_image,omitempty" gorm:"foreignKey:ProfileImageID"`
	Sessions     []Session `json:"-" gorm:"foreignKey:UserID"`
}

// Image представляет изображение в системе
type Image struct {
	ID              uint      `json:"id" gorm:"primaryKey"`
	MediaType       string    `json:"media_type" gorm:"not null"`
	Bucket          string    `json:"bucket" gorm:"not null"`
	Key             string    `json:"key" gorm:"not null"`
	Mime            string    `json:"mime" gorm:"not null"`
	Size            int64     `json:"size"`
	ChecksumSHA256  string    `json:"checksum_sha256"`
	Width           int       `json:"width"`
	Height          int       `json:"height"`
	ExifStripped    bool      `json:"exif_stripped"`
	Colorspace      string    `json:"colorspace"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

// Session представляет сессию пользователя
type Session struct {
	ID                    uint      `json:"id" gorm:"primaryKey"`
	UserID                uint      `json:"user_id" gorm:"not null"`
	SessionID             string    `json:"session_id" gorm:"uniqueIndex;not null"`
	UserAgent             string    `json:"user_agent"`
	ClientID              string    `json:"client_id"`
	LocalSystemTimeZone   string    `json:"local_system_time_zone"`
	Platform              string    `json:"platform"`
	IP                    string    `json:"ip"`
	IsActive              bool      `json:"is_active" gorm:"default:true"`
	CreatedAt             time.Time `json:"created_at"`
	UpdatedAt             time.Time `json:"updated_at"`
	ExpiresAt             time.Time `json:"expires_at"`

	// Связи
	User User `json:"user,omitempty" gorm:"foreignKey:UserID"`
}