package llm

import (
	"context"
	"log/slog"

	pb "github.com/dagahan/theorem/gen/go/llm_gateway/v1"
	"google.golang.org/grpc"
)

type llmClient interface {
	Health(ctx context.Context, in *pb.HealthRequest, opts ...grpc.CallOption) (*pb.HealthResponse, error)
	Question(ctx context.Context, in *pb.QuestionRequest, opts ...grpc.CallOption) (*pb.QuestionResponse, error)
}

type service struct {
	l         *slog.Logger
	llmClient llmClient
}

func New(
	l *slog.Logger,
	llmClient llmClient,
) *service {
	return &service{
		l:         l,
		llmClient: llmClient,
	}
}
