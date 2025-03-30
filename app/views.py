from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F, Q, ExpressionWrapper, DecimalField, Value, Count, Max
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

import json
import csv
import io
import pandas as pd
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from accounts.models import Company
from .models import Customer, Order, OrderItem, Payment, Item, OrderTemplate, OrderTemplateItem, Bank
from .forms import (
    OrderForm, OrderItemFormSet, PaymentForm, BulkOrderForm, 
    OrderTemplateForm, OrderTemplateItemFormSet, CustomerForm, CustomerCSVUploadForm, BankForm
)
from .utils import (
    calculate_total_orders_amount, calculate_total_payments, 
    calculate_customer_balance, calculate_total_initial_balance
)

@login_required
def home(request):
    """Home page view serving as the main dashboard."""
    company = request.user.company
    user_type = request.user.user_type
    
    # Get time frame parameters
    timeframe = request.GET.get('timeframe', 'monthly')
    today = timezone.now()
    
    # Calculate date range based on timeframe
    if timeframe == 'daily':
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today
        previous_start = start_date - timezone.timedelta(days=1)
        previous_end = start_date
    elif timeframe == 'weekly':
        start_date = today - timezone.timedelta(days=today.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today
        previous_start = start_date - timezone.timedelta(days=7)
        previous_end = start_date
    elif timeframe == 'monthly':
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today
        previous_start = (start_date - timezone.timedelta(days=1)).replace(day=1)
        previous_end = start_date
    elif timeframe == 'custom':
        try:
            start_date = timezone.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
            end_date = timezone.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
            date_diff = (end_date - start_date).days
            previous_start = start_date - timezone.timedelta(days=date_diff)
            previous_end = start_date
        except (TypeError, ValueError):
            # Default to monthly if custom dates are invalid
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = today
            previous_start = (start_date - timezone.timedelta(days=1)).replace(day=1)
            previous_end = start_date
    else:  # all time
        start_date = None
        end_date = today
        previous_start = None
        previous_end = None
    
    # Base querysets
    customers = Customer.objects.filter(company=company)
    orders = Order.objects.filter(company=company)
    payments = Payment.objects.filter(company=company)
    
    if user_type == 'AGENT':
        orders = orders.filter(agent=request.user)
        payments = payments.filter(agent=request.user)
    
    # Apply date filters if not "all time"
    if start_date:
        current_customers = customers.filter(created_at__range=[start_date, end_date]).count()
        current_orders = orders.filter(created_at__range=[start_date, end_date]).count()
        current_collections = payments.filter(
            created_at__range=[start_date, end_date]
        ).aggregate(
            total=Coalesce(
                Sum('amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            )
        )['total']
        
        if previous_start:
            previous_customers = customers.filter(created_at__range=[previous_start, previous_end]).count()
            previous_orders = orders.filter(created_at__range=[previous_start, previous_end]).count()
            previous_collections = payments.filter(
                created_at__range=[previous_start, previous_end]
            ).aggregate(
                total=Coalesce(
                    Sum('amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                )
            )['total']
        else:
            previous_customers = 0
            previous_orders = 0
            previous_collections = 0
    else:
        # All time stats
        current_customers = customers.count()
        current_orders = orders.count()
        current_collections = payments.aggregate(
            total=Coalesce(
                Sum('amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            )
        )['total']
        previous_customers = 0
        previous_orders = 0
        previous_collections = 0
    
    # Calculate growth percentages
    customers_growth = (
        ((current_customers - previous_customers) / previous_customers * 100)
        if previous_customers > 0 else 
        (100 if current_customers > 0 else 0)
    )
    
    orders_growth = (
        ((current_orders - previous_orders) / previous_orders * 100)
        if previous_orders > 0 else
        (100 if current_orders > 0 else 0)
    )
    
    collections_growth = (
        ((current_collections - previous_collections) / previous_collections * 100)
        if previous_collections > 0 else
        (100 if current_collections > 0 else 0)
    )
    
    # Calculate totals for the selected period
    if start_date:
        filtered_payments = payments.filter(created_at__range=[start_date, end_date])
        filtered_orders = orders.filter(created_at__range=[start_date, end_date])
        total_collections = calculate_total_payments(filtered_payments)
        total_orders_amount = calculate_total_orders_amount(filtered_orders)
    else:
        total_collections = calculate_total_payments(payments)
        total_orders_amount = calculate_total_orders_amount(orders)
    
    # Get total initial balance from all customers
    total_initial_balance = calculate_total_initial_balance(customers)
    
    # Add initial balance to pending collections calculation
    pending_collections = total_orders_amount - total_collections + total_initial_balance
    
    # Get paginated recent customers with their details
    page = request.GET.get('page', 1)
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-created_at')  # Ensure default is LIFO
    
    customer_queryset = customers
    if search_query:
        customer_queryset = customer_queryset.filter(
            Q(name__icontains=search_query) |
            Q(mobile1__icontains=search_query) |
            Q(mobile2__icontains=search_query) |
            Q(address__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(id_number__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'calculated_balance':
        # Special case for balance sorting
        customer_queryset = customer_queryset.annotate(
            calculated_balance=ExpressionWrapper(
                Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('orders__orderitems__quantity') * F('orders__orderitems__price'),
                            output_field=DecimalField(max_digits=10, decimal_places=2)
                        )
                    ),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                ) - Coalesce(
                    Sum('payments__amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                ) + F('initial_balance'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).order_by('calculated_balance')
    elif sort_by == '-calculated_balance':
        # Special case for balance sorting (descending)
        customer_queryset = customer_queryset.annotate(
            calculated_balance=ExpressionWrapper(
                Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('orders__orderitems__quantity') * F('orders__orderitems__price'),
                            output_field=DecimalField(max_digits=10, decimal_places=2)
                        )
                    ),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                ) - Coalesce(
                    Sum('payments__amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                ) + F('initial_balance'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).order_by('-calculated_balance')
    elif sort_by == 'created_at':
        # Sort by creation date (oldest first)
        customer_queryset = customer_queryset.order_by('created_at')
    else:
        # Default to newest first if no specific sort is applied
        if sort_by == '-created_at':
            customer_queryset = customer_queryset.order_by(sort_by)
        else:
            # Apply the requested sort but maintain LIFO as secondary sort
            customer_queryset = customer_queryset.order_by(sort_by, '-created_at')
    
    # Annotate customers with required fields
    customer_queryset = customer_queryset.annotate(
        total_orders=Count('orders'),
        total_payments=Coalesce(
            Sum('payments__amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
        ),
        last_order_date=Max('orders__created_at'),
        last_payment_date=Max('payments__created_at'),
        calculated_balance=ExpressionWrapper(
            Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('orders__orderitems__quantity') * F('orders__orderitems__price'),
                        output_field=DecimalField(max_digits=10, decimal_places=2)
                    )
                ),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            ) - Coalesce(
                Sum('payments__amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            ) + F('initial_balance'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )
    
    # Add the outstanding balance to each customer in the queryset
    for customer in customer_queryset:
        # Make sure we're using the property that includes initial_balance
        customer.calculated_balance = customer.outstanding_balance
    
    # Paginate the customers
    paginator = Paginator(customer_queryset, 10)
    try:
        recent_customers = paginator.page(page)
    except PageNotAnInteger:
        recent_customers = paginator.page(1)
    except EmptyPage:
        recent_customers = paginator.page(paginator.num_pages)
    
    # Get paginated recent activities based on user type
    activities_page = request.GET.get('activities_page', 1)
    if user_type == 'AGENT':
        activities = get_agent_recent_activities(request.user, limit=20)  # Increased limit for pagination
    else:
        activities = get_recent_activities(company, limit=20)  # Increased limit for pagination
    
    # Paginate activities
    activities_paginator = Paginator(activities, 5)
    try:
        recent_activities = activities_paginator.page(activities_page)
    except PageNotAnInteger:
        recent_activities = activities_paginator.page(1)
    except EmptyPage:
        recent_activities = activities_paginator.page(activities_paginator.num_pages)
    
    # Initialize agent_performance
    agent_performance = []
    
    if user_type == 'COMPANY_ADMIN':
        # Add agent performance data for company admins
        agents = company.agents.select_related('user').all()
        
        for agent in agents:
            agent_orders = Order.objects.filter(company=company, agent=agent.user)
            agent_payments = Payment.objects.filter(company=company, agent=agent.user)
            
            # Calculate total order amount
            total_order_amount = agent_orders.aggregate(
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
            
            # Calculate total collections
            total_collections = agent_payments.aggregate(
                total=Coalesce(
                    Sum('amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                )
            )['total']
            
            # Calculate collection percentage
            collection_percentage = 0
            if total_order_amount > 0:
                collection_percentage = (total_collections / total_order_amount) * 100
            
            agent_performance.append({
                'agent': agent.user,
                'total_orders': agent_orders.count(),
                'total_order_amount': total_order_amount,
                'total_collections': total_collections,
                'collection_percentage': collection_percentage
            })
    
    # Add all data to context
    context = {
        'user': request.user,
        'company': company,
        'customers_count': customers.count(),
        'orders_count': orders.count(),
        'payments_count': payments.count(),
        'total_collections': total_collections,
        'pending_collections': pending_collections,
        'customers_growth': customers_growth,
        'orders_growth': orders_growth,
        'collections_growth': collections_growth,
        'current_month_orders': current_orders,
        'current_month_collections': current_collections,
        'timeframe': timeframe,
        'start_date': start_date,
        'end_date': end_date,
        'user_type': user_type,
        'recent_customers': recent_customers,
        'is_customers_paginated': recent_customers.paginator.num_pages > 1,
        'recent_activities': recent_activities,
        'search_query': search_query,
        'sort_by': sort_by,
        'agent_performance': agent_performance if user_type == 'COMPANY_ADMIN' else None,
    }
    
    return render(request, 'app/home.html', context)

def get_recent_activities(company, limit=5):
    """Get recent activities for a company."""
    activities = []
    
    # Get recent orders with timestamps
    recent_orders = Order.objects.filter(company=company).select_related('customer').order_by('-created_at')[:limit]
    for order in recent_orders:
        activities.append({
            'type': 'order',
            'message': f"New order #{order.id} created for {order.customer.name}",
            'timestamp': order.created_at,
            'amount': order.total_amount,
            'url': reverse('app:order-detail', args=[order.id])
        })
    
    # Get recent payments with timestamps
    recent_payments = Payment.objects.filter(company=company).select_related('customer').order_by('-created_at')[:limit]
    for payment in recent_payments:
        activities.append({
            'type': 'payment',
            'message': f"Payment of ₹{payment.amount_received} received from {payment.customer.name}",
            'timestamp': payment.created_at,
            'amount': payment.amount_received,
            'url': reverse('app:payment-receipt', args=[payment.id])
        })
    
    # Sort combined activities by timestamp (newest first) and limit to 5
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:limit]

def get_agent_recent_activities(agent_user, limit=5):
    """Get recent activities for an agent."""
    activities = []
    
    # Get recent orders by the agent with timestamps
    recent_orders = Order.objects.filter(agent=agent_user).select_related('customer').order_by('-created_at')[:limit]
    for order in recent_orders:
        activities.append({
            'type': 'order',
            'message': f"You created order #{order.id} for {order.customer.name}",
            'timestamp': order.created_at,
            'amount': order.total_amount,
            'url': reverse('app:order-detail', args=[order.id])
        })
    
    # Get recent payments collected by the agent with timestamps
    recent_payments = Payment.objects.filter(agent=agent_user).select_related('customer').order_by('-created_at')[:limit]
    for payment in recent_payments:
        activities.append({
            'type': 'payment',
            'message': f"You collected ₹{payment.amount_received} from {payment.customer.name}",
            'timestamp': payment.created_at,
            'amount': payment.amount_received,
            'url': reverse('app:payment-receipt', args=[payment.id])
        })
    
    # Sort combined activities by timestamp (newest first) and limit to 5
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:limit]

# Customer Views
class CustomerListView(LoginRequiredMixin, ListView):
    """View for listing customers."""
    model = Customer
    template_name = 'app/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20  # Increased to show more customers per page
    
    def get_queryset(self):
        company = self.request.user.company
        queryset = Customer.objects.filter(company=company)
        
        # Apply search filter if provided
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(mobile1__icontains=search_query) |
                Q(mobile2__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(id_number__icontains=search_query)
            )
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-created_at')  # Default to newest first (LIFO)
        
        # Annotate with calculated balance and other fields
        queryset = queryset.annotate(
            orders_total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('orders__orderitems__quantity') * F('orders__orderitems__price'),
                        output_field=DecimalField(max_digits=10, decimal_places=2)
                    )
                ),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            ),
            payments_total=Coalesce(
                Sum('payments__amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
            ),
            calculated_balance=ExpressionWrapper(
                Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('orders__orderitems__quantity') * F('orders__orderitems__price'),
                            output_field=DecimalField(max_digits=10, decimal_places=2)
                        )
                    ),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                ) - Coalesce(
                    Sum('payments__amount_received', output_field=DecimalField(max_digits=10, decimal_places=2)),
                    Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
                ) + F('initial_balance'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        
        # Apply sorting based on the annotated fields
        if sort_by == 'calculated_balance':
            queryset = queryset.order_by('calculated_balance', '-created_at')
        elif sort_by == '-calculated_balance':
            queryset = queryset.order_by('-calculated_balance', '-created_at')
        elif sort_by.startswith('-'):
            queryset = queryset.order_by(sort_by, '-created_at')
        else:
            queryset = queryset.order_by(sort_by, 'created_at')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['sort_by'] = self.request.GET.get('sort', '-created_at')
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    """View for customer details."""
    model = Customer
    template_name = 'app/customer_detail.html'
    context_object_name = 'customer'

    def get_queryset(self):
        """Filter customers by company."""
        return Customer.objects.filter(company=self.request.user.company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()

        # Get orders and payments for the customer
        orders = customer.orders.all().order_by('-order_date')
        payments = customer.payments.all().order_by('-payment_date')
        
        # Use utility functions to calculate totals
        total_amount = calculate_total_orders_amount(orders)
        total_payments = calculate_total_payments(payments)
        balance = calculate_customer_balance(customer)
        
        # Update context with new values.
        context.update({
            'orders': orders,
            'payments': payments,
            'total_amount': total_amount,
            'total_payments': total_payments,
            'balance': balance,
        })
        return context

# Helper function to generate sample CSV
def generate_sample_customer_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    # Write header with new fields
    writer.writerow([
        'name', 'address', 'mobile1', 'mobile2', 'location', 'id_number', 
        'initial_balance', 'customer_type', 'collection_frequency', 
        'collection_day_of_week', 'collection_day_of_month'
    ])
    # Write sample data with new fields
    writer.writerow([
        'John Doe', '123 Main St, Anytown', '9876543210', '9876543211', 
        'North', 'ID12345', '1000.00', 'B2C_READY_CASH', 'WEEKLY', '1', ''
    ])
    writer.writerow([
        'Jane Smith', '456 Park Ave, Sometown', '8765432100', '', 
        'South', 'ID67890', '500.00', 'B2C_EMI', 'MONTHLY', '', '15'
    ])
    writer.writerow([
        'ABC Company', '789 Business Park, Downtown', '7654321000', '7654321001', 
        'Central', 'COMP123', '2000.00', 'B2B', 'NONE', '', ''
    ])
    
    return output.getvalue()

# Helper function to process CSV and create customers
def process_customer_csv(csv_file, company):
    """Process a CSV file and create customer records."""
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    customers_created = 0
    errors = []
    
    required_fields = ['name', 'address', 'mobile1', 'location']
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header row
        try:
            # Check for missing required fields and specify which ones
            missing_fields = [field for field in required_fields if not row.get(field)]
            if missing_fields:
                fields_str = ", ".join([f"`{field}`" for field in missing_fields])
                errors.append(f"Row {row_num}: Missing required fields: {fields_str}")
                continue
            
            # Parse initial balance with fallback to 0
            initial_balance = Decimal('0.00')
            if row.get('initial_balance'):
                try:
                    initial_balance = Decimal(str(row.get('initial_balance', '0.00')))
                except (ValueError, TypeError, Decimal.InvalidOperation):
                    errors.append(f"Row {row_num}: Invalid initial balance value")
                    continue
            
            # Parse customer_type with fallback to default
            customer_type = row.get('customer_type', 'B2C_READY_CASH')
            if customer_type not in [choice[0] for choice in Customer.CUSTOMER_TYPE_CHOICES]:
                customer_type = 'B2C_READY_CASH'  # Default if invalid
            
            # Parse collection_frequency with fallback to default
            collection_frequency = row.get('collection_frequency', 'NONE')
            if collection_frequency not in [choice[0] for choice in Customer.COLLECTION_FREQUENCY_CHOICES]:
                collection_frequency = 'NONE'  # Default if invalid
            
            # Parse collection day fields
            collection_day_of_week = None
            collection_day_of_month = None
            
            if collection_frequency == 'WEEKLY' and row.get('collection_day_of_week'):
                try:
                    day_of_week = int(row.get('collection_day_of_week'))
                    if 0 <= day_of_week <= 6:  # Valid weekday range
                        collection_day_of_week = day_of_week
                except (ValueError, TypeError):
                    # Invalid value, but not critical - just leave as None
                    pass
            
            if collection_frequency == 'MONTHLY' and row.get('collection_day_of_month'):
                try:
                    day_of_month = int(row.get('collection_day_of_month'))
                    if 1 <= day_of_month <= 31:  # Valid day of month range
                        collection_day_of_month = day_of_month
                except (ValueError, TypeError):
                    # Invalid value, but not critical - just leave as None
                    pass
            
            # Create customer object with new fields
            Customer.objects.create(
                company=company,
                name=row.get('name', ''),
                address=row.get('address', ''),
                mobile1=row.get('mobile1', ''),
                mobile2=row.get('mobile2', ''),
                location=row.get('location', ''),
                id_number=row.get('id_number', ''),
                initial_balance=initial_balance,
                customer_type=customer_type,
                collection_frequency=collection_frequency,
                collection_day_of_week=collection_day_of_week,
                collection_day_of_month=collection_day_of_month
            )
            customers_created += 1
            
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    return customers_created, errors

@login_required
def download_customer_csv_template(request):
    """Download a sample CSV template for customer import."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_template.csv"'
    
    # Generate sample CSV content
    response.write(generate_sample_customer_csv())
    
    return response

class CustomerCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new customer."""
    model = Customer
    form_class = CustomerForm
    template_name = 'app/customer_form.html'
    success_url = reverse_lazy('app:customer-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['csv_form'] = CustomerCSVUploadForm()
        return context

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        messages.success(self.request, "Customer created successfully.")
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        # Check if it's a CSV upload
        if 'csv_file' in request.FILES:
            form = CustomerCSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                
                # Validate file is a CSV
                if not csv_file.name.endswith('.csv'):
                    messages.error(request, "The uploaded file must be a CSV file (.csv extension).")
                    return self.get(request, *args, **kwargs)
                
                # Process the CSV file
                try:
                    customers_created, errors = process_customer_csv(csv_file, request.user.company)
                    
                    if errors:
                        # If all rows have errors, group common errors together
                        if len(errors) > 5 and all(error.startswith("Row") and "Missing required fields" in error for error in errors[:5]):
                            # Check for pattern of missing the same fields
                            field_pattern = errors[0].split("Missing required fields: ")[1] if len(errors) > 0 else ""
                            if all(field_pattern in error for error in errors[:5]):
                                messages.warning(
                                    request, 
                                    f"Multiple rows are missing the same required fields: {field_pattern}. "
                                    f"Please check your CSV column headers and ensure they match the expected format."
                                )
                                messages.info(
                                    request,
                                    f"Download the sample CSV template for reference. "
                                    f"Required fields are: name, address, mobile1, and location."
                                )
                            else:
                                # Show the first 5 errors
                                for error in errors[:5]:
                                    messages.warning(request, error)
                                
                                if len(errors) > 5:
                                    messages.warning(request, f"...and {len(errors) - 5} more errors. Please check your CSV file format.")
                        else:
                            # Show specific errors (limited to first 5)
                            for error in errors[:5]:
                                messages.warning(request, error)
                            
                            if len(errors) > 5:
                                messages.warning(request, f"...and {len(errors) - 5} more errors")
                    
                    if customers_created > 0:
                        messages.success(request, f"{customers_created} customers imported successfully")
                        return redirect(self.success_url)
                    else:
                        messages.error(
                            request, 
                            "No customers were imported. Please check that your CSV file has the correct format "
                            "and contains valid data. Download the sample template for reference."
                        )
                
                except Exception as e:
                    messages.error(request, f"Error processing file: {str(e)}")
                    messages.info(request, "Try downloading the sample template for the correct format.")
            else:
                # Form validation error
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            
            return self.get(request, *args, **kwargs)
        
        # Otherwise, proceed with normal form submission
        return super().post(request, *args, **kwargs)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating an existing customer."""
    model = Customer
    form_class = CustomerForm
    template_name = 'app/customer_form.html'
    
    def get_queryset(self):
        """Filter customers by company."""
        return Customer.objects.filter(company=self.request.user.company)
    
    def get_success_url(self):
        """Return to customer detail view after successful update."""
        return reverse_lazy('app:customer-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f"Customer '{self.object.name}' updated successfully.")
        return super().form_valid(form)

@login_required
def customer_delete(request, pk):
    """Delete a customer and all associated data."""
    customer = get_object_or_404(Customer, pk=pk, company=request.user.company)
    
    if request.method == 'POST':
        name = customer.name
        try:
            # Use transaction to ensure all related data is deleted properly
            with transaction.atomic():
                customer.delete()
                messages.success(request, f"Customer '{name}' has been deleted successfully.")
                return redirect('app:customer-list')
        except Exception as e:
            messages.error(request, f"Error deleting customer: {str(e)}")
            return redirect('app:customer-detail', pk=pk)
    
    # If it's not a POST request, redirect to the detail page
    return redirect('app:customer-detail', pk=pk)

# Order Views
class OrderListView(LoginRequiredMixin, ListView):
    """View for listing orders."""
    model = Order
    template_name = 'app/order_list.html'
    context_object_name = 'orders'
    ordering = ['-order_date']

    def get_queryset(self):
        """Filter orders by company."""
        return Order.objects.filter(company=self.request.user.company)

class OrderDetailView(LoginRequiredMixin, DetailView):
    """View for order details."""
    model = Order
    template_name = 'app/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        """Filter orders by company."""
        return Order.objects.filter(company=self.request.user.company)

class OrderCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new order."""
    model = Order
    form_class = OrderForm
    template_name = 'app/order_form.html'
    success_url = reverse_lazy('app:order-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        customer_id = self.kwargs.get('customer_id')
        if customer_id:
            initial['customer'] = customer_id
        return initial

    def get_success_url(self):
        if 'customer_id' in self.kwargs:
            return reverse_lazy('app:customer-detail', kwargs={'pk': self.kwargs['customer_id']})
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = OrderItemFormSet(self.request.POST)
        else:
            data['items'] = OrderItemFormSet()
        
        # Add available items for the company
        data['available_items'] = Item.objects.filter(
            company=self.request.user.company,
            is_active=True
        ).order_by('name')
        
        return data

    def form_valid(self, form):
        """Set the company and agent before saving."""
        context = self.get_context_data()
        formset = context['items']
        
        form.instance.company = self.request.user.company
        form.instance.agent = self.request.user
        
        try:
            with transaction.atomic():
                self.object = form.save()
                
                if formset.is_valid():
                    formset.instance = self.object
                    formset.save()
                else:
                    raise ValueError("Formset validation failed")
                    
                messages.success(self.request, 'Order created successfully.')
                return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error creating order: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data()
        context['form'] = form
        messages.error(self.request, 'Please correct the errors below.')
        return self.render_to_response(context)

# Payment Views
class PaymentListView(LoginRequiredMixin, ListView):
    """View for listing payments."""
    model = Payment
    template_name = 'app/payment_list.html'
    context_object_name = 'payments'
    ordering = ['-payment_date']

    def get_queryset(self):
        """Filter payments by company."""
        return Payment.objects.filter(company=self.request.user.company)

class PaymentCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new payment."""
    model = Payment
    form_class = PaymentForm
    template_name = 'app/payment_form.html'
    success_url = reverse_lazy('app:payment-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        customer_id = self.kwargs.get('customer_id')
        if customer_id:
            initial['customer'] = customer_id
        return initial

    def get_success_url(self):
        if 'customer_id' in self.kwargs:
            return reverse_lazy('app:customer-detail', kwargs={'pk': self.kwargs['customer_id']})
        return super().get_success_url()

    def form_valid(self, form):
        """Set the company and agent before saving."""
        form.instance.company = self.request.user.company
        form.instance.agent = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Payment recorded successfully')
        return response

# Add a new view for receipts
class PaymentReceiptView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = 'app/receipts/payment_receipt.html'
    context_object_name = 'payment'

    def get_queryset(self):
        """Filter payments by company."""
        return Payment.objects.filter(company=self.request.user.company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Payment Receipt',
            'doc_type': 'Receipt',
            'amount': self.object.amount_received,
            'customer': self.object.customer,
            'document_number': self.object.id,
            'back_url': reverse_lazy('app:payment-list')
        })
        return context

class OrderInvoiceView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'app/receipts/order_invoice.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Order Invoice',
            'doc_type': 'Invoice',
            'amount': self.object.total_amount,
            'customer': self.object.customer,
            'document_number': self.object.id,
            'back_url': reverse_lazy('app:order-detail', kwargs={'pk': self.object.pk})
        })
        return context

# Public, non-login required invoice view
class PublicOrderInvoiceView(DetailView):
    model = Order
    template_name = 'app/receipts/order_invoice.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        # No company filtering - open to public access
        return Order.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Order Invoice',
            'doc_type': 'Invoice',
            'amount': self.object.total_amount,
            'customer': self.object.customer,
            'document_number': self.object.id,
            'back_url': reverse('app:order-invoice-public', kwargs={'pk': self.object.pk}),
            'is_public': True
        })
        return context

@login_required
def get_customer_items(request, customer_id):
    """API endpoint to get customer-specific item prices."""
    try:
        customer = Customer.objects.get(
            id=customer_id,
            company=request.user.company
        )
        
        # Get all customer-specific prices
        customer_prices = CustomerItemPrice.objects.filter(
            customer=customer
        ).select_related('item')
        
        # Create a dictionary of item prices
        price_data = {}
        for cp in customer_prices:
            price_data[cp.item.id] = {
                'price': float(cp.price),
                'last_ordered': cp.item.order_items.filter(
                    order__customer=customer
                ).order_by('-order__order_date').first().order.order_date.strftime('%Y-%m-%d') if cp.item.order_items.filter(order__customer=customer).exists() else None
            }
        
        return JsonResponse(price_data)
        
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class BulkOrderCreateView(LoginRequiredMixin, View):
    """View for creating multiple orders at once."""
    template_name = 'app/bulk_order_form.html'

    def get(self, request):
        form = BulkOrderForm(company=request.user.company)
        template_id = request.GET.get('template')
        initial_items = []
        
        if template_id:
            try:
                template = OrderTemplate.objects.get(
                    id=template_id,
                    company=request.user.company
                )
                for item in template.template_items.all():
                    initial_items.append({
                        'item': item.item,
                        'quantity': item.quantity,
                        'price': item.default_price,
                        'remarks': item.remarks
                    })
            except OrderTemplate.DoesNotExist:
                messages.error(request, 'Template not found.')
        
        return render(request, self.template_name, {
            'form': form,
            'initial_items': initial_items
        })

    def post(self, request):
        form = BulkOrderForm(request.POST, company=request.user.company)
        if form.is_valid():
            try:
                with transaction.atomic():
                    customer = form.cleaned_data['customer']
                    order_date = form.cleaned_data['order_date']
                    delivery_date = form.cleaned_data.get('delivery_date')  # Optional field
                    remarks = form.cleaned_data['remarks']
                    items_data = json.loads(form.cleaned_data['items_data'])
                    
                    # Create the order
                    order = Order.objects.create(
                        customer=customer,
                        company=request.user.company,
                        agent=request.user.agent_profile if hasattr(request.user, 'agent_profile') else None,
                        order_date=order_date,
                        delivery_date=delivery_date,
                        remarks=remarks
                    )
                    
                    # Add order items
                    for item_data in items_data:
                        OrderItem.objects.create(
                            order=order,
                            item_id=item_data['item_id'],
                            quantity=item_data['quantity'],
                            price=item_data['price'],
                            remarks=item_data.get('remarks', '')
                        )
                    
                    messages.success(request, f'Order #{order.id} created successfully.')
                    return JsonResponse({
                        'status': 'success',
                        'message': f'Order #{order.id} created successfully.',
                        'redirect_url': reverse('app:order-detail', args=[order.id])
                    })
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data.',
                'errors': form.errors
            }, status=400)

class OrderTemplateListView(LoginRequiredMixin, ListView):
    """View for listing order templates."""
    model = OrderTemplate
    template_name = 'app/order_template_list.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        return OrderTemplate.objects.filter(company=self.request.user.company)

class OrderTemplateCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new order template."""
    model = OrderTemplate
    form_class = OrderTemplateForm
    template_name = 'app/order_template_form.html'
    success_url = reverse_lazy('app:order-template-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = OrderTemplateItemFormSet(self.request.POST)
        else:
            context['formset'] = OrderTemplateItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        with transaction.atomic():
            form.instance.company = self.request.user.company
            form.instance.created_by = self.request.user
            self.object = form.save()
            
            if formset.is_valid():
                formset.instance = self.object
                formset.save()
                messages.success(self.request, 'Order template created successfully.')
                return super().form_valid(form)
            else:
                return self.form_invalid(form)

class OrderTemplateUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating an order template."""
    model = OrderTemplate
    form_class = OrderTemplateForm
    template_name = 'app/order_template_form.html'
    success_url = reverse_lazy('app:order-template-list')

    def get_queryset(self):
        return OrderTemplate.objects.filter(company=self.request.user.company)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = OrderTemplateItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['formset'] = OrderTemplateItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        with transaction.atomic():
            form.instance.company = self.request.user.company
            self.object = form.save()
            
            if formset.is_valid():
                formset.instance = self.object
                formset.save()
                messages.success(self.request, 'Order template updated successfully.')
                return super().form_valid(form)
            else:
                return self.form_invalid(form)

@login_required
def order_templates_api(request):
    """API endpoint for order templates."""
    templates = OrderTemplate.objects.filter(
        company=request.user.company,
        is_active=True
    ).annotate(
        items_count=Count('template_items'),
        total_value=Sum(F('template_items__quantity') * F('template_items__default_price'))
    )
    
    data = []
    for template in templates:
        items = []
        for item in template.template_items.all():
            items.append({
                'id': item.item.id,
                'name': item.item.name,
                'quantity': float(item.quantity),
                'price': float(item.default_price),
                'remarks': item.remarks or ''
            })
        
        data.append({
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'items_count': template.items_count,
            'total_value': float(template.total_value or 0),
            'items': items
        })
    
    return JsonResponse({'templates': data})

@login_required
def import_items_api(request):
    """API endpoint to import items from file."""
    if request.method != 'POST' or 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
    
    file = request.FILES['file']
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return JsonResponse({'error': 'Unsupported file format'}, status=400)
        
        required_columns = ['item_id', 'quantity', 'price']
        if not all(col in df.columns for col in required_columns):
            return JsonResponse({'error': 'Missing required columns'}, status=400)
        
        items = []
        for _, row in df.iterrows():
            try:
                item = Item.objects.get(
                    id=row['item_id'],
                    company=request.user.company
                )
                items.append({
                    'id': item.id,
                    'name': item.name,
                    'quantity': float(row['quantity']),
                    'price': float(row['price']),
                    'unit': item.unit
                })
            except Item.DoesNotExist:
                continue
        
        return JsonResponse(items, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def create_item(request):
    """API endpoint to create a new item."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        # Get data from request
        name = request.POST.get('name')
        unit = request.POST.get('unit')
        default_price = request.POST.get('default_price')
        description = request.POST.get('description', '')
        
        # Validate required fields
        if not all([name, unit, default_price]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Create new item
        item = Item.objects.create(
            company=request.user.company,
            name=name,
            unit=unit,
            default_price=default_price,
            description=description
        )
        
        # Return success response
        return JsonResponse({
            'id': item.id,
            'name': item.name,
            'unit': item.unit,
            'default_price': float(item.default_price)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# Bank Management Views
class BankListView(LoginRequiredMixin, ListView):
    """View for listing company bank accounts."""
    model = Bank
    template_name = 'app/bank_list.html'
    context_object_name = 'banks'
    
    def get_queryset(self):
        """Filter banks by company."""
        return Bank.objects.filter(company=self.request.user.company)

class BankCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new bank account."""
    model = Bank
    form_class = BankForm
    template_name = 'app/bank_form.html'
    success_url = reverse_lazy('app:bank-list')
    
    def form_valid(self, form):
        """Set the company before saving."""
        form.instance.company = self.request.user.company
        
        # Use transaction to ensure integrity
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, 'Bank account created successfully.')
            return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class BankUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating a bank account."""
    model = Bank
    form_class = BankForm
    template_name = 'app/bank_form.html'
    success_url = reverse_lazy('app:bank-list')
    
    def get_queryset(self):
        """Filter banks by company."""
        return Bank.objects.filter(company=self.request.user.company)
    
    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, 'Bank account updated successfully.')
            return response

@login_required
def bank_delete(request, pk):
    """Delete a bank account."""
    bank = get_object_or_404(Bank, pk=pk, company=request.user.company)
    
    if request.method == 'POST':
        # Check if bank has payments
        if bank.payments.exists():
            messages.error(request, f"Cannot delete bank '{bank.name}' because it has payments associated with it.")
            return redirect('app:bank-list')
        
        try:
            with transaction.atomic():
                bank_name = bank.name
                bank.delete()
                messages.success(request, f"Bank account '{bank_name}' has been deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting bank account: {str(e)}")
    
    return redirect('app:bank-list')
