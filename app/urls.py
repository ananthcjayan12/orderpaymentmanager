from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Reports
    path('reports/', views.report_dashboard, name='reports'),
    
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer-create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<int:pk>/update/', views.CustomerUpdateView.as_view(), name='customer-update'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer-delete'),
    path('customers/csv-template/', views.download_customer_csv_template, name='customer-csv-template'),
    
    # Banks
    path('banks/', views.BankListView.as_view(), name='bank-list'),
    path('banks/create/', views.BankCreateView.as_view(), name='bank-create'),
    path('banks/<int:pk>/update/', views.BankUpdateView.as_view(), name='bank-update'),
    path('banks/<int:pk>/delete/', views.bank_delete, name='bank-delete'),
    
    # Orders
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/create/bulk/', views.BulkOrderCreateView.as_view(), name='bulk-order-create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/invoice/', views.OrderInvoiceView.as_view(), name='order-invoice'),
    
    # Public (no login required) invoice access
    path('invoice/<int:pk>/', views.PublicOrderInvoiceView.as_view(), name='order-invoice-public'),
    
    # Order Templates
    path('templates/', views.OrderTemplateListView.as_view(), name='order-template-list'),
    path('templates/create/', views.OrderTemplateCreateView.as_view(), name='order-template-create'),
    path('templates/<int:pk>/edit/', views.OrderTemplateUpdateView.as_view(), name='order-template-edit'),
    path('templates/api/', views.order_templates_api, name='order-templates-api'),
    
    # Payments
    path('payments/', views.PaymentListView.as_view(), name='payment-list'),
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment-create'),
    path('payments/<int:pk>/receipt/', views.PaymentReceiptView.as_view(), name='payment-receipt'),
    
    # Customer-specific URLs
    path('customers/<int:customer_id>/orders/create/', views.OrderCreateView.as_view(), name='customer-order-create'),
    path('customers/<int:customer_id>/payments/create/', views.PaymentCreateView.as_view(), name='customer-payment-create'),
    
    # API endpoints
    path('api/customer/<int:customer_id>/items/', views.get_customer_items, name='customer-items'),
    path('api/items/create/', views.create_item, name='item-create'),
    
    # Add these new URL patterns
    path('defaulters/', views.DefaultersListView.as_view(), name='defaulters-list'),
    path('upcoming-payments/', views.UpcomingPaymentsView.as_view(), name='upcoming-payments'),
] 