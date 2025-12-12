"""
Glue ETL Job: Transform Customer from Bronze to Silver
Purpose: Clean and standardize customer data
Input: Bronze layer core_customer table
Output: Silver layer customer/ folder
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, current_timestamp, trim, lower, concat_ws, lit

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("Starting Customer Bronze to Silver transformation...")

# Read from Bronze
bronze_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse-poc_dev_bronze",
    table_name="core_customer"
).toDF()

print(f"Bronze records: {bronze_df.count()}")

# Actual column mapping based on Bronze data:
# col0 = operation (I/U/D)
# col1 = dms_timestamp
# col2 = id (UUID)
# col3 = email
# col4 = first_name
# col5 = last_name
# col6 = phone
# col7 = is_active
# col8-col11 = metadata JSON fragments

# Note: tenant_id is missing from Bronze - this is a DMS issue
# We'll need to derive it from order data or fix DMS task

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        lit("unknown").alias("tenant_id"),  # Missing from Bronze - will fix later
        trim(lower(col("col3"))).alias("email"),
        col("col4").alias("first_name"),
        col("col5").alias("last_name"),
        col("col6").alias("phone"),
        col("col7").cast("boolean").alias("is_active"),
        concat_ws("", col("col8"), col("col9"), col("col10"), col("col11")).alias("metadata_raw"),
        current_timestamp().alias("processed_at")
    )

print(f"Silver records: {silver_df.count()}")

# Data quality checks
null_emails = silver_df.filter(col("email").isNull()).count()
missing_tenant_ids = silver_df.filter(col("tenant_id").isNull()).count()
print(f"NULL emails: {null_emails}")
print(f"Missing tenant_ids: {missing_tenant_ids}")

# Write to Silver
output_path = "s3://lakehouse-poc-dev-silver-ti4jmrk8/customer/"
silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save(output_path)

print(f"Successfully wrote to {output_path}")
job.commit()
