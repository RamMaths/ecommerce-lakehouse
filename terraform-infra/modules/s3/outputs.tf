output "bronze_bucket_name" {
  description = "Bronze layer bucket name"
  value       = aws_s3_bucket.bronze.id
}

output "bronze_bucket_arn" {
  description = "Bronze layer bucket ARN"
  value       = aws_s3_bucket.bronze.arn
}

output "silver_bucket_name" {
  description = "Silver layer bucket name"
  value       = aws_s3_bucket.silver.id
}

output "silver_bucket_arn" {
  description = "Silver layer bucket ARN"
  value       = aws_s3_bucket.silver.arn
}

output "gold_bucket_name" {
  description = "Gold layer bucket name"
  value       = aws_s3_bucket.gold.id
}

output "gold_bucket_arn" {
  description = "Gold layer bucket ARN"
  value       = aws_s3_bucket.gold.arn
}

output "scripts_bucket_name" {
  description = "Scripts bucket name"
  value       = aws_s3_bucket.scripts.id
}

output "scripts_bucket_arn" {
  description = "Scripts bucket ARN"
  value       = aws_s3_bucket.scripts.arn
}

output "athena_bucket_name" {
  description = "Athena results bucket name"
  value       = aws_s3_bucket.athena.id
}

output "athena_bucket_arn" {
  description = "Athena results bucket ARN"
  value       = aws_s3_bucket.athena.arn
}
