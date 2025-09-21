FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY users/go.mod users/go.sum ./users/
COPY gen/go.mod gen/go.sum ./gen/

WORKDIR /app/users
RUN go mod download

WORKDIR /app
COPY users/ ./users/
COPY gen/ ./gen/

WORKDIR /app/users

ENV GOCACHE=/root/.cache/go-build
RUN --mount=type=cache,target="/root/.cache/go-build" go build -o /app/users-bin ./cmd/

FROM scratch AS runner

WORKDIR /app

COPY --from=builder /app/users-bin ./users

USER 1000:1000

CMD ["./users"]
