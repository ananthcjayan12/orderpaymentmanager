from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Registration URLs
    path('register/company/', views.CompanyRegistrationView.as_view(), name='register_company'),
    path('register/agent/', views.AgentRegistrationView.as_view(), name='register_agent'),
    
    # Dashboard URLs
    path('dashboard/company/', views.company_dashboard, name='company_dashboard'),
    path('dashboard/agent/', views.agent_dashboard, name='agent_dashboard'),
    
    # Agent Management URLs
    path('agents/', views.AgentListView.as_view(), name='agent_list'),
] 