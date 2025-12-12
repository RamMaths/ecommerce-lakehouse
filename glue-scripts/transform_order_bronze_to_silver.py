"""
Glue ETL Job: Transform Order from Bronze to Silver
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, to_timestamp, current_timestamp

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

bronze_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse-poc_dev_bronze",
    table_name="core_order"
).toDF()

# Actual column mapping based on Bronze data (16 columns):
# col0 = operation, col1 = dms_timestamp, col2 = id
# col3 = order_number, col4 = status, col5 = subtotal
# col6 = tax, col7 = shipping, col8 = total
# col9 = order_date, col10 = shipped_date
# col11-col12 = metadata, col13 = customer_id, col14 = tenant_id, col15 = timestamps

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col14").alias("tenant_id"),
        col("col13").alias("customer_id"),
        col("col3").alias("order_number"),
        col("col4").alias("status"),
        col("col5").cast("decimal(10,2)").alias("subtotal"),
        col("col6").cast("decimal(10,2)").alias("tax"),
        col("col7").cast("decimal(10,2)").alias("shipping"),
        col("col8").cast("decimal(10,2)").alias("total"),
        to_timestamp(col("col9")).alias("order_date"),
        to_timestamp(col("col10")).alias("shipped_date"),
        current_timestamp().alias("processed_at")
    )

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .partitionBy("order_date") \
    .save("s3://lakehouse-poc-dev-silver-ti4jmrk8/order/")

job.commit()
