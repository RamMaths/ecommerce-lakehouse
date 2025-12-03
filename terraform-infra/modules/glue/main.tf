# AWS Glue Data Catalog and ETL Jobs

# Glue Databases
resource "aws_glue_catalog_database" "bronze" {
  name        = "${var.project_name}_${var.environment}_bronze"
  description = "Bronze layer - raw data from DMS"

  tags = merge(var.tags, {
    Layer = "Bronze"
  })
}

resource "aws_glue_catalog_database" "silver" {
  name        = "${var.project_name}_${var.environment}_silver"
  description = "Silver layer - cleaned and standardized data"

  tags = merge(var.tags, {
    Layer = "Silver"
  })
}

resource "aws_glue_catalog_database" "gold" {
  name        = "${var.project_name}_${var.environment}_gold"
  description = "Gold layer - aggregated business-ready data"

  tags = merge(var.tags, {
    Layer = "Gold"
  })
}

# Glue Crawler for Bronze Layer
resource "aws_glue_crawler" "bronze" {
  name          = "${var.project_name}-${var.environment}-bronze-crawler"
  role          = var.glue_role_arn
  database_name = aws_glue_catalog_database.bronze.name

  s3_target {
    path = "s3://${var.bronze_bucket_name}/dms-data/"
  }

  schedule = "cron(0 * * * ? *)"  # Run hourly

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable"
      }
    }
  })

  tags = var.tags
}

# Glue Crawler for Silver Layer
resource "aws_glue_crawler" "silver" {
  name          = "${var.project_name}-${var.environment}-silver-crawler"
  role          = var.glue_role_arn
  database_name = aws_glue_catalog_database.silver.name

  s3_target {
    path = "s3://${var.silver_bucket_name}/"
  }

  schedule = "cron(0 0 * * ? *)"  # Run daily

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  tags = var.tags
}

# Glue Crawler for Gold Layer
resource "aws_glue_crawler" "gold" {
  name          = "${var.project_name}-${var.environment}-gold-crawler"
  role          = var.glue_role_arn
  database_name = aws_glue_catalog_database.gold.name

  s3_target {
    path = "s3://${var.gold_bucket_name}/"
  }

  schedule = "cron(0 0 * * ? *)"  # Run daily

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  tags = var.tags
}
