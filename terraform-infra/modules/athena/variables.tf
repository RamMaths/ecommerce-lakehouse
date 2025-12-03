variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "results_bucket_name" {
  description = "S3 bucket for Athena query results"
  type        = string
}

variable "bronze_database" {
  description = "Bronze Glue database name"
  type        = string
}

variable "silver_database" {
  description = "Silver Glue database name"
  type        = string
}

variable "gold_database" {
  description = "Gold Glue database name"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
