# Django-Centric Product Requirements Document (PRD)

This PRD is designed to be **easily understandable** by both humans and Large Language Models (LLMs). It outlines the requirements for an **Order & Payment Management** web application, built using the **Django** framework.


**File Structure**: *Order & Payment Manager (Django)*

├── app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── core
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── filestruct.txt
├── instructions.md
├── manage.py
└── setup_instructions.md
## 1. Product Overview

**Product Name**: *Order & Payment Manager (Django)*

### Objective
Replace the manual ledger-based system with a Django web application that handles:
1. **Customer Management** (details, outstanding balances)  
2. **Order Management** (multiple items, per-customer pricing)  
3. **Payment Tracking** (cash received, balance updates, instant receipt generation)  
4. **Reporting & Analytics** (daily, monthly, date-range reports, defaulters, etc.)

### Key Technologies
- **Python** (3.8+ recommended)  
- **Django** (4.x or latest stable release)  
- **PostgreSQL** (preferred; MySQL or SQLite if smaller-scale)  
- **HTML / CSS / JavaScript** (e.g., Bootstrap for frontend)

## 2. Architecture & High-Level Design

### Django Project Structure
- Use `django-admin startproject order_payment_manager`
- Create separate apps: `customers`, `orders`, `payments`, and `reports` (modular approach)

### Recommended Apps
- **customers**: Manages customer data, including defaulter logic
- **orders**: Handles order creation, multiple items, and per-customer pricing
- **payments**: Tracks cash received, balances, and receipt generation
- **reports**: Provides daily, monthly, and custom reports, plus defaulter insights

### Database
- **PostgreSQL** is recommended for scalability and concurrency
- Use Django's ORM for model definitions and queries

### Authentication & Authorization
- Django's built-in auth system
- Define groups or roles: **Admin** (full access) and **Staff** (restricted access)

## 3. Detailed Requirements & Implementation Notes

Below are the core functional requirements adapted to Django's approach.

### 3.1 Customer Management

#### Model Structure (`customers/models.py`)
```python
from django.db import models

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
        # Implementation detail:
        # Calculate via sum of orders - sum of payments,
        # or an alternative approach that updates a stored field on every change.
        pass
```

#### Key Points
- Fields: name, address, mobile1, mobile2, location, id_number
- Outstanding Balance Calculation: Could be dynamic (sum orders minus payments) or stored/updated on each transaction

#### Views/URLs
- `customers/views.py`: Could include CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDetailView
- Use Class-Based Views (CBVs) or Django REST Framework (if a RESTful API is desired)

#### Templates
- `customers/templates/customers/` with customer_list.html, customer_form.html, etc.

### 3.2 Order Management

#### Model Structure (`orders/models.py`)
```python
from django.db import models
from customers.models import Customer

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateField()
    remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return sum(item.line_total for item in self.orderitems.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='orderitems')
    item_name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    @property
    def line_total(self):
        return (self.price or 0) * (self.quantity or 0)
```

#### Key Points
- Order: Linked to Customer; has order_date, remarks, and a computed total_amount from child items
- OrderItem: Linked to Order, with item_name, quantity, price
- Reusing Price: Store or recall the "last used price" per (customer, item_name) to auto-fill on new items if desired

#### Views/URLs
- `orders/views.py`: Could have OrderListView, OrderCreateView, OrderDetailView, OrderUpdateView
- Potential use of inline formsets for multiple OrderItem entries under one order

#### Templates
- `orders/templates/orders/` for listing, creating, editing

### 3.3 Payment & Receipt Management

#### Model Structure (`payments/models.py`)
```python
from django.db import models
from customers.models import Customer

class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField(auto_now_add=True)
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer.name} - {self.amount_received} on {self.payment_date}"
```

#### Key Points
- Payment: Links to a Customer, records date, amount, and notes
- Updating Balance: Each Payment can trigger an update or recalculation of the customer's outstanding balance (via signals or manual logic)

#### Receipt Generation
- Use Django templates to render a receipt.html
- Convert to PDF using WeasyPrint, xhtml2pdf, or ReportLab
- Provide a "Print" or "Download PDF" button after payment is saved

#### Views
- `payments/views.py`: Could have PaymentCreateView to handle new payments and generate receipts

#### Example Workflow
1. User creates a new payment
2. System saves it to the DB
3. Customer's outstanding balance is updated
4. A receipt is generated (HTML/PDF)
5. User prints or downloads the receipt

### 3.4 Reporting & Analytics

#### Approaches
- A separate reports app for queries across Order, Payment, Customer
- Or integrate reporting logic into each relevant app

#### Core Reports
- Customer-wise Report
  - Summaries: total orders, total paid, outstanding balance
  - Optimize queries with select_related / prefetch_related
- Daily & Monthly Reports
  - Filter by order_date or payment_date
- Date Range
  - Let users set a custom start_date and end_date
- Defaulters Report
  - Customers who missed two consecutive payments or exceed a credit threshold
  - Implementation details can vary (e.g., track "billing cycles" or "missed payments")

#### Views/URLs
- `reports/views.py`: Could have DailyReportView, MonthlyReportView, DateRangeReportView, DefaulterReportView

#### Templates
- `reports/templates/reports/` to show tables, filters, charts, etc.

### 3.5 Reminder / Notifications
- Maintain a defaulters view or model
- Optional: Integrate SMS (e.g., Twilio) or email (e.g., SendGrid) for overdue reminders

## 4. User Roles & Permissions

### Admin
- Superuser or assigned "admin" group
- Full CRUD across apps
- Access to Django Admin panel

### Staff
- Custom group or assigned permissions
- Limited CRUD (e.g., can't delete old records)
- Restrict advanced settings or certain data fields

## 5. Development Steps

### Environment Setup
1. Install Python 3.8+
2. Create a virtual environment and install: `pip install django psycopg2-binary`
3. Initialize Git for version control

### Create Django Project & Apps
```bash
django-admin startproject order_payment_manager
cd order_payment_manager
python manage.py startapp customers
python manage.py startapp orders
python manage.py startapp payments
python manage.py startapp reports
```

### Configure Settings
In `settings.py`:
- Add your apps to INSTALLED_APPS
- Configure DATABASES for PostgreSQL
- Set TIME_ZONE, LANGUAGE_CODE, etc.
- Configure static and media file handling if needed

### Define Models
- Implement Customer, Order, OrderItem, Payment
- Include model methods or properties for calculations (e.g., total amounts, balances)

### Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Admin Configuration
In each app's `admin.py`, register your models:
```python
from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile1', 'location', 'outstanding_balance')
```
Repeat for Order, OrderItem, Payment.

### Views & URLs
- Implement class-based or function-based views for CRUD operations
- Define URL patterns in urls.py and reference them in the main order_payment_manager/urls.py

### Templates
- Use Django Template Language (DTL) or a front-end framework (React, Vue)
- Create forms for adding/editing customers, orders, and payments
- Add a specialized template for receipts (potentially converting to PDF)

### Reporting Logic
- Implement logic in reports/views.py
- Use Django's aggregation and filtering for daily, monthly, date-range, and defaulter reports

### Testing
- Write unit tests for models, views, and forms
- Use pytest or Django's built-in test framework
- Ensure coverage for edge cases (e.g., partial payments, order with multiple items)

### Deployment
- Use Gunicorn or uWSGI + Nginx for production environments
- Configure environment variables (DB credentials, secret keys)
- Set DEBUG = False for production

## 6. Acceptance Criteria

### Customers
- Can add, edit, view, search customers
- Shows real-time outstanding balance on customer detail pages

### Orders
- Can create orders with multiple items
- Price can be updated later and reflected in the final total
- Ability to store/reuse custom item prices per customer (optional)

### Payments & Receipts
- Record full or partial payments
- Adjust outstanding balances automatically
- Generate a printable/downloadable receipt instantly upon saving a payment

### Reports
- Daily, monthly, and custom date range aggregation
- Defaulter list for customers missing more than two consecutive payments
- Filtering by highest outstanding amounts or similar KPIs

### User Experience
- Simple, intuitive UI with minimal steps
- Clear navigation to orders, payments, and reports
- Optional notifications or reminders for defaulters
