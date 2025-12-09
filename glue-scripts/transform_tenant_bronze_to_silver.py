"""
Glue ETL Job: Transform Tenant from Bronze to Silver
Purpose: Clean and standardize tenant data, remove DMS metadata
Input: s3://lakehouse-poc-dev-bronze-ti4jmrk8/dms-data/public/core_tenant/
Output: s3://lakehouse-poc-dev-silver-ti4jmrk8/tenant/
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, from_json, to_timestamp, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

# Initialize Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("Starting Tenant Bronze to Silver transformation...")

# Read from Bronze layer (Glue Catalog)
print("Reading from Bronze layer...")
bronze_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse-poc_dev_bronze",
    table_name="core_tenant"
).toDF()

print(f"Bronze records read: {bronze_df.count()}")

# Column mapping from DMS CSV format
# col0 = operation (I/U/D)
# col1 = dms_timestamp
# col2 = id (UUID)
# col3 = name
# col4 = slug
# col5 = domain
# col6 = is_active
# col7 = settings (struct)
# col8 = created_at
# col9 = updated_at

# Define schema for settings JSON
settings_schema = StructType([
    StructField("plan_type", StringType(), True),
    StructField("max_users", IntegerType(), True),
    StructField("features", ArrayType(StringType()), True)
])

# Transform: Map columns and filter
print("Transforming data...")
silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .withColumn("settings_parsed", from_json(col("col7"), settings_schema)) \
    .select(
        col("col2").alias("id"),
        col("col3").alias("name"),
        col("col4").alias("slug"),
        col("col5").alias("domain"),
        col("col6").cast("boolean").alias("is_active"),
        col("settings_parsed.plan_type").alias("plan_type"),
        col("settings_parsed.max_users").alias("max_users"),
        col("settings_parsed.features").alias("features"),
        to_timestamp(col("col8")).alias("created_at"),
        to_timestamp(col("col9")).alias("updated_at"),
        current_timestamp().alias("processed_at")
    )

print(f"Silver records after transformation: {silver_df.count()}")

# Data quality checks
print("Performing data quality checks...")
null_ids = silver_df.filter(col("id").isNull()).count()
null_names = silver_df.filter(col("name").isNull()).count()
inactive_tenants = silver_df.filter(col("is_active") == False).count()

print(f"Data Quality Report:")
print(f"  - NULL IDs: {null_ids}")
print(f"  - NULL Names: {null_names}")
print(f"  - Inactive Tenants: {inactive_tenants}")

# Show sample data
print("Sample transformed data:")
silver_df.show(5, truncate=False)

# Write to Silver layer in Parquet format
print("Writing to Silver layer...")
output_path = "s3://lakehouse-poc-dev-silver-ti4jmrk8/tenant/"

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save(output_path)

print(f"Successfully wrote {silver_df.count()} records to {output_path}")

# Commit job
job.commit()
print("Job completed successfully!")
