# AWS DMS configuration for PostgreSQL to S3 replication

# DMS Subnet Group (using default VPC for simplicity)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_dms_replication_subnet_group" "main" {
  replication_subnet_group_id          = "${var.project_name}-${var.environment}-dms-subnet"
  replication_subnet_group_description = "DMS replication subnet group"
  subnet_ids                           = data.aws_subnets.default.ids

  tags = var.tags
}

# DMS Replication Instance
resource "aws_dms_replication_instance" "main" {
  replication_instance_id   = "${var.project_name}-${var.environment}-dms"
  replication_instance_class = var.dms_instance_class
  allocated_storage          = var.dms_allocated_storage
  
  engine_version             = "3.5.2"
  multi_az                   = false
  publicly_accessible        = true  # Required to connect to external PostgreSQL
  
  replication_subnet_group_id = aws_dms_replication_subnet_group.main.id
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-dms-instance"
  })
}

# Source Endpoint - PostgreSQL (Django)
resource "aws_dms_endpoint" "source" {
  endpoint_id   = "${var.project_name}-${var.environment}-source-postgres"
  endpoint_type = "source"
  engine_name   = "postgres"

  server_name = var.source_db_host
  port        = var.source_db_port
  database_name = var.source_db_name
  username    = var.source_db_username
  password    = var.source_db_password

  ssl_mode = "none"  # Change to "require" if using SSL

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-source-endpoint"
  })
}

# Target Endpoint - S3 (Bronze Layer)
resource "aws_dms_endpoint" "target" {
  endpoint_id   = "${var.project_name}-${var.environment}-target-s3"
  endpoint_type = "target"
  engine_name   = "s3"

  s3_settings {
    bucket_name             = var.target_bucket_name
    bucket_folder           = "dms-data"
    compression_type        = "GZIP"
    data_format             = "parquet"
    parquet_version         = "parquet-2-0"
    
    # Partitioning
    date_partition_enabled  = true
    date_partition_sequence = "YYYYMMDD"
    
    service_access_role_arn = var.dms_service_role_arn
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-target-endpoint"
  })
}

# DMS Replication Task
resource "aws_dms_replication_task" "main" {
  replication_task_id       = "${var.project_name}-${var.environment}-task"
  migration_type            = "full-load-and-cdc"
  replication_instance_arn  = aws_dms_replication_instance.main.replication_instance_arn
  source_endpoint_arn       = aws_dms_endpoint.source.endpoint_arn
  target_endpoint_arn       = aws_dms_endpoint.target.endpoint_arn

  table_mappings = jsonencode({
    rules = [
      {
        rule-type = "selection"
        rule-id   = "1"
        rule-name = "include-all-core-tables"
        object-locator = {
          schema-name = "public"
          table-name  = "core_%"
        }
        rule-action = "include"
      },
      {
        rule-type = "selection"
        rule-id   = "2"
        rule-name = "include-auth-tables"
        object-locator = {
          schema-name = "public"
          table-name  = "auth_%"
        }
        rule-action = "include"
      },
      {
        rule-type = "selection"
        rule-id   = "3"
        rule-name = "include-django-tables"
        object-locator = {
          schema-name = "public"
          table-name  = "django_%"
        }
        rule-action = "include"
      }
    ]
  })

  replication_task_settings = jsonencode({
    TargetMetadata = {
      TargetSchema = ""
      SupportLobs  = true
      FullLobMode  = false
      LobChunkSize = 64
      LimitedSizeLobMode = true
      LobMaxSize   = 32
    }
    FullLoadSettings = {
      TargetTablePrepMode = "DROP_AND_CREATE"
      MaxFullLoadSubTasks = 8
    }
    Logging = {
      EnableLogging = true
      LogComponents = [
        {
          Id       = "TRANSFORMATION"
          Severity = "LOGGER_SEVERITY_DEFAULT"
        },
        {
          Id       = "SOURCE_UNLOAD"
          Severity = "LOGGER_SEVERITY_DEFAULT"
        },
        {
          Id       = "TARGET_LOAD"
          Severity = "LOGGER_SEVERITY_DEFAULT"
        }
      ]
    }
    ChangeProcessingDdlHandlingPolicy = {
      HandleSourceTableDropped   = true
      HandleSourceTableTruncated = true
      HandleSourceTableAltered   = true
    }
    ChangeProcessingTuning = {
      BatchApplyPreserveTransaction = true
      BatchApplyTimeoutMin          = 1
      BatchApplyTimeoutMax          = 30
      BatchApplyMemoryLimit         = 500
      BatchSplitSize                = 0
      MinTransactionSize            = 1000
      CommitTimeout                 = 1
      MemoryLimitTotal              = 1024
      MemoryKeepTime                = 60
      StatementCacheSize            = 50
    }
  })

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-replication-task"
  })

  # Don't start automatically - we'll start it manually after verification
  start_replication_task = false

  depends_on = [
    aws_dms_replication_instance.main,
    aws_dms_endpoint.source,
    aws_dms_endpoint.target
  ]
}
