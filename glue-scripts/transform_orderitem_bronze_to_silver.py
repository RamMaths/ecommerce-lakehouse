"""
Glue ETL Job: Transform OrderItem from Bronze to Silver
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
    table_name="core_orderitem"
).toDF()

# col2=id, col3=order_id, col4=product_id, col5=quantity
# col6=unit_price, col7=discount, col8=total
# col9=created_at, col10=updated_at

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col3").alias("order_id"),
        col("col4").alias("product_id"),
        col("col5").cast("integer").alias("quantity"),
        col("col6").cast("decimal(10,2)").alias("unit_price"),
        col("col7").cast("decimal(10,2)").alias("discount"),
        col("col8").cast("decimal(10,2)").alias("total"),
        to_timestamp(col("col9")).alias("created_at"),
        to_timestamp(col("col10")).alias("updated_at"),
        current_timestamp().alias("processed_at")
    )

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-silver-ti4jmrk8/orderitem/")

job.commit()
