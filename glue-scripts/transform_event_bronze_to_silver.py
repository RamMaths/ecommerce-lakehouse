"""
Glue ETL Job: Transform Event from Bronze to Silver
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
    table_name="core_event"
).toDF()

# col2=id, col3=tenant_id, col4=event_type, col5=customer_id
# col6=session_id, col7=page_url, col8=metadata
# col9=event_timestamp, col10=created_at

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col3").alias("tenant_id"),
        col("col4").alias("event_type"),
        col("col5").alias("customer_id"),
        col("col6").alias("session_id"),
        col("col7").alias("page_url"),
        col("col8").alias("metadata"),
        to_timestamp(col("col9")).alias("event_timestamp"),
        to_timestamp(col("col10")).alias("created_at"),
        current_timestamp().alias("processed_at")
    )

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .partitionBy("event_timestamp") \
    .save("s3://lakehouse-poc-dev-silver-ti4jmrk8/event/")

job.commit()
