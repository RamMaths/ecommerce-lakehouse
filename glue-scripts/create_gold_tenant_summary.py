"""
Glue ETL Job: Create Gold Layer Tenant Summary
Purpose: Basic tenant metrics using available Silver data
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, count, current_timestamp

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("Creating Gold Layer Tenant Summary...")

# Read Silver layer tables
tenants_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse-poc_dev_silver",
    table_name="tenant"
).toDF()

customers_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse-poc_dev_silver",
    table_name="customer"
).toDF()

print(f"Tenants: {tenants_df.count()}")
print(f"Customers: {customers_df.count()}")

# Create tenant summary with customer counts
tenant_summary = tenants_df \
    .join(
        customers_df.groupBy("tenant_id").agg(count("id").alias("customer_count")),
        tenants_df.id == customers_df.tenant_id,
        "left"
    ) \
    .select(
        col("id").alias("tenant_id"),
        col("name").alias("tenant_name"),
        col("slug").alias("tenant_slug"),
        col("is_active"),
        col("customer_count"),
        current_timestamp().alias("processed_at")
    ) \
    .fillna(0, ["customer_count"])

print(f"Tenant summary records: {tenant_summary.count()}")

# Show sample data
tenant_summary.show(10, False)

# Write to Gold layer
tenant_summary.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/tenant_summary/")

print("Gold layer tenant summary created successfully!")
job.commit()