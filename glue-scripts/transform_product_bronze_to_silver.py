"""
Glue ETL Job: Transform Product from Bronze to Silver
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
    table_name="core_product"
).toDF()

# col2=id, col3=tenant_id, col4=name, col5=sku, col6=description
# col7=category, col8=price, col9=cost, col10=stock_quantity
# col11=is_active, col12=created_at, col13=updated_at

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col3").alias("tenant_id"),
        col("col4").alias("name"),
        col("col5").alias("sku"),
        col("col6").alias("description"),
        col("col7").alias("category"),
        col("col8").cast("decimal(10,2)").alias("price"),
        col("col9").cast("decimal(10,2)").alias("cost"),
        col("col10").cast("integer").alias("stock_quantity"),
        col("col11").cast("boolean").alias("is_active"),
        to_timestamp(col("col12")).alias("created_at"),
        to_timestamp(col("col13")).alias("updated_at"),
        current_timestamp().alias("processed_at")
    )

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-silver-ti4jmrk8/product/")

job.commit()
