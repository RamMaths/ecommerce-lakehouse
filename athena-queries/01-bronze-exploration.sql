-- Bronze Layer Data Exploration Queries
-- Database: lakehouse-poc_dev_bronze
-- Note: Column names are col0, col1, col2, etc. because CSV has no headers

-- ============================================
-- 1. TENANT ANALYSIS
-- ============================================

-- Count tenants
SELECT COUNT(*) as tenant_count 
FROM "lakehouse-poc_dev_bronze".core_tenant;

-- View tenant details
-- col0 = operation (I/U/D)
-- col1 = timestamp
-- col2 = id (UUID)
-- col3 = name
-- col4 = slug
-- col5 = domain
-- col6 = is_active
-- col7 = settings (JSON)
-- col8 = created_at
-- col9 = updated_at
SELECT 
  col2 as id,
  col3 as name,
  col4 as slug,
  col6 as is_active,
  col7.plan_type as plan_type,
  col7.max_users as max_users
FROM "lakehouse-poc_dev_bronze".core_tenant
WHERE col0 = 'I'  -- Only inserts
LIMIT 10;

-- ============================================
-- 2. CUSTOMER ANALYSIS
-- ============================================

-- Count customers
SELECT COUNT(*) as customer_count 
FROM "lakehouse-poc_dev_bronze".core_customer;

-- Customers by tenant
SELECT 
  col3 as tenant_id,
  COUNT(*) as customer_count
FROM "lakehouse-poc_dev_bronze".core_customer
WHERE col0 = 'I'
GROUP BY col3
ORDER BY customer_count DESC;

-- ============================================
-- 3. ORDER ANALYSIS
-- ============================================

-- Count orders
SELECT COUNT(*) as order_count 
FROM "lakehouse-poc_dev_bronze".core_order;

-- Orders by status
-- col6 = status
SELECT 
  col6 as status,
  COUNT(*) as order_count,
  ROUND(SUM(CAST(col5 AS DOUBLE)), 2) as total_amount
FROM "lakehouse-poc_dev_bronze".core_order
WHERE col0 = 'I'
GROUP BY col6
ORDER BY order_count DESC;

-- Revenue by tenant
SELECT 
  t.col3 as tenant_name,
  COUNT(DISTINCT o.col2) as order_count,
  ROUND(SUM(CAST(o.col5 AS DOUBLE)), 2) as total_revenue,
  ROUND(AVG(CAST(o.col5 AS DOUBLE)), 2) as avg_order_value
FROM "lakehouse-poc_dev_bronze".core_order o
JOIN "lakehouse-poc_dev_bronze".core_tenant t 
  ON o.col3 = t.col2
WHERE o.col0 = 'I' AND o.col6 = 'completed'
GROUP BY t.col3
ORDER BY total_revenue DESC;

-- ============================================
-- 4. PRODUCT ANALYSIS
-- ============================================

-- Count products
SELECT COUNT(*) as product_count 
FROM "lakehouse-poc_dev_bronze".core_product;

-- Products by category
-- col5 = category
SELECT 
  col5 as category,
  COUNT(*) as product_count,
  ROUND(AVG(CAST(col6 AS DOUBLE)), 2) as avg_price
FROM "lakehouse-poc_dev_bronze".core_product
WHERE col0 = 'I'
GROUP BY col5
ORDER BY product_count DESC;

-- Top products by order count
SELECT 
  p.col3 as product_name,
  p.col5 as category,
  COUNT(*) as times_ordered,
  SUM(CAST(oi.col5 AS INT)) as total_quantity
FROM "lakehouse-poc_dev_bronze".core_orderitem oi
JOIN "lakehouse-poc_dev_bronze".core_product p 
  ON oi.col4 = p.col2
WHERE oi.col0 = 'I'
GROUP BY p.col3, p.col5
ORDER BY times_ordered DESC
LIMIT 20;

-- ============================================
-- 5. EVENT ANALYSIS
-- ============================================

-- Count events
SELECT COUNT(*) as event_count 
FROM "lakehouse-poc_dev_bronze".core_event;

-- Events by type
-- col4 = event_type
SELECT 
  col4 as event_type,
  COUNT(*) as event_count,
  COUNT(DISTINCT col5) as unique_customers
FROM "lakehouse-poc_dev_bronze".core_event
WHERE col0 = 'I'
GROUP BY col4
ORDER BY event_count DESC;

-- Event funnel analysis
WITH event_counts AS (
  SELECT 
    col4 as event_type,
    COUNT(*) as event_count
  FROM "lakehouse-poc_dev_bronze".core_event
  WHERE col0 = 'I'
  GROUP BY col4
)
SELECT 
  event_type,
  event_count,
  ROUND(100.0 * event_count / SUM(event_count) OVER (), 2) as percentage
FROM event_counts
ORDER BY event_count DESC;

-- ============================================
-- 6. SUBSCRIPTION ANALYSIS
-- ============================================

-- Count subscriptions
SELECT COUNT(*) as subscription_count 
FROM "lakehouse-poc_dev_bronze".core_subscription;

-- Subscriptions by status
-- col6 = status
SELECT 
  col6 as status,
  COUNT(*) as subscription_count,
  ROUND(SUM(CAST(col8 AS DOUBLE)), 2) as total_mrr
FROM "lakehouse-poc_dev_bronze".core_subscription
WHERE col0 = 'I'
GROUP BY col6
ORDER BY subscription_count DESC;

-- MRR by tenant
SELECT 
  t.col3 as tenant_name,
  COUNT(s.col2) as active_subscriptions,
  ROUND(SUM(CAST(s.col8 AS DOUBLE)), 2) as mrr,
  ROUND(AVG(CAST(s.col8 AS DOUBLE)), 2) as avg_subscription_value
FROM "lakehouse-poc_dev_bronze".core_subscription s
JOIN "lakehouse-poc_dev_bronze".core_tenant t 
  ON s.col3 = t.col2
WHERE s.col0 = 'I' AND s.col6 = 'active'
GROUP BY t.col3
ORDER BY mrr DESC;

-- ============================================
-- 7. INVOICE ANALYSIS
-- ============================================

-- Count invoices
SELECT COUNT(*) as invoice_count 
FROM "lakehouse-poc_dev_bronze".core_invoice;

-- Invoices by status
-- col6 = status
SELECT 
  col6 as status,
  COUNT(*) as invoice_count,
  ROUND(SUM(CAST(col5 AS DOUBLE)), 2) as total_amount
FROM "lakehouse-poc_dev_bronze".core_invoice
WHERE col0 = 'I'
GROUP BY col6
ORDER BY invoice_count DESC;

-- ============================================
-- 8. DATA QUALITY CHECKS
-- ============================================

-- Check for NULL values in key fields
SELECT 
  'core_tenant' as table_name,
  SUM(CASE WHEN col2 IS NULL THEN 1 ELSE 0 END) as null_ids,
  SUM(CASE WHEN col3 IS NULL THEN 1 ELSE 0 END) as null_names,
  COUNT(*) as total_records
FROM "lakehouse-poc_dev_bronze".core_tenant
WHERE col0 = 'I'

UNION ALL

SELECT 
  'core_customer' as table_name,
  SUM(CASE WHEN col2 IS NULL THEN 1 ELSE 0 END) as null_ids,
  SUM(CASE WHEN col4 IS NULL THEN 1 ELSE 0 END) as null_emails,
  COUNT(*) as total_records
FROM "lakehouse-poc_dev_bronze".core_customer
WHERE col0 = 'I'

UNION ALL

SELECT 
  'core_order' as table_name,
  SUM(CASE WHEN col2 IS NULL THEN 1 ELSE 0 END) as null_ids,
  SUM(CASE WHEN col5 IS NULL THEN 1 ELSE 0 END) as null_amounts,
  COUNT(*) as total_records
FROM "lakehouse-poc_dev_bronze".core_order
WHERE col0 = 'I';

-- ============================================
-- 9. RECORD COUNTS SUMMARY
-- ============================================

SELECT 
  'Tenants' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_tenant
WHERE col0 = 'I'

UNION ALL

SELECT 
  'Customers' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_customer
WHERE col0 = 'I'

UNION ALL

SELECT 
  'Products' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_product
WHERE col0 = 'I'

UNION ALL

SELECT 
  'Orders' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_order
WHERE col0 = 'I'

UNION ALL

SELECT 
  'Order Items' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_orderitem
WHERE col0 = 'I'

UNION ALL

SELECT 
  'Events' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_event
WHERE col0 = 'I'

UNION ALL

SELECT 
  'Subscriptions' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_subscription
WHERE col0 = 'I'

UNION ALL

SELECT 
  'Invoices' as entity,
  COUNT(*) as record_count
FROM "lakehouse-poc_dev_bronze".core_invoice
WHERE col0 = 'I'

ORDER BY record_count DESC;

-- ============================================
-- 10. BUSINESS METRICS PREVIEW
-- ============================================

-- Overall business summary
SELECT 
  (SELECT COUNT(*) FROM "lakehouse-poc_dev_bronze".core_tenant WHERE col0 = 'I') as total_tenants,
  (SELECT COUNT(*) FROM "lakehouse-poc_dev_bronze".core_customer WHERE col0 = 'I') as total_customers,
  (SELECT COUNT(*) FROM "lakehouse-poc_dev_bronze".core_order WHERE col0 = 'I' AND col6 = 'completed') as completed_orders,
  (SELECT ROUND(SUM(CAST(col5 AS DOUBLE)), 2) FROM "lakehouse-poc_dev_bronze".core_order WHERE col0 = 'I' AND col6 = 'completed') as total_revenue,
  (SELECT ROUND(SUM(CAST(col8 AS DOUBLE)), 2) FROM "lakehouse-poc_dev_bronze".core_subscription WHERE col0 = 'I' AND col6 = 'active') as total_mrr,
  (SELECT COUNT(*) FROM "lakehouse-poc_dev_bronze".core_event WHERE col0 = 'I') as total_events;
