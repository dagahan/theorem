package users

import (
	"context"

	"github.com/dagahan/theorem/users/internal/db/ent"
	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/dagahan/theorem/users/internal/models"
)

func (r *userRepo) Update(ctx context.Context, user *models.User) error {
	_, err := r.client.User.
		UpdateOneID(user.ID).
		SetEmail(user.Email).
		SetPassword(user.HashedPassword).
		Save(ctx)
	if ent.IsNotFound(err) {
		return errorz.UserNotFound
	}
	if ent.IsConstraintError(err) {
		return errorz.EmailAlreadyInUse
	}

	return err
}
