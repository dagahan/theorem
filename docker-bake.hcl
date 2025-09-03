variable "REGISTRY" { default = "ghcr.io/your-org" }
variable "PROJECT"  { default = "theorem" }
variable "VERSION"  { default = "1.0.0" }
variable "SHA"      { default = "dev" }

variable "PLATFORMS" { default = ["linux/amd64","linux/arm64"] }

group "default" { targets = ["gateway","vllm"] }


target "common" {
  platforms   = var.PLATFORMS
  pull        = true
  cache-to    = ["type=registry,ref=${REGISTRY}/${PROJECT}/buildcache:all,mode=max"]
  cache-from  = ["type=registry,ref=${REGISTRY}/${PROJECT}/buildcache:all"]
}


target "gateway" {
  inherits   = ["common"]
  context    = "./gateway"
  dockerfile = "dockerfile"
  tags       = ["${REGISTRY}/${PROJECT}/gateway:${VERSION}", "${REGISTRY}/${PROJECT}/gateway:${SHA}"]
}

target "vllm" {
  inherits   = ["common"]
  context    = "./vllm"
  dockerfile = "dockerfile"
  tags       = ["${REGISTRY}/${PROJECT}/vllm:${VERSION}", "${REGISTRY}/${PROJECT}/vllm:${SHA}"]
}


