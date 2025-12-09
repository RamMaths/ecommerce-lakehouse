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
from pyspark.sql.functions import col, to_timestamp, current_timestamp, trim, lower

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

# Column mapping:
# col0 = operation, col1 = dms_timestamp
# col2 = id, col3 = tenant_id, col4 = email, col5 = first_name
# col6 = last_name, col7 = phone, col8 = address, col9 = city
# col10 = state, col11 = country, col12 = postal_code, col13 = metadata
# col14 = created_at, col15 = updated_at

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col3").alias("tenant_id"),
        trim(lower(col("col4"))).alias("email"),
        col("col5").alias("first_name"),
        col("col6").alias("last_name"),
        col("col7").alias("phone"),
        col("col8").alias("address"),
        col("col9").alias("city"),
        col("col10").alias("state"),
        col("col11").alias("country"),
        col("col12").alias("postal_code"),
        col("col13").alias("metadata"),
        to_timestamp(col("col14")).alias("created_at"),
        to_timestamp(col("col15")).alias("updated_at"),
        current_timestamp().alias("processed_at")
    )

print(f"Silver records: {silver_df.count()}")

# Data quality checks
null_emails = silver_df.filter(col("email").isNull()).count()
print(f"NULL emails: {null_emails}")

# Write to Silver
output_path = "s3://lakehouse-poc-dev-silver-ti4jmrk8/customer/"
silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .partitionBy("created_at") \
    .save(output_path)

print(f"Successfully wrote to {output_path}")
job.commit()
