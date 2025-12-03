output "workgroup_name" {
  description = "Athena workgroup name"
  value       = aws_athena_workgroup.main.name
}

output "workgroup_arn" {
  description = "Athena workgroup ARN"
  value       = aws_athena_workgroup.main.arn
}

output "named_queries" {
  description = "Named query IDs"
  value = {
    revenue_by_tenant      = aws_athena_named_query.revenue_by_tenant.id
    customer_acquisition   = aws_athena_named_query.customer_acquisition.id
    event_funnel          = aws_athena_named_query.event_funnel.id
    mrr_by_tenant         = aws_athena_named_query.mrr_by_tenant.id
    top_products          = aws_athena_named_query.top_products.id
  }
}
