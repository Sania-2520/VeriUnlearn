variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "veriunlearn"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "cluster_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.29"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "cluster_endpoint_public_access" {
  description = "Enable public access to EKS endpoint"
  type        = bool
  default     = false
}

variable "standard_instance_types" {
  description = "Instance types for standard node group"
  type        = list(string)
  default     = ["m6i.xlarge", "m6i.2xlarge"]
}

variable "standard_capacity_type" {
  description = "Capacity type for standard nodes"
  type        = string
  default     = "ON_DEMAND"
}

variable "standard_desired_size" {
  description = "Desired number of standard nodes"
  type        = number
  default     = 3
}

variable "standard_min_size" {
  description = "Minimum number of standard nodes"
  type        = number
  default     = 2
}

variable "standard_max_size" {
  description = "Maximum number of standard nodes"
  type        = number
  default     = 10
}

variable "gpu_instance_types" {
  description = "Instance types for GPU node group"
  type        = list(string)
  default     = ["p3.2xlarge", "p3.8xlarge"]
}

variable "gpu_desired_size" {
  description = "Desired number of GPU nodes"
  type        = number
  default     = 2
}

variable "gpu_min_size" {
  description = "Minimum number of GPU nodes"
  type        = number
  default     = 1
}

variable "gpu_max_size" {
  description = "Maximum number of GPU nodes"
  type        = number
  default     = 5
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
