package users

import (
	"context"

	"github.com/dagahan/theorem/users/internal/db/ent"
	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/dagahan/theorem/users/internal/repository/mappers"
)

func (r *userRepo) Create(ctx context.Context, user *models.User) (*models.User, error) {
	created, err := r.client.User.
		Create().
		SetEmail(user.Email).
		SetPassword(user.HashedPassword).
		Save(ctx)
	if err != nil {
		if ent.IsConstraintError(err) {
			return nil, errorz.UserAlreadyExists
		}
		return nil, err
	}

	return mappers.EntUserToModel(created), nil
}
