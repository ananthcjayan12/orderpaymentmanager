from django import forms
from django.forms import inlineformset_factory
from .models import Order, OrderItem, Payment

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer', 'order_date', 'remarks']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' in kwargs and 'customer' in kwargs['initial']:
            self.fields['customer'].widget.attrs['readonly'] = True
            self.fields['customer'].disabled = True

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['item_name', 'quantity', 'price', 'remarks']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }

# Create the formset with more configuration
OrderItemFormSet = inlineformset_factory(
    Order, 
    OrderItem,
    form=OrderItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
    fields=['item_name', 'quantity', 'price', 'remarks'],
)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['customer', 'amount_received', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' in kwargs and 'customer' in kwargs['initial']:
            self.fields['customer'].widget.attrs['readonly'] = True
            self.fields['customer'].disabled = True 