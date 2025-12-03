output "bronze_database_name" {
  description = "Bronze database name"
  value       = aws_glue_catalog_database.bronze.name
}

output "silver_database_name" {
  description = "Silver database name"
  value       = aws_glue_catalog_database.silver.name
}

output "gold_database_name" {
  description = "Gold database name"
  value       = aws_glue_catalog_database.gold.name
}

output "bronze_crawler_name" {
  description = "Bronze crawler name"
  value       = aws_glue_crawler.bronze.name
}

output "silver_crawler_name" {
  description = "Silver crawler name"
  value       = aws_glue_crawler.silver.name
}

output "gold_crawler_name" {
  description = "Gold crawler name"
  value       = aws_glue_crawler.gold.name
}
