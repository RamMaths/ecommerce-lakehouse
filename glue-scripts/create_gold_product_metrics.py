"""
Glue ETL Job: Create Gold Layer Product Metrics
Purpose: Product performance analytics and inventory insights
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, sum as spark_sum, count, avg, round as spark_round, current_timestamp

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print("Creating Gold Layer Product Metrics...")

# Read Silver layer tables
tenants_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="tenant"
).toDF()

products_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="product"
).toDF()

orderitems_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="orderitem"
).toDF()

orders_df = glueContext.create_dynamic_frame.from_catalog(
    database="lakehouse_poc_dev_silver",
    table_name="order"
).toDF()

# Product Performance by Tenant
product_performance = orderitems_df \
    .join(orders_df.filter(col("status") == "completed").select("id", "tenant_id"), 
          orderitems_df.order_id == orders_df.id) \
    .groupBy("tenant_id", "product_id") \
    .agg(
        count("orderitems_df.id").alias("times_ordered"),
        spark_sum("quantity").alias("total_quantity_sold"),
        spark_round(spark_sum("subtotal"), 2).alias("total_revenue")
    ) \
    .join(products_df.select("id", "name", "price", "stock_quantity"), 
          col("product_id") == products_df.id) \
    .join(tenants_df.select("id", "name"), col("tenant_id") == tenants_df.id) \
    .select(
        col("tenant_id"),
        tenants_df.name.alias("tenant_name"),
        col("product_id"),
        products_df.name.alias("product_name"),
        col("price").alias("current_price"),
        col("stock_quantity").alias("current_stock"),
        col("times_ordered"),
        col("total_quantity_sold"),
        col("total_revenue"),
        spark_round(col("total_revenue") / col("total_quantity_sold"), 2).alias("avg_selling_price"),
        current_timestamp().alias("processed_at")
    )

# Top Products by Revenue
top_products_by_revenue = product_performance \
    .orderBy(col("total_revenue").desc()) \
    .limit(100)

# Low Stock Alert
low_stock_products = products_df \
    .filter(col("stock_quantity") < 50) \
    .join(tenants_df.select("id", "name"), col("tenant_id") == tenants_df.id) \
    .select(
        col("tenant_id"),
        col("name").alias("tenant_name"),
        col("id").alias("product_id"),
        products_df.name.alias("product_name"),
        col("stock_quantity"),
        col("price"),
        current_timestamp().alias("processed_at")
    )

print(f"Product performance records: {product_performance.count()}")
print(f"Top products records: {top_products_by_revenue.count()}")
print(f"Low stock products: {low_stock_products.count()}")

# Write to Gold layer
product_performance.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/product_performance/")

top_products_by_revenue.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/top_products/")

low_stock_products.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://lakehouse-poc-dev-gold-ti4jmrk8/low_stock_alert/")

print("Gold layer product metrics created successfully!")
job.commit()
