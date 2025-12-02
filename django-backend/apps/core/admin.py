"""
Django admin configuration for core models.
"""
from django.contrib import admin
from .models import Tenant, Customer, Product, Order, OrderItem, Event, Subscription, Invoice


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'domain']
    readonly_fields = ['id', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'tenant', 'is_active', 'created_at']
    list_filter = ['is_active', 'tenant', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['tenant']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'tenant', 'category', 'price', 'stock_quantity', 'is_active']
    list_filter = ['is_active', 'category', 'tenant', 'created_at']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['tenant']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'tenant', 'customer', 'status', 'total', 'order_date']
    list_filter = ['status', 'tenant', 'order_date']
    search_fields = ['order_number', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['tenant', 'customer']
    date_hierarchy = 'order_date'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ['product']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'unit_price', 'total']
    search_fields = ['order__order_number', 'product__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['order', 'product']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'tenant', 'customer', 'session_id', 'created_at']
    list_filter = ['event_type', 'tenant', 'created_at']
    search_fields = ['session_id', 'customer__email']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['tenant', 'customer']
    date_hierarchy = 'created_at'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['plan_name', 'tenant', 'customer', 'status', 'monthly_amount', 'start_date', 'end_date']
    list_filter = ['status', 'billing_cycle', 'tenant', 'start_date']
    search_fields = ['plan_name', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['tenant', 'customer']
    date_hierarchy = 'start_date'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'tenant', 'customer', 'amount', 'status', 'issue_date', 'due_date']
    list_filter = ['status', 'tenant', 'issue_date']
    search_fields = ['invoice_number', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['tenant', 'customer', 'subscription']
    date_hierarchy = 'issue_date'
