from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Customer, Order, OrderItem, Payment
from django.db.models import Sum, Count
from django.contrib import messages
from django.db import transaction
from .forms import OrderForm, OrderItemFormSet, PaymentForm
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    """Home page view."""
    context = {
        'user': request.user
    }
    
    if request.user.is_authenticated:
        if request.user.user_type == 'COMPANY_ADMIN':
            # Get counts for company admin
            context.update({
                'customers_count': Customer.objects.filter(company=request.user.company).count(),
                'orders_count': Order.objects.filter(company=request.user.company).count(),
                'payments_count': Payment.objects.filter(company=request.user.company).count(),
                'recent_activities': get_recent_activities(request.user.company)
            })
        elif request.user.user_type == 'AGENT':
            # Get counts for agent
            context.update({
                'agent_orders_count': Order.objects.filter(agent=request.user.agent_profile).count(),
                'agent_payments_count': Payment.objects.filter(agent=request.user.agent_profile).count(),
                'agent_recent_activities': get_agent_recent_activities(request.user.agent_profile)
            })
    
    return render(request, 'app/home.html', context)

def get_recent_activities(company, limit=5):
    """Get recent activities for a company."""
    activities = []
    
    # Get recent orders
    recent_orders = Order.objects.filter(company=company).order_by('-created_at')[:limit]
    for order in recent_orders:
        activities.append(f"New order #{order.id} created for {order.customer.name}")
    
    # Get recent payments
    recent_payments = Payment.objects.filter(company=company).order_by('-created_at')[:limit]
    for payment in recent_payments:
        activities.append(f"Payment of ₹{payment.amount_received} received from {payment.customer.name}")
    
    # Sort combined activities by date (newest first) and limit to 5
    return sorted(activities, reverse=True)[:limit]

def get_agent_recent_activities(agent, limit=5):
    """Get recent activities for an agent."""
    activities = []
    
    # Get recent orders by the agent
    recent_orders = Order.objects.filter(agent=agent).order_by('-created_at')[:limit]
    for order in recent_orders:
        activities.append(f"You created order #{order.id} for {order.customer.name}")
    
    # Get recent payments collected by the agent
    recent_payments = Payment.objects.filter(agent=agent).order_by('-created_at')[:limit]
    for payment in recent_payments:
        activities.append(f"You collected ₹{payment.amount_received} from {payment.customer.name}")
    
    # Sort combined activities by date (newest first) and limit to 5
    return sorted(activities, reverse=True)[:limit]

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
        return data

    def form_valid(self, form):
        """Set the company and agent before saving."""
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
