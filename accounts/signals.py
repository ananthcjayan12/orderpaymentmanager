from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Agent, Company

User = get_user_model()

@receiver(pre_save, sender=User)
def set_user_type(sender, instance, **kwargs):
    """Set user type based on the related profile."""
    if hasattr(instance, 'agent_profile'):
        instance.user_type = 'AGENT'

@receiver(post_save, sender=Agent)
def update_user_status(sender, instance, **kwargs):
    """Update user active status based on agent status."""
    if instance.user:
        instance.user.is_active = instance.status == 'ACTIVE'
        instance.user.save()

@receiver(post_save, sender=Company)
def handle_company_status_change(sender, instance, **kwargs):
    """Handle company subscription status changes."""
    if instance.subscription_status in ['EXPIRED', 'CANCELLED']:
        # Deactivate all agents when company subscription expires/cancels
        instance.agents.all().update(status='INACTIVE')
        # Deactivate all related user accounts
        User.objects.filter(
            agent_profile__company=instance
        ).update(is_active=False) 