from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('daily/', views.DailySalesReportView.as_view(), name='daily-sales'),
    path('monthly/', views.MonthlyReportView.as_view(), name='monthly-report'),
    path('date-range/', views.DateRangeReportView.as_view(), name='date-range'),
] 