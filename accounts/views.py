from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, ListView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from .forms import (
    EmailAuthenticationForm,
    CompanyRegistrationForm,
    CompanyAdminRegistrationForm,
    AgentRegistrationForm,
    AgentProfileForm
)
from .models import Company, Agent
from django.db import models

class CustomLoginView(LoginView):
    """Custom login view that uses email authentication."""
    form_class = EmailAuthenticationForm
    template_name = 'accounts/auth/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        """Return the main dashboard URL."""
        return reverse_lazy('app:home')

    def form_valid(self, form):
        """Handle successful login."""
        auth_login(self.request, form.get_user())
        return redirect(self.get_success_url())

def logout_view(request):
    """Logout view."""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('accounts:login')

class CompanyRegistrationView(CreateView):
    """View for company registration."""
    template_name = 'accounts/auth/company_register.html'
    form_class = CompanyRegistrationForm
    success_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'user_form' not in context:
            context['user_form'] = CompanyAdminRegistrationForm(self.request.POST or None)
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        user_form = CompanyAdminRegistrationForm(request.POST, request.FILES)

        if form.is_valid() and user_form.is_valid():
            return self.form_valid(form, user_form)
        else:
            return self.form_invalid(form, user_form)

    def form_valid(self, form, user_form):
        """Handle valid form data."""
        try:
            with transaction.atomic():
                # Create company first
                company = form.save()
                
                # Create admin user
                admin = user_form.save(commit=False)
                admin.user_type = 'COMPANY_ADMIN'
                admin.company = company  # Set the company before saving
                admin.save()
                
                messages.success(
                    self.request,
                    'Company registered successfully. Please login with your email and password.'
                )
                return redirect(self.success_url)
                
        except Exception as e:
            messages.error(
                self.request,
                f'Error registering company: {str(e)}'
            )
            return self.form_invalid(form, user_form)

    def form_invalid(self, form, user_form):
        """Handle invalid form data."""
        return self.render_to_response(
            self.get_context_data(
                form=form,
                user_form=user_form
            )
        )

    def send_welcome_email(self, company, admin):
        """Send welcome email to company admin."""
        # TODO: Implement email sending
        pass

class AgentRegistrationView(LoginRequiredMixin, CreateView):
    """View for agent registration by company admin."""
    template_name = 'accounts/auth/agent_register.html'
    form_class = AgentRegistrationForm
    success_url = reverse_lazy('accounts:agent_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'profile_form' not in context:
            context['profile_form'] = AgentProfileForm()
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST requests."""
        self.object = None
        user_form = self.get_form()
        profile_form = AgentProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            return self.form_valid(user_form, profile_form)
        else:
            return self.form_invalid(user_form, profile_form)

    def form_valid(self, user_form, profile_form):
        """Handle valid form data."""
        try:
            with transaction.atomic():
                # Create user
                user = user_form.save(commit=False)
                user.user_type = 'AGENT'
                user.company = self.request.user.company
                user.save()
                
                # Create agent profile
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.company = self.request.user.company
                profile.save()
                
                self.object = user
                
                # Send welcome email
                self.send_welcome_email(profile)
                
                messages.success(
                    self.request,
                    'Agent registered successfully. Login credentials have been sent to their email.'
                )
                return redirect(self.success_url)
                
        except Exception as e:
            messages.error(
                self.request,
                f'Error registering agent: {str(e)}'
            )
            return self.form_invalid(user_form, profile_form)

    def form_invalid(self, user_form, profile_form):
        """Handle invalid form data."""
        return self.render_to_response(
            self.get_context_data(
                form=user_form,
                profile_form=profile_form
            )
        )

    def send_welcome_email(self, agent):
        """Send welcome email to agent."""
        # TODO: Implement email sending
        pass

@login_required
def company_dashboard(request):
    """Company admin dashboard view."""
    # Basic access check
    if not request.user.is_authenticated:
        return redirect('accounts:login')
        
    if request.user.user_type != 'COMPANY_ADMIN':
        messages.error(request, 'Access denied. You must be a company admin.')
        return redirect('accounts:login')
    
    # Simple dashboard data
    context = {
        'user': request.user,
        'company': request.user.company,
    }
    return render(request, 'accounts/company_dashboard.html', context)

def calculate_collection_rate(company):
    """Calculate collection rate for the company."""
    total_order_amount = company.orders.aggregate(
        total=models.Sum('total_amount')
    )['total'] or 0
    total_collections = company.payments.aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    if total_order_amount == 0:
        return 100
    return round((total_collections / total_order_amount) * 100, 2)

@login_required
def agent_dashboard(request):
    """Agent dashboard view."""
    if request.user.user_type != 'AGENT':
        messages.error(request, 'Access denied.')
        return redirect('accounts:login')
    
    agent = request.user.agent_profile
    context = {
        'total_collections': agent.total_collections,
        'total_orders': agent.total_orders,
        'collection_efficiency': agent.collection_efficiency,
    }
    return render(request, 'accounts/agent_dashboard.html', context)

class AgentListView(LoginRequiredMixin, ListView):
    """View for listing agents."""
    model = Agent
    template_name = 'accounts/agent_list.html'
    context_object_name = 'agents'

    def get_queryset(self):
        """Filter agents by company."""
        return Agent.objects.filter(company=self.request.user.company)

    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['company'] = self.request.user.company
        return context
