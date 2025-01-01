from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

class UserManager(BaseUserManager):
    """Custom user manager to handle email as the unique identifier."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'SUPER_ADMIN')
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Custom user model that uses email as the unique identifier."""
    USER_TYPES = (
        ('SUPER_ADMIN', 'Super Admin'),
        ('COMPANY_ADMIN', 'Company Admin'),
        ('AGENT', 'Agent'),
    )

    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    company = models.ForeignKey(
        'Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['user_type']

    def __str__(self):
        return self.email

    class Meta:
        swappable = 'AUTH_USER_MODEL'

class Company(models.Model):
    """Model to store company information."""
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    gstin = models.CharField(max_length=15, blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    
    # Subscription and status
    SUBSCRIPTION_STATUS_CHOICES = [
        ('TRIAL', 'Trial'),
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='TRIAL'
    )
    subscription_end_date = models.DateField(null=True, blank=True)
    
    # Branding settings
    primary_color = models.CharField(max_length=7, default='#007bff')  # Hex color code
    secondary_color = models.CharField(max_length=7, default='#6c757d')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Agent(models.Model):
    """Model to store agent information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='agents')
    
    # Personal Information
    full_name = models.CharField(max_length=100)
    address = models.TextField()
    id_proof_type = models.CharField(max_length=50, blank=True, null=True)
    id_proof_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Role and Status
    ROLE_CHOICES = [
        ('FIELD_AGENT', 'Field Agent'),
        ('OFFICE_STAFF', 'Office Staff'),
        ('SUPERVISOR', 'Supervisor'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='FIELD_AGENT')
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Performance Metrics
    total_collections = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    total_orders = models.IntegerField(default=0)
    collection_target = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} - {self.company.name}"

    class Meta:
        ordering = ['company', 'full_name']

    @property
    def collection_efficiency(self):
        """Calculate collection efficiency as a percentage."""
        if self.collection_target == 0:
            return 0
        return (self.total_collections / self.collection_target) * 100

    @property
    def is_active(self):
        """Check if the agent is currently active."""
        return self.status == 'ACTIVE'
