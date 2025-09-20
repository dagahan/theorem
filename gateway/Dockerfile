FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY gateway/go.mod gateway/go.sum ./gateway/
COPY gen/go.mod gen/go.sum ./gen/

WORKDIR /app/gateway
RUN go mod download

WORKDIR /app
COPY gateway/ ./gateway/
COPY gen/ ./gen/

WORKDIR /app/gateway

ENV GOCACHE=/root/.cache/go-build
RUN --mount=type=cache,target="/root/.cache/go-build" go build -o /app/gateway-bin ./cmd/

FROM scratch AS runner

WORKDIR /app

COPY --from=builder /app/gateway-bin ./gateway

USER 1000:1000

CMD ["./gateway"]
