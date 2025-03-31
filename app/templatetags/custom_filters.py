from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def div(value, arg):
    """Divide the value by the argument"""
    try:
        if not value:
            return 0
        return Decimal(value) / Decimal(arg) if arg else 0
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Multiply the value with the argument"""
    try:
        if not value:
            return 0
        return Decimal(value) * Decimal(arg)
    except ValueError:
        return 0

@register.filter
def subtract(value, arg):
    """Subtract the argument from the value"""
    try:
        if not value:
            return 0
        return Decimal(value) - Decimal(arg)
    except ValueError:
        return 0

@register.filter
def add(value, arg):
    """Add the argument to the value"""
    try:
        if not value:
            return 0
        return Decimal(value) + Decimal(arg)
    except ValueError:
        return 0

@register.filter
def percentage(value, total):
    """Calculate percentage of value against total"""
    try:
        if not value or not total:
            return 0
        return (Decimal(value) / Decimal(total)) * 100
    except (ValueError, ZeroDivisionError):
        return 0 