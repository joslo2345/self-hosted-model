variable "subscription_id" {
  type = string
}

variable "cluster_name" {
  type        = string
  default     = "incident-assistant-aks"
  description = "Project A's AKS cluster (its `aks_name` output)."
}

variable "cluster_resource_group" {
  type        = string
  default     = "incident-assistant-rg"
  description = "Project A's resource group (its `resource_group` output)."
}

variable "gpu_vm_size" {
  type        = string
  default     = "Standard_NC24ads_A100_v4" # 1x A100 80 GB: bf16 or FP8 Qwen3.5-9B with room for KV cache
  description = "Needs a GPU with bf16/FP8 support (Ampere or newer); T4s can't run the bf16 weights."
}

variable "gpu_max_nodes" {
  type    = number
  default = 1
}

variable "spot" {
  type        = bool
  default     = true
  description = "Spot VMs cost far less but can be evicted; the model reloads from the weight cache."
}

variable "spot_max_price" {
  type        = number
  default     = -1 # pay up to the on-demand price; eviction then only happens for capacity
  description = "USD per hour, or -1 for the on-demand price cap."
}

variable "tags" {
  type    = map(string)
  default = { project = "self-hosted-model", package = "b2" }
}
