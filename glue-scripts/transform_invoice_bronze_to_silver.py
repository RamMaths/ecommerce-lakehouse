"""
Glue ETL Job: Transform Invoice from Bronze to Silver
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
    table_name="core_invoice"
).toDF()

# col2=id, col3=tenant_id, col4=customer_id, col5=subscription_id
# col6=invoice_number, col7=amount, col8=status, col9=due_date
# col10=paid_date, col11=created_at, col12=updated_at

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col3").alias("tenant_id"),
        col("col4").alias("customer_id"),
        col("col5").alias("subscription_id"),
        col("col6").alias("invoice_number"),
        col("col7").cast("decimal(10,2)").alias("amount"),
        col("col8").alias("status"),
        to_timestamp(col("col9")).alias("due_date"),
        to_timestamp(col("col10")).alias("paid_date"),
        to_timestamp(col("col11")).alias("created_at"),
        to_timestamp(col("col12")).alias("updated_at"),
        current_timestamp().alias("processed_at")
    )

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-silver-ti4jmrk8/invoice/")

job.commit()
