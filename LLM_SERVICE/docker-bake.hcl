variable "REGISTRY" { default = "ghcr.io/your-org" }
variable "PROJECT"  { default = "theorem" }
variable "VERSION"  { default = "1.0.0" }
variable "SHA"      { default = "dev" }

variable "PLATFORMS" { default = ["linux/amd64"] } 

group "default" { targets = ["llm_gateway","vllm"] }


target "common" {
  platforms   = var.PLATFORMS
  pull        = true
  cache-to    = ["type=registry,ref=${REGISTRY}/${PROJECT}/buildcache:all,mode=max"]
  cache-from  = ["type=registry,ref=${REGISTRY}/${PROJECT}/buildcache:all"]
}


target "llm_gateway" {
  inherits   = ["common"]
  context    = "./llm_gateway"
  dockerfile = "dockerfile"
  tags       = ["${REGISTRY}/${PROJECT}/llm_gateway:${VERSION}", "${REGISTRY}/${PROJECT}/llm_gateway:${SHA}"]
}

target "vllm" {
  inherits   = ["common"]
  context    = "./vllm"
  dockerfile = "dockerfile"
  tags       = ["${REGISTRY}/${PROJECT}/vllm:${VERSION}", "${REGISTRY}/${PROJECT}/vllm:${SHA}"]
}


