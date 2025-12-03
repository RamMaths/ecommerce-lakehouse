output "dms_service_role_arn" {
  description = "ARN of DMS service role"
  value       = aws_iam_role.dms_service_role.arn
}

output "dms_s3_role_arn" {
  description = "ARN of DMS S3 target role"
  value       = aws_iam_role.dms_s3_role.arn
}

output "glue_role_arn" {
  description = "ARN of Glue service role"
  value       = aws_iam_role.glue_role.arn
}

output "athena_user_role_arn" {
  description = "ARN of Athena user role"
  value       = aws_iam_role.athena_user_role.arn
}
