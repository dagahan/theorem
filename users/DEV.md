Генерация таблиц

```shell
go run entgo.io/ent/cmd/ent new --target internal/db/schema {TableName}
```

Генерация орм

```shell
go run -mod=mod entgo.io/ent/cmd/ent generate ./internal/db/schema --target ./internal/db/ent/
```
