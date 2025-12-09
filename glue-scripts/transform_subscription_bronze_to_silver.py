"""
Glue ETL Job: Transform Subscription from Bronze to Silver
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
    table_name="core_subscription"
).toDF()

# col2=id, col3=tenant_id, col4=customer_id, col5=plan_name
# col6=billing_cycle, col7=status, col8=start_date, col9=end_date
# col10=monthly_amount, col11=created_at, col12=updated_at

silver_df = bronze_df \
    .filter(col("col0") == "I") \
    .select(
        col("col2").alias("id"),
        col("col3").alias("tenant_id"),
        col("col4").alias("customer_id"),
        col("col5").alias("plan_name"),
        col("col6").alias("billing_cycle"),
        col("col7").alias("status"),
        to_timestamp(col("col8")).alias("start_date"),
        to_timestamp(col("col9")).alias("end_date"),
        col("col10").cast("decimal(10,2)").alias("monthly_amount"),
        to_timestamp(col("col11")).alias("created_at"),
        to_timestamp(col("col12")).alias("updated_at"),
        current_timestamp().alias("processed_at")
    )

silver_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-silver-ti4jmrk8/subscription/")

job.commit()
