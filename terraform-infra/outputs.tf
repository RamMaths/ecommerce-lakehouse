output "s3_buckets" {
  description = "S3 bucket names for data lake layers"
  value = {
    bronze  = module.s3.bronze_bucket_name
    silver  = module.s3.silver_bucket_name
    gold    = module.s3.gold_bucket_name
    scripts = module.s3.scripts_bucket_name
    athena  = module.s3.athena_bucket_name
  }
}

output "glue_databases" {
  description = "Glue Data Catalog database names"
  value = {
    bronze = module.glue.bronze_database_name
    silver = module.glue.silver_database_name
    gold   = module.glue.gold_database_name
  }
}

output "dms_replication_instance_endpoint" {
  description = "DMS replication instance endpoint"
  value       = module.dms.replication_instance_endpoint
}

output "athena_workgroup" {
  description = "Athena workgroup name"
  value       = module.athena.workgroup_name
}

output "next_steps" {
  description = "Next steps after infrastructure deployment"
  value = <<-EOT
    
    ✅ Infrastructure deployed successfully!
    
    Next steps:
    1. Start DMS replication task: ${module.dms.replication_task_arn}
    2. Run Glue crawlers to discover Bronze data
    3. Execute Glue ETL jobs for Silver layer
    4. Query data in Athena workgroup: ${module.athena.workgroup_name}
    
    S3 Buckets:
    - Bronze: s3://${module.s3.bronze_bucket_name}
    - Silver: s3://${module.s3.silver_bucket_name}
    - Gold: s3://${module.s3.gold_bucket_name}
    
    Glue Databases:
    - Bronze: ${module.glue.bronze_database_name}
    - Silver: ${module.glue.silver_database_name}
    - Gold: ${module.glue.gold_database_name}
  EOT
}
