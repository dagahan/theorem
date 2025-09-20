package dto

type QuestionRequest struct {
	Text string `json:"text"`
}

type QuestionResponse struct {
	Response string `json:"text"`
}
