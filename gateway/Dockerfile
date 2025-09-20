FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./

RUN go mod download

COPY . .

ENV GOCACHE=/root/.cache/go-build
RUN --mount=type=cache,target="/root/.cache/go-build" go build -o gateway ./cmd/

FROM scratch AS runner

WORKDIR /app

COPY --from=builder /app/gateway ./gateway

USER 1000:1000

CMD ["./gateway"]
