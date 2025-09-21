package mappers

import (
	"github.com/dagahan/theorem/users/internal/db/ent"
	"github.com/dagahan/theorem/users/internal/models"
)

func EntUserToModel(u *ent.User) *models.User {
	return &models.User{
		ID:             u.ID,
		Email:          u.Email,
		HashedPassword: u.Password,
	}
}
