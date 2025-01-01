from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, Company, Agent
from django.contrib.auth import password_validation

class EmailAuthenticationForm(AuthenticationForm):
    """Custom authentication form that uses email instead of username."""
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

class CompanyRegistrationForm(forms.ModelForm):
    """Form for company registration."""
    class Meta:
        model = Company
        fields = ['name', 'address', 'phone', 'email', 'website', 'gstin', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'gstin': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'})
        }

    def clean_gstin(self):
        gstin = self.cleaned_data.get('gstin')
        if gstin:
            # Add GSTIN validation logic here
            if len(gstin) != 15:
                raise ValidationError('GSTIN must be 15 characters long')
        return gstin

class CompanyAdminRegistrationForm(forms.ModelForm):
    """Form for registering company admin users."""
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=password_validation.password_validators_help_text_html()
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Enter the same password as before, for verification.'
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        """Check if both passwords match."""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        """Save the user with the hashed password."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.username = None  # Ensure username is not used
        user.user_type = 'COMPANY_ADMIN'
        if commit:
            user.save()
        return user

class AgentRegistrationForm(UserCreationForm):
    """Form for agent registration."""
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'AGENT'
        if commit:
            user.save()
        return user

class AgentProfileForm(forms.ModelForm):
    """Form for agent profile details."""
    class Meta:
        model = Agent
        fields = ['full_name', 'address', 'id_proof_type', 'id_proof_number', 'role']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'id_proof_type': forms.TextInput(attrs={'class': 'form-control'}),
            'id_proof_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'})
        } 