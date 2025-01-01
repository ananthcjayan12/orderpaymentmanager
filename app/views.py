from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Customer, Order, OrderItem, Payment, Item, CustomerItemPrice, OrderTemplate
from django.db.models import Sum, Count
from django.contrib import messages
from django.db import transaction
from .forms import OrderForm, OrderItemFormSet, PaymentForm, BulkOrderForm, OrderTemplateForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import F
import json
import pandas as pd

@login_required
def home(request):
    """Home page view."""
    context = {
        'user': request.user
    }
    
    if request.user.is_authenticated:
        if request.user.user_type == 'COMPANY_ADMIN':
            # Get base counts
            company = request.user.company
            customers = Customer.objects.filter(company=company)
            orders = Order.objects.filter(company=company)
            payments = Payment.objects.filter(company=company)
            
            # Calculate totals
            total_collections = payments.aggregate(total=Sum('amount_received'))['total'] or 0
            total_orders = orders.aggregate(total=Sum(
                F('orderitems__quantity') * F('orderitems__price')
            ))['total'] or 0
            pending_collections = total_orders - total_collections
            
            # Get month-over-month growth
            last_month = timezone.now() - timezone.timedelta(days=30)
            previous_month = last_month - timezone.timedelta(days=30)
            
            current_month_orders = orders.filter(created_at__gte=last_month).count()
            previous_month_orders = orders.filter(
                created_at__gte=previous_month,
                created_at__lt=last_month
            ).count()
            
            current_month_collections = payments.filter(created_at__gte=last_month).aggregate(
                total=Sum('amount_received')
            )['total'] or 0
            previous_month_collections = payments.filter(
                created_at__gte=previous_month,
                created_at__lt=last_month
            ).aggregate(total=Sum('amount_received'))['total'] or 0
            
            # Calculate growth percentages
            orders_growth = (
                ((current_month_orders - previous_month_orders) / previous_month_orders * 100)
                if previous_month_orders > 0 else 0
            )
            collections_growth = (
                ((current_month_collections - previous_month_collections) / previous_month_collections * 100)
                if previous_month_collections > 0 else 0
            )
            
            # Get agent performance data
            agent_performance = []
            for agent in company.agents.all():
                agent_collections = payments.filter(agent=agent).aggregate(
                    total=Sum('amount_received')
                )['total'] or 0
                agent_performance.append({
                    'name': agent.user.get_full_name() or agent.user.username,
                    'collections': agent_collections
                })
            
            # Sort agents by performance
            agent_performance.sort(key=lambda x: x['collections'], reverse=True)
            
            context.update({
                'customers_count': customers.count(),
                'orders_count': orders.count(),
                'payments_count': payments.count(),
                'total_collections': total_collections,
                'pending_collections': pending_collections,
                'orders_growth': orders_growth,
                'collections_growth': collections_growth,
                'agent_performance': agent_performance,
                'recent_activities': get_recent_activities(company)
            })
            
        elif request.user.user_type == 'AGENT':
            agent = request.user.agent_profile
            agent_orders = Order.objects.filter(agent=agent)
            agent_payments = Payment.objects.filter(agent=agent)
            
            # Calculate agent's month-over-month growth
            last_month = timezone.now() - timezone.timedelta(days=30)
            previous_month = last_month - timezone.timedelta(days=30)
            
            current_month_orders = agent_orders.filter(created_at__gte=last_month).count()
            previous_month_orders = agent_orders.filter(
                created_at__gte=previous_month,
                created_at__lt=last_month
            ).count()
            
            current_month_collections = agent_payments.filter(created_at__gte=last_month).aggregate(
                total=Sum('amount_received')
            )['total'] or 0
            previous_month_collections = agent_payments.filter(
                created_at__gte=previous_month,
                created_at__lt=last_month
            ).aggregate(total=Sum('amount_received'))['total'] or 0
            
            # Calculate growth percentages
            orders_growth = (
                ((current_month_orders - previous_month_orders) / previous_month_orders * 100)
                if previous_month_orders > 0 else 0
            )
            collections_growth = (
                ((current_month_collections - previous_month_collections) / previous_month_collections * 100)
                if previous_month_collections > 0 else 0
            )
            
            context.update({
                'agent_orders_count': agent_orders.count(),
                'agent_payments_count': agent_payments.count(),
                'orders_growth': orders_growth,
                'collections_growth': collections_growth,
                'agent_recent_activities': get_agent_recent_activities(agent)
            })
    
    return render(request, 'app/home.html', context)

def get_recent_activities(company, limit=5):
    """Get recent activities for a company."""
    activities = []
    
    # Get recent orders with timestamps
    recent_orders = Order.objects.filter(company=company).order_by('-created_at')[:limit]
    for order in recent_orders:
        activities.append({
            'type': 'order',
            'message': f"New order #{order.id} created for {order.customer.name}",
            'timestamp': order.created_at,
            'amount': order.total_amount
        })
    
    # Get recent payments with timestamps
    recent_payments = Payment.objects.filter(company=company).order_by('-created_at')[:limit]
    for payment in recent_payments:
        activities.append({
            'type': 'payment',
            'message': f"Payment of ₹{payment.amount_received} received from {payment.customer.name}",
            'timestamp': payment.created_at,
            'amount': payment.amount_received
        })
    
    # Sort combined activities by timestamp (newest first) and limit to 5
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:limit]

def get_agent_recent_activities(agent, limit=5):
    """Get recent activities for an agent."""
    activities = []
    
    # Get recent orders by the agent with timestamps
    recent_orders = Order.objects.filter(agent=agent).order_by('-created_at')[:limit]
    for order in recent_orders:
        activities.append({
            'type': 'order',
            'message': f"You created order #{order.id} for {order.customer.name}",
            'timestamp': order.created_at,
            'amount': order.total_amount
        })
    
    # Get recent payments collected by the agent with timestamps
    recent_payments = Payment.objects.filter(agent=agent).order_by('-created_at')[:limit]
    for payment in recent_payments:
        activities.append({
            'type': 'payment',
            'message': f"You collected ₹{payment.amount_received} from {payment.customer.name}",
            'timestamp': payment.created_at,
            'amount': payment.amount_received
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
    ordering = ['name']

    def get_queryset(self):
        """Filter customers by company."""
        return Customer.objects.filter(company=self.request.user.company)

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
        context['orders'] = customer.orders.all().order_by('-order_date')
        context['payments'] = customer.payments.all().order_by('-payment_date')
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new customer."""
    model = Customer
    template_name = 'app/customer_form.html'
    fields = ['name', 'address', 'mobile1', 'mobile2', 'location', 'id_number']
    success_url = reverse_lazy('app:customer-list')

    def form_valid(self, form):
        """Set the company before saving."""
        form.instance.company = self.request.user.company
        return super().form_valid(form)

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
        form.instance.agent = self.request.user.agent_profile
        
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
        form.instance.agent = self.request.user.agent_profile
        response = super().form_valid(form)
        messages.success(self.request, 'Payment recorded successfully')
        return response

# Add a new view for receipts
class PaymentReceiptView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = 'app/receipts/payment_receipt.html'
    context_object_name = 'payment'

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
                    remarks = form.cleaned_data['remarks']
                    items_data = json.loads(form.cleaned_data['items_data'])
                    
                    # Create the order
                    order = Order.objects.create(
                        customer=customer,
                        company=request.user.company,
                        agent=request.user.agent_profile if hasattr(request.user, 'agent_profile') else None,
                        order_date=order_date,
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
