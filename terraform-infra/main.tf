# Main Terraform configuration for Lakehouse POC

# Get current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  account_id    = data.aws_caller_identity.current.account_id
  region        = data.aws_region.current.name
  name_prefix   = "${var.project_name}-${var.environment}"
  resource_tags = merge(var.additional_tags, {
    Project     = var.project_name
    Environment = var.environment
  })
}

# IAM Module - Create roles and policies first
module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  account_id   = local.account_id
  region       = local.region
  tags         = local.resource_tags
}

# S3 Module - Create buckets for data lake
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
  account_id   = local.account_id
  suffix       = random_string.suffix.result
  tags         = local.resource_tags
}

# DMS Module - Database replication
module "dms" {
  source = "./modules/dms"

  project_name           = var.project_name
  environment            = var.environment
  source_db_host         = var.source_db_host
  source_db_port         = var.source_db_port
  source_db_name         = var.source_db_name
  source_db_username     = var.source_db_username
  source_db_password     = var.source_db_password
  target_bucket_arn      = module.s3.bronze_bucket_arn
  target_bucket_name     = module.s3.bronze_bucket_name
  dms_instance_class     = var.dms_instance_class
  dms_allocated_storage  = var.dms_allocated_storage
  dms_service_role_arn   = module.iam.dms_service_role_arn
  tags                   = local.resource_tags

  depends_on = [module.iam, module.s3]
}

# Glue Module - Data catalog and ETL
module "glue" {
  source = "./modules/glue"

  project_name        = var.project_name
  environment         = var.environment
  bronze_bucket_name  = module.s3.bronze_bucket_name
  silver_bucket_name  = module.s3.silver_bucket_name
  gold_bucket_name    = module.s3.gold_bucket_name
  scripts_bucket_name = module.s3.scripts_bucket_name
  glue_role_arn       = module.iam.glue_role_arn
  worker_type         = var.glue_worker_type
  number_of_workers   = var.glue_number_of_workers
  tags                = local.resource_tags

  depends_on = [module.iam, module.s3]
}

# Athena Module - Query engine
module "athena" {
  source = "./modules/athena"

  project_name        = var.project_name
  environment         = var.environment
  results_bucket_name = module.s3.athena_bucket_name
  bronze_database     = module.glue.bronze_database_name
  silver_database     = module.glue.silver_database_name
  gold_database       = module.glue.gold_database_name
  tags                = local.resource_tags

  depends_on = [module.glue]
}
