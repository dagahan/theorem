package config

import (
	"time"

	"github.com/ilyakaznacheev/cleanenv"
)

type Config struct {
	Server   server
	Postgres postgres
	Valkey   valkey
	Token    tokenParams
	Session  sessionParams
	Hasher   hasher
}

type server struct {
	Addr string `env:"SERVER_ADDR" env-default:":8080"`
}

type postgres struct {
	URL string `env:"POSTGRES_URL" env-required:"true"`
}

type valkey struct {
	Addr     string `env:"VALKEY_ADDR" env-required:"true"`
	Password string `env:"VALKEY_PASSWORD" env-required:"true"`
}

type tokenParams struct {
	AccessTTL  time.Duration `env:"ACCESS_TOKEN_TTL" env-default:"15m"`
	RefreshTTL time.Duration `env:"REFRESH_TOKEN_TTL" env-default:"24h"`
	JWTSecret  string        `env:"JWT_SECRET" env-required:"true"`
}

type sessionParams struct {
	MaxTTL      time.Duration `env:"SESSION_MAX_TTL" env-default:"2160h"`
	InactiveTTL time.Duration `env:"SESSION_INACTIVE_TTL" env-default:"720h"`
}

type hasher struct {
	Cost int `env:"HASH_COST" env-default:"8"`
}

func NewConfig() (*Config, error) {
	var cfg Config

	// Read .env file
	// If failed to read file, will try ReadEnv
	if err := cleanenv.ReadConfig(".env", &cfg); err == nil {
		return &cfg, nil
	}

	// Read env
	if err := cleanenv.ReadEnv(&cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}
