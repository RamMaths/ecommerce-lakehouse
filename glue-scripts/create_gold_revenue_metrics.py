"""
Glue ETL Job: Create Gold Layer Revenue Metrics
Purpose: Aggregate revenue data by tenant and time periods
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, sum as spark_sum, count, avg, round as spark_round, date_trunc, current_timestamp

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("Creating Gold Layer Revenue Metrics...")

# Read Silver layer tables
tenants_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="tenant"
).toDF()

orders_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="order"
).toDF()

customers_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="customer"
).toDF()

# Revenue by Tenant (Monthly)
revenue_by_tenant_monthly = orders_df \
    .filter(col("status") == "completed") \
    .withColumn("month", date_trunc("month", col("order_date"))) \
    .groupBy("tenant_id", "month") \
    .agg(
        count("id").alias("order_count"),
        spark_round(spark_sum("total"), 2).alias("total_revenue"),
        spark_round(avg("total"), 2).alias("avg_order_value"),
        count("customer_id").alias("unique_customers")
    ) \
    .join(tenants_df.select("id", "name"), col("tenant_id") == tenants_df.id) \
    .select(
        col("tenant_id"),
        col("name").alias("tenant_name"),
        col("month"),
        col("order_count"),
        col("total_revenue"),
        col("avg_order_value"),
        col("unique_customers"),
        current_timestamp().alias("processed_at")
    )

# Revenue by Tenant (Overall)
revenue_by_tenant_total = orders_df \
    .filter(col("status") == "completed") \
    .groupBy("tenant_id") \
    .agg(
        count("id").alias("total_orders"),
        spark_round(spark_sum("total"), 2).alias("total_revenue"),
        spark_round(avg("total"), 2).alias("avg_order_value")
    ) \
    .join(tenants_df.select("id", "name", "plan_type"), col("tenant_id") == tenants_df.id) \
    .join(
        customers_df.groupBy("tenant_id").agg(count("id").alias("total_customers")),
        "tenant_id"
    ) \
    .select(
        col("tenant_id"),
        col("name").alias("tenant_name"),
        col("plan_type"),
        col("total_customers"),
        col("total_orders"),
        col("total_revenue"),
        col("avg_order_value"),
        spark_round(col("total_revenue") / col("total_customers"), 2).alias("revenue_per_customer"),
        current_timestamp().alias("processed_at")
    )

print(f"Monthly revenue records: {revenue_by_tenant_monthly.count()}")
print(f"Total revenue records: {revenue_by_tenant_total.count()}")

# Write to Gold layer
revenue_by_tenant_monthly.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .partitionBy("month") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/revenue_by_tenant_monthly/")

revenue_by_tenant_total.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/revenue_by_tenant_total/")

print("Gold layer revenue metrics created successfully!")
job.commit()
