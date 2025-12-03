output "replication_instance_arn" {
  description = "ARN of DMS replication instance"
  value       = aws_dms_replication_instance.main.replication_instance_arn
}

output "replication_instance_endpoint" {
  description = "Endpoint of DMS replication instance"
  value       = aws_dms_replication_instance.main.replication_instance_public_ips
}

output "source_endpoint_arn" {
  description = "ARN of source endpoint"
  value       = aws_dms_endpoint.source.endpoint_arn
}

output "target_endpoint_arn" {
  description = "ARN of target endpoint"
  value       = aws_dms_endpoint.target.endpoint_arn
}

output "replication_task_arn" {
  description = "ARN of replication task"
  value       = aws_dms_replication_task.main.replication_task_arn
}

output "next_steps" {
  description = "Next steps after DMS deployment"
  value = <<-EOT
    DMS Configuration Complete!
    
    To start replication:
    1. Ensure Django PostgreSQL is accessible from AWS
    2. Test source endpoint connection in AWS Console
    3. Start replication task: ${aws_dms_replication_task.main.replication_task_id}
    
    Monitor replication:
    aws dms describe-replication-tasks --filters Name=replication-task-arn,Values=${aws_dms_replication_task.main.replication_task_arn}
  EOT
}
