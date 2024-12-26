from django.contrib import admin
from .models import Customer, Order, OrderItem, Payment

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile1', 'location', 'outstanding_balance')
    search_fields = ('name', 'mobile1', 'mobile2', 'location')
    list_filter = ('location', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'order_date', 'total_amount')
    list_filter = ('order_date', 'customer')
    search_fields = ('customer__name',)
    inlines = [OrderItemInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'payment_date', 'amount_received')
    list_filter = ('payment_date', 'customer')
    search_fields = ('customer__name',)
