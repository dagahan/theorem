package users

import (
	"context"

	"github.com/dagahan/theorem/users/internal/db/ent"
	"github.com/dagahan/theorem/users/internal/errorz"
	"github.com/google/uuid"
)

func (r *userRepo) Delete(ctx context.Context, id uuid.UUID) error {
	err := r.client.User.
		DeleteOneID(id).
		Exec(ctx)
	if ent.IsNotFound(err) {
		return errorz.UserNotFound
	}

	return err
}
