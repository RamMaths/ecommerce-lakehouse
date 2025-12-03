variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "bronze_bucket_name" {
  description = "Bronze layer bucket name"
  type        = string
}

variable "silver_bucket_name" {
  description = "Silver layer bucket name"
  type        = string
}

variable "gold_bucket_name" {
  description = "Gold layer bucket name"
  type        = string
}

variable "scripts_bucket_name" {
  description = "Scripts bucket name"
  type        = string
}

variable "glue_role_arn" {
  description = "Glue service role ARN"
  type        = string
}

variable "worker_type" {
  description = "Glue worker type"
  type        = string
}

variable "number_of_workers" {
  description = "Number of Glue workers"
  type        = number
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
