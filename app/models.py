from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F
from accounts.models import Company

class Customer(models.Model):
    """Model for customers."""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='customers'
    )
    name = models.CharField(max_length=100)
    address = models.TextField()
    mobile1 = models.CharField(max_length=20)
    mobile2 = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=100)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    initial_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def outstanding_balance(self):
        """Calculate outstanding balance for the customer."""
        total_orders = self.orders.aggregate(
            total=Sum(F('orderitems__quantity') * F('orderitems__price'))
        )['total'] or 0
        total_payments = self.payments.aggregate(
            total=Sum('amount_received')
        )['total'] or 0
        return total_orders - total_payments + self.initial_balance

class Item(models.Model):
    """Model for items."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, default='unit')
    default_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_price_for_customer(self, customer=None):
        """Get price for a specific customer or default price."""
        if customer:
            customer_price = self.customer_prices.filter(customer=customer).first()
            if customer_price:
                return customer_price.price
        return self.default_price

class CustomerItemPrice(models.Model):
    """Model for customer-specific item prices."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='item_prices')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='customer_prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['customer', 'item']

    def __str__(self):
        return f"{self.customer.name} - {self.item.name}: ₹{self.price}"

class Order(models.Model):
    """Model for orders."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='orders')
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_orders'
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateField()
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"

    @property
    def total_amount(self):
        """Calculate total amount for the order."""
        return self.orderitems.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or 0

class OrderItem(models.Model):
    """Model for order items."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='orderitems')
    item = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )
    item_name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.item_name} - {self.quantity}"

    @property
    def line_total(self):
        """Calculate total for this line item."""
        return self.quantity * self.price

class Payment(models.Model):
    """Model for payments."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payments')
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_payments'
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.customer.name}"

class OrderTemplate(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='order_templates')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['name', 'company']

    def __str__(self):
        return self.name

    def get_total_items(self):
        return self.template_items.count()

    def get_total_value(self):
        return sum(item.quantity * item.default_price for item in self.template_items.all())

class OrderTemplateItem(models.Model):
    template = models.ForeignKey(OrderTemplate, on_delete=models.CASCADE, related_name='template_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    default_price = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['item__name']

    def __str__(self):
        return f"{self.item.name} - {self.quantity}"
