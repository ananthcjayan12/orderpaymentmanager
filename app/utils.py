from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Value
from django.db.models.functions import Coalesce

def calculate_total_orders_amount(orders_queryset):
    """
    Calculate the total amount for a queryset of orders.
    
    Args:
        orders_queryset: A queryset of Order objects
        
    Returns:
        Decimal: The total amount of all orders
    """
    return orders_queryset.aggregate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    F('orderitems__quantity') * F('orderitems__price'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
        )
    )['total']

def calculate_total_payments(payments_queryset):
    """
    Calculate the total payments received from a queryset of payments.
    
    Args:
        payments_queryset: A queryset of Payment objects
        
    Returns:
        Decimal: The total amount of all payments
    """
    return payments_queryset.aggregate(
        total=Coalesce(
            Sum('amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
        )
    )['total']

def calculate_customer_balance(customer):
    """
    Calculate the outstanding balance for a customer.
    
    Args:
        customer: A Customer object
        
    Returns:
        Decimal: The outstanding balance
    """
    total_orders_amount = calculate_total_orders_amount(customer.orders.all())
    total_payments = calculate_total_payments(customer.payments.all())
    return total_orders_amount - total_payments + customer.initial_balance

def calculate_total_initial_balance(customers_queryset):
    """
    Calculate the total initial balance for a queryset of customers.
    
    Args:
        customers_queryset: A queryset of Customer objects
        
    Returns:
        Decimal: The total initial balance
    """
    return customers_queryset.aggregate(
        total=Coalesce(
            Sum('initial_balance', output_field=DecimalField(max_digits=10, decimal_places=2)),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
        )
    )['total'] 