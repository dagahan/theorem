#!/usr/bin/env bash
set -Eeuo pipefail

if [[ -f ".env" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs)
fi


# default values (if not provided by .env file)
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-${VLLM_MATH_PORT:-8000}}"

MODEL_SRC="${MODEL_SRC:-meta-llama/Llama-3.1-8B-Instruct}"
# Extract model name from MODEL_SRC (everything after the last '/')
MODEL_NAME="${MODEL_NAME:-${MODEL_SRC##*/}}"
MAX_LEN="${MAX_LEN:-8192}"
TP_SIZE="${TP_SIZE:-1}"

HF_CACHE_DIR="${HF_CACHE_DIR:-/data/hf-cache}"
export HF_HOME="${HF_HOME:-$HF_CACHE_DIR}"

GPU_UTIL="${GPU_UTIL:-0.92}"
DTYPE="${DTYPE:-auto}"

# System prompt configuration
SYSTEM_PROMPT="${SYSTEM_PROMPT:-You are a helpful assistant.}"


echo "Starting vLLM OpenAI-compatible server..."
echo "  Host:        $HOST"
echo "  Port:        $PORT"
echo "  Model:       $MODEL_SRC  (as $MODEL_NAME)"
echo "  Max Length:  $MAX_LEN"
echo "  TP Size:     $TP_SIZE"
echo "  HF Cache:    $HF_CACHE_DIR"
echo "  GPU Util:    $GPU_UTIL"
echo "  DType:       $DTYPE"
echo "  System Prompt: ${SYSTEM_PROMPT:0:100}..."


exec uv run -m vllm.entrypoints.openai.api_server \
  --host "$HOST" \
  --port "$PORT" \
  --model "$MODEL_SRC" \
  --served-model-name "$MODEL_NAME" \
  --download-dir "$HF_CACHE_DIR" \
  --max-model-len "$MAX_LEN" \
  --tensor-parallel-size "$TP_SIZE" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --dtype "$DTYPE" \
  --system-prompt "$SYSTEM_PROMPT"


