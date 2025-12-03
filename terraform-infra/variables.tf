variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "lakehouse-poc"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "ramses"
}

variable "owner" {
  description = "Owner/creator of the resources"
  type        = string
  default     = "lakehouse-team"
}

# DMS Source Database Configuration
variable "source_db_host" {
  description = "Django PostgreSQL host (public IP or hostname)"
  type        = string
}

variable "source_db_port" {
  description = "Django PostgreSQL port"
  type        = number
  default     = 5432
}

variable "source_db_name" {
  description = "Django PostgreSQL database name"
  type        = string
  default     = "lakehouse_poc"
}

variable "source_db_username" {
  description = "Django PostgreSQL username"
  type        = string
  default     = "lakehouse_user"
  sensitive   = true
}

variable "source_db_password" {
  description = "Django PostgreSQL password"
  type        = string
  sensitive   = true
}

# DMS Configuration
variable "dms_instance_class" {
  description = "DMS replication instance class"
  type        = string
  default     = "dms.t3.medium"
}

variable "dms_allocated_storage" {
  description = "DMS replication instance storage in GB"
  type        = number
  default     = 100
}

# Glue Configuration
variable "glue_worker_type" {
  description = "Glue job worker type"
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Number of Glue workers"
  type        = number
  default     = 2
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
