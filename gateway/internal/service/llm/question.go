package llm

import (
	"context"
	"fmt"

	pb "github.com/dagahan/theorem/gen/go/llm_gateway/v1"
)

func (s *service) Question(ctx context.Context, text string) (string, error) {
	req := &pb.QuestionRequest{
		RawText:   text,
		Stream:    false,
		AgentName: s.agentName,
	}
	resp, err := s.llmClient.Question(ctx, req)
	if err != nil {
		s.l.Error("failed to make a question with llm gateway",
			"error", err,
			"response", resp,
		)
		return "", fmt.Errorf("failed to make a question with llm gateway: %w", err)
	}

	s.l.Info("successful question",
		"response", resp,
	)

	return resp.Answer, err
}
