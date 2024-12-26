from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    # Customer URLs
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer-create'),
    
    # Order URLs
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/create/<int:customer_id>/', views.OrderCreateView.as_view(), name='order-create-for-customer'),
    path('orders/<int:pk>/invoice/', views.OrderInvoiceView.as_view(), name='order-invoice'),
    
    # Payment URLs
    path('payments/', views.PaymentListView.as_view(), name='payment-list'),
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment-create'),
    path('payments/create/<int:customer_id>/', views.PaymentCreateView.as_view(), name='payment-create-for-customer'),
    path('payments/<int:pk>/receipt/', views.PaymentReceiptView.as_view(), name='payment-receipt'),
] 