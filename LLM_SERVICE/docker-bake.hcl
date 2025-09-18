variable "REGISTRY" { default = "ghcr.io/your-org" }
variable "PROJECT"  { default = "theorem" }
variable "VERSION"  { default = "1.0.0" }
variable "SHA"      { default = "dev" }
variable "PLATFORMS_GPU" { default = ["linux/amd64"] }
variable "PLATFORMS_CPU" { default = ["linux/amd64"] }


group "default" {
  targets = ["qdrant", "embedder", "vllm_math"]
}


target "common" {
  pull       = true
  cache-to   = ["type=registry,ref=${REGISTRY}/${PROJECT}/buildcache:all,mode=max"]
  cache-from = ["type=registry,ref=${REGISTRY}/${PROJECT}/buildcache:all"]
}


target "qdrant" {
  inherits   = ["common"]
  context    = "./qdrant"
  dockerfile = "dockerfile"
  platforms  = var.PLATFORMS_CPU
  tags       = [
    "${REGISTRY}/${PROJECT}/qdrant:${VERSION}",
    "${REGISTRY}/${PROJECT}/qdrant:${SHA}",
  ]
}


target "embedder" {
  inherits   = ["common"]
  context    = "./embedder"
  dockerfile = "dockerfile"
  platforms  = var.PLATFORMS_CPU
  tags       = [
    "${REGISTRY}/${PROJECT}/embedder:${VERSION}",
    "${REGISTRY}/${PROJECT}/embedder:${SHA}",
  ]
}


target "vllm_math" {
  inherits   = ["common"]
  context    = "./vllm_math"
  dockerfile = "dockerfile"
  platforms  = var.PLATFORMS_GPU
  tags       = [
    "${REGISTRY}/${PROJECT}/vllm_math:${VERSION}",
    "${REGISTRY}/${PROJECT}/vllm_math:${SHA}",
  ]
}


