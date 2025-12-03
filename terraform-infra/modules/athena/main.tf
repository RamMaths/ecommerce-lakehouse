# Amazon Athena configuration for querying data lake

# Athena Workgroup
resource "aws_athena_workgroup" "main" {
  name = "${var.project_name}-${var.environment}-workgroup"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.results_bucket_name}/query-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }

  tags = var.tags
}

# Named Query - Revenue by Tenant
resource "aws_athena_named_query" "revenue_by_tenant" {
  name      = "${var.project_name}-revenue-by-tenant"
  workgroup = aws_athena_workgroup.main.id
  database  = var.gold_database
  query     = <<-SQL
    SELECT 
      t.name as tenant_name,
      COUNT(DISTINCT o.id) as order_count,
      ROUND(SUM(o.total), 2) as total_revenue,
      ROUND(AVG(o.total), 2) as avg_order_value
    FROM ${var.bronze_database}.core_tenant t
    LEFT JOIN ${var.bronze_database}.core_order o 
      ON o.tenant_id = t.id
    WHERE o.status = 'completed'
    GROUP BY t.name
    ORDER BY total_revenue DESC;
  SQL

  description = "Total revenue by tenant from completed orders"
}

# Named Query - Customer Acquisition
resource "aws_athena_named_query" "customer_acquisition" {
  name      = "${var.project_name}-customer-acquisition"
  workgroup = aws_athena_workgroup.main.id
  database  = var.bronze_database
  query     = <<-SQL
    SELECT 
      DATE_TRUNC('month', created_at) as month,
      COUNT(*) as new_customers
    FROM ${var.bronze_database}.core_customer
    GROUP BY DATE_TRUNC('month', created_at)
    ORDER BY month;
  SQL

  description = "Customer acquisition trends by month"
}

# Named Query - Event Funnel
resource "aws_athena_named_query" "event_funnel" {
  name      = "${var.project_name}-event-funnel"
  workgroup = aws_athena_workgroup.main.id
  database  = var.bronze_database
  query     = <<-SQL
    SELECT 
      event_type,
      COUNT(*) as event_count,
      COUNT(DISTINCT customer_id) as unique_customers,
      COUNT(DISTINCT session_id) as unique_sessions
    FROM ${var.bronze_database}.core_event
    GROUP BY event_type
    ORDER BY event_count DESC;
  SQL

  description = "Event funnel analysis showing conversion metrics"
}

# Named Query - MRR by Tenant
resource "aws_athena_named_query" "mrr_by_tenant" {
  name      = "${var.project_name}-mrr-by-tenant"
  workgroup = aws_athena_workgroup.main.id
  database  = var.bronze_database
  query     = <<-SQL
    SELECT 
      t.name as tenant_name,
      COUNT(s.id) as active_subscriptions,
      ROUND(SUM(s.monthly_amount), 2) as mrr,
      ROUND(AVG(s.monthly_amount), 2) as avg_subscription_value
    FROM ${var.bronze_database}.core_tenant t
    LEFT JOIN ${var.bronze_database}.core_subscription s 
      ON s.tenant_id = t.id
    WHERE s.status = 'active'
    GROUP BY t.name
    ORDER BY mrr DESC;
  SQL

  description = "Monthly Recurring Revenue (MRR) by tenant"
}

# Named Query - Top Products
resource "aws_athena_named_query" "top_products" {
  name      = "${var.project_name}-top-products"
  workgroup = aws_athena_workgroup.main.id
  database  = var.bronze_database
  query     = <<-SQL
    SELECT 
      p.name as product_name,
      p.category,
      COUNT(oi.id) as times_ordered,
      SUM(oi.quantity) as total_quantity,
      ROUND(SUM(oi.total), 2) as total_revenue
    FROM ${var.bronze_database}.core_product p
    JOIN ${var.bronze_database}.core_orderitem oi 
      ON oi.product_id = p.id
    JOIN ${var.bronze_database}.core_order o 
      ON o.id = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY p.name, p.category
    ORDER BY total_revenue DESC
    LIMIT 20;
  SQL

  description = "Top 20 products by revenue"
}
