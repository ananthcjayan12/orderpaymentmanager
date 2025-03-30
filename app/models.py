from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F
from accounts.models import Company
from .utils import calculate_total_orders_amount, calculate_total_payments, calculate_customer_balance
from django.core.validators import MinValueValidator, MaxValueValidator

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
        return calculate_customer_balance(self)

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
    ORDER_TYPE_CHOICES = [
        ('B2C_READY_CASH', 'B2C Ready Cash'),
        ('B2C_EMI', 'B2C EMI'),
        ('B2B_READY_CASH', 'B2B Ready Cash'),
        ('B2B_EMI', 'B2B EMI'),
    ]
    
    COLLECTION_FREQUENCY_CHOICES = [
        ('NONE', 'No Regular Collection'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]
    
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
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
    delivery_date = models.DateField(null=True, blank=True, help_text="Date when the order should be delivered (optional)")
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='B2C_READY_CASH'
    )
    emi_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text="Amount to be collected per installment for EMI orders"
    )
    collection_frequency = models.CharField(
        max_length=10,
        choices=COLLECTION_FREQUENCY_CHOICES,
        default='NONE'
    )
    collection_day_of_week = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        help_text='Day of the week for weekly collections'
    )
    collection_day_of_month = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text='Day of the month for monthly collections (1-31)'
    )
    next_payment_date = models.DateField(null=True, blank=True, help_text="Calculated next payment date based on collection frequency")
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
        
    def save(self, *args, **kwargs):
        """Override save method to calculate next payment date."""
        # Calculate next payment date based on collection frequency
        if self.collection_frequency == 'WEEKLY' and self.collection_day_of_week is not None:
            # Get the next occurrence of the specified day of the week
            today = timezone.localdate()
            days_ahead = self.collection_day_of_week - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            self.next_payment_date = today + timezone.timedelta(days=days_ahead)
        elif self.collection_frequency == 'MONTHLY' and self.collection_day_of_month is not None:
            # Get the next occurrence of the specified day of the month
            today = timezone.localdate()
            # If today is after the collection day in the current month, move to next month
            if today.day > self.collection_day_of_month:
                if today.month == 12:
                    next_month = 1
                    next_year = today.year + 1
                else:
                    next_month = today.month + 1
                    next_year = today.year
                # Handle case where day might be invalid for the next month (e.g., 31 in a 30-day month)
                import calendar
                last_day = calendar.monthrange(next_year, next_month)[1]
                day = min(self.collection_day_of_month, last_day)
                self.next_payment_date = timezone.datetime(next_year, next_month, day).date()
            else:
                # Set to the collection day in the current month
                self.next_payment_date = timezone.datetime(today.year, today.month, self.collection_day_of_month).date()
        else:
            # No regular collection
            self.next_payment_date = None
        
        super().save(*args, **kwargs)

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

class Bank(models.Model):
    """Model for company banks."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='banks')
    name = models.CharField(max_length=100, help_text="Payment receiving account (e.g., 'Main Account', 'Cash')")
    is_default = models.BooleanField(default=False, help_text="Set as the default payment method")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        unique_together = ['company', 'name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # If this bank is set as default, unset default for other banks of the company
        if self.is_default:
            Bank.objects.filter(company=self.company, is_default=True).exclude(pk=self.pk).update(is_default=False)
        # If no default set for the company, make this the default
        elif not Bank.objects.filter(company=self.company, is_default=True).exists():
            self.is_default = True
        super().save(*args, **kwargs)

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
    bank = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.customer.name}"
