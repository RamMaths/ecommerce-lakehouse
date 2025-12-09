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

# col2=id, col3=tenant_id, col4=customer_id, col5=order_number
# col6=total, col7=subtotal, col8=tax, col9=discount, col10=status
# col11=order_date, col12=created_at, col13=updated_at

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col3").alias("tenant_id"),
        col("col4").alias("customer_id"),
        col("col5").alias("order_number"),
        col("col6").cast("decimal(10,2)").alias("total"),
        col("col7").cast("decimal(10,2)").alias("subtotal"),
        col("col8").cast("decimal(10,2)").alias("tax"),
        col("col9").cast("decimal(10,2)").alias("discount"),
        col("col10").alias("status"),
        to_timestamp(col("col11")).alias("order_date"),
        to_timestamp(col("col12")).alias("created_at"),
        to_timestamp(col("col13")).alias("updated_at"),
        current_timestamp().alias("processed_at")
    )

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .partitionBy("order_date") \
    .save("s3://lakehouse-poc-dev-silver-ti4jmrk8/order/")

job.commit()
