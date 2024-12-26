from django.db import models
from django.db.models import Sum, F
from django.utils import timezone

class Customer(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    mobile1 = models.CharField(max_length=15)
    mobile2 = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def outstanding_balance(self):
        orders_total = self.orders.annotate(
            item_total=Sum(F('orderitems__quantity') * F('orderitems__price'))
        ).aggregate(
            total=Sum('item_total')
        )['total'] or 0
        
        payments_total = self.payments.aggregate(
            total=Sum('amount_received')
        )['total'] or 0
        
        return orders_total - payments_total

class Order(models.Model):
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_date = models.DateField(default=timezone.now)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"

    @property
    def total_amount(self):
        return self.orderitems.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or 0

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='orderitems'
    )
    item_name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.item_name} - {self.quantity} units"

    @property
    def line_total(self):
        return self.quantity * self.price

class Payment(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_date = models.DateField(default=timezone.now)
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.name} - {self.amount_received} on {self.payment_date}"
