package users

import (
	"context"

	"github.com/dagahan/theorem/users/internal/db/ent"
	"github.com/dagahan/theorem/users/internal/db/ent/user"
	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
	"github.com/dagahan/theorem/users/internal/repository/mappers"
)

func (r *userRepo) GetByEmail(ctx context.Context, email string) (*models.User, error) {
	u, err := r.client.User.
		Query().
		Where(user.Email(email)).
		Only(ctx)
	if err != nil {
		if ent.IsNotFound(err) {
			return nil, errorz.UserNotFound
		}
		return nil, err
	}

	return mappers.EntUserToModel(u), nil
}
