variable "project_id" {
  description = "Existing Google Cloud project in which resources are created."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid Google Cloud project ID."
  }
}

variable "region" {
  description = "Google Cloud region for regional resources."
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Environment label used in resource names."
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "cluster_name" {
  description = "GKE cluster name."
  type        = string
  default     = "scip"
}

variable "network_cidr" {
  description = "Primary subnet CIDR used by GKE nodes."
  type        = string
  default     = "10.20.0.0/20"
}

variable "pods_cidr" {
  description = "Secondary subnet CIDR used by Kubernetes Pods."
  type        = string
  default     = "10.24.0.0/14"
}

variable "services_cidr" {
  description = "Secondary subnet CIDR used by Kubernetes Services."
  type        = string
  default     = "10.28.0.0/20"
}

variable "master_ipv4_cidr" {
  description = "RFC1918 /28 used by the GKE control plane."
  type        = string
  default     = "172.16.0.0/28"
}

variable "master_authorized_networks" {
  description = "Trusted operator networks allowed to reach the public control-plane endpoint."
  type = list(object({
    cidr_block   = string
    display_name = string
  }))

  validation {
    condition     = length(var.master_authorized_networks) > 0
    error_message = "Provide at least one explicit trusted control-plane CIDR."
  }
}

variable "node_machine_type" {
  description = "Machine type for the separately managed GKE node pool."
  type        = string
  default     = "e2-standard-4"
}

variable "node_min_count" {
  description = "Minimum node count per zone."
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Maximum node count per zone."
  type        = number
  default     = 3
}

variable "database_tier" {
  description = "Cloud SQL machine tier."
  type        = string
  default     = "db-custom-2-7680"
}

variable "labels" {
  description = "Additional labels applied to supported resources."
  type        = map(string)
  default     = {}
}
