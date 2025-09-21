package users

import "github.com/dagahan/theorem/users/internal/db/ent"

type userRepo struct {
	client *ent.Client
}

func NewUserRepo(client *ent.Client) *userRepo {
	return &userRepo{client: client}
}
