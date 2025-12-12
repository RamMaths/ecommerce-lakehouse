"""
Glue ETL Job: Create Gold Layer Customer Metrics
Purpose: Customer analytics including acquisition, retention, and LTV
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, sum as spark_sum, count, avg, round as spark_round, date_trunc, current_timestamp, min as spark_min, max as spark_max, datediff

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("Creating Gold Layer Customer Metrics...")

# Read Silver layer tables
tenants_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="tenant"
).toDF()

customers_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="customer"
).toDF()

orders_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="order"
).toDF()

subscriptions_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="subscription"
).toDF()

# Customer Lifetime Value by Tenant
customer_ltv = orders_df \
    .filter(col("status") == "completed") \
    .groupBy("tenant_id", "customer_id") \
    .agg(
        count("id").alias("total_orders"),
        spark_round(spark_sum("total"), 2).alias("lifetime_value"),
        spark_round(avg("total"), 2).alias("avg_order_value"),
        spark_min("order_date").alias("first_order_date"),
        spark_max("order_date").alias("last_order_date")
    ) \
    .join(customers_df.select("id", "email", "tenant_id"), col("customer_id") == customers_df.id) \
    .join(tenants_df.select("id", "name"), col("tenant_id") == tenants_df.id) \
    .select(
        col("tenant_id"),
        col("name").alias("tenant_name"),
        col("customer_id"),
        col("email"),
        col("total_orders"),
        col("lifetime_value"),
        col("avg_order_value"),
        col("first_order_date"),
        col("last_order_date"),
        datediff(col("last_order_date"), col("first_order_date")).alias("customer_age_days"),
        current_timestamp().alias("processed_at")
    )

# Customer Acquisition by Month
customer_acquisition = customers_df \
    .withColumn("month", date_trunc("month", col("created_at"))) \
    .groupBy("tenant_id", "month") \
    .agg(
        count("id").alias("new_customers")
    ) \
    .join(tenants_df.select("id", "name"), col("tenant_id") == tenants_df.id) \
    .select(
        col("tenant_id"),
        col("name").alias("tenant_name"),
        col("month"),
        col("new_customers"),
        current_timestamp().alias("processed_at")
    )

# Active Subscription Metrics
active_subscriptions = subscriptions_df \
    .filter(col("status") == "active") \
    .groupBy("tenant_id") \
    .agg(
        count("id").alias("active_subscription_count"),
        spark_round(spark_sum("price"), 2).alias("monthly_recurring_revenue")
    ) \
    .join(tenants_df.select("id", "name"), col("tenant_id") == tenants_df.id) \
    .select(
        col("tenant_id"),
        col("name").alias("tenant_name"),
        col("active_subscription_count"),
        col("monthly_recurring_revenue"),
        current_timestamp().alias("processed_at")
    )

print(f"Customer LTV records: {customer_ltv.count()}")
print(f"Customer acquisition records: {customer_acquisition.count()}")
print(f"Active subscription records: {active_subscriptions.count()}")

# Write to Gold layer
customer_ltv.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/customer_ltv/")

customer_acquisition.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .partitionBy("month") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/customer_acquisition/")

active_subscriptions.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/active_subscriptions/")

print("Gold layer customer metrics created successfully!")
job.commit()
