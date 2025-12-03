variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "source_db_host" {
  description = "Source PostgreSQL host"
  type        = string
}

variable "source_db_port" {
  description = "Source PostgreSQL port"
  type        = number
}

variable "source_db_name" {
  description = "Source PostgreSQL database name"
  type        = string
}

variable "source_db_username" {
  description = "Source PostgreSQL username"
  type        = string
  sensitive   = true
}

variable "source_db_password" {
  description = "Source PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "target_bucket_name" {
  description = "Target S3 bucket name"
  type        = string
}

variable "target_bucket_arn" {
  description = "Target S3 bucket ARN"
  type        = string
}

variable "dms_instance_class" {
  description = "DMS replication instance class"
  type        = string
}

variable "dms_allocated_storage" {
  description = "DMS allocated storage in GB"
  type        = number
}

variable "dms_service_role_arn" {
  description = "DMS service role ARN"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
