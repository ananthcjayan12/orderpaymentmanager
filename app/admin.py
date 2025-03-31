from django.contrib import admin
from .models import (
    Customer, Item, CustomerItemPrice, Order, OrderItem, OrderTemplate, OrderTemplateItem, Bank, OrderPayment, Payment
)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'mobile1', 'address', 'created_at')
    search_fields = ('name', 'mobile1', 'address')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'default_price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(CustomerItemPrice)
class CustomerItemPriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'item', 'price')
    search_fields = ('customer__name', 'item__name')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'order_date', 'order_type', 'next_payment_date')
    list_filter = ('order_type', 'order_date')
    search_fields = ('customer__name',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'item_name', 'quantity', 'price')
    search_fields = ('order__customer__name', 'item_name')

@admin.register(OrderTemplate)
class OrderTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'company', 'created_at', 'is_active')
    search_fields = ('name', 'company__name')

@admin.register(OrderTemplateItem)
class OrderTemplateItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'template', 'item', 'quantity', 'default_price')
    search_fields = ('template__name', 'item__name')

@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'company', 'is_default')
    list_filter = ('is_default', 'company')
    search_fields = ('name', 'company__name')

@admin.register(OrderPayment)
class OrderPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'installment_number', 'due_date', 'amount', 'payment')
    list_filter = ('due_date', 'installment_number')
    search_fields = ('order__customer__name',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'payment_date', 'amount_received', 'agent')
    list_filter = ('payment_date',)
    search_fields = ('customer__name', 'agent__username')
